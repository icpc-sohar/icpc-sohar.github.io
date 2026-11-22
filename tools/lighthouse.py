"""Lighthouse (mobile, simulated slow phone + network) on every built page, served gzip-compressed like
GitHub Pages serves it. Needs Node; the first run downloads lighthouse@12 into the npx cache.
Run after tools/build.py:  python3 tools/lighthouse.py [page ...]   e.g.  python3 tools/lighthouse.py / en/gallery/
Reports: screenshots/lighthouse/perf/<page>.json (git-ignored). Targets: P>=90 A>=95 BP>=95 SEO>=95, LCP<2.5s, CLS<0.1."""
import functools
import gzip
import io
import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / '_site'
OUT = ROOT / 'screenshots/lighthouse/perf'
TEXT = ('text/', 'application/javascript', 'application/json', 'image/svg+xml', 'application/xml')


class Gzip(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / 'index.html'
        ctype = self.guess_type(str(path))
        if not path.is_file() or not ctype.startswith(TEXT) or 'gzip' not in self.headers.get('Accept-Encoding', ''):
            return super().send_head()
        body = gzip.compress(path.read_bytes())
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        return io.BytesIO(body)


pages = sys.argv[1:] or sorted('/' + p.parent.relative_to(SITE).as_posix().replace('.', '') + '/' for p in SITE.rglob('index.html'))
pages = [('/' + p.strip('/') + '/').replace('//', '/') for p in pages]
OUT.mkdir(parents=True, exist_ok=True)
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Gzip, directory=str(SITE)))
srv.handle_error = lambda *a: None  # Lighthouse drops connections on purpose; not an error
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{srv.server_address[1]}'
fails = 0
for p in pages:
    name = ('home' + p.rstrip('/').replace('/', '-')) if p != '/' else 'home'
    dest = OUT / f'{name}.json'
    subprocess.run(['npx', '-y', 'lighthouse@12', base + p, '--quiet', '--chrome-flags=--headless=new',
                    '--output=json', f'--output-path={dest}'], check=True, capture_output=True)
    r = json.loads(dest.read_text())
    c, a = r['categories'], r['audits']
    s = {k: round(c[k]['score'] * 100) for k in ('performance', 'accessibility', 'best-practices', 'seo')}
    lcp = a['largest-contentful-paint']['numericValue'] / 1000
    cls = a['cumulative-layout-shift']['numericValue']
    ok = s['performance'] >= 90 and min(s['accessibility'], s['best-practices'], s['seo']) >= 95 and lcp < 2.5 and cls < 0.1
    fails += not ok
    print(f"{'ok ' if ok else 'LOW'} {p:20} P{s['performance']:4} A{s['accessibility']:4} BP{s['best-practices']:4} "
          f"SEO{s['seo']:4}  LCP {lcp:.2f}s  CLS {cls:.3f}  TBT {a['total-blocking-time']['displayValue']}")
srv.shutdown()
srv.server_close()
print(f'{len(pages) - fails}/{len(pages)} pages meet every target')
