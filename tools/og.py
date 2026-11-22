"""Render the link-preview image (Open Graph) shown when the site is shared: assets/icons/og.jpg, 1200x630.
Bilingual, so one image serves the Arabic and English pages. Uses the cover photo, the club mark,
the university logo and the local fonts; rendered with Playwright from a small inline page.
Run:  python3 tools/og.py   (then python3 tools/build.py copies it into _site/)"""
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="/assets/fonts/fonts.css">
<style>
  :root { --navy:#0B427B; --sun:#F2B43C; }
  * { margin:0; box-sizing:border-box; }
  body { inline-size:1200px; block-size:630px; overflow:hidden; position:relative; color:#fff;
         font-family:'IBM Plex Sans Arabic','Archivo',sans-serif; background:#081220; }
  .ph { position:absolute; inset:0; inline-size:100%; block-size:100%; object-fit:cover; object-position:42% 38%; }
  .shade { position:absolute; inset:0; background:
      linear-gradient(to left, rgb(8 18 32 / .95) 0%, rgb(8 18 32 / .82) 48%, rgb(8 18 32 / .25) 100%); }
  .txt { position:absolute; inset-block:64px; inset-inline-start:72px; inline-size:640px; display:flex; flex-direction:column; }
  .brand { display:flex; align-items:center; gap:16px; font-weight:700; font-size:26px; }
  .brand img { inline-size:64px; block-size:64px; }
  .brand small { display:block; font-size:18px; font-weight:400; opacity:.8; }
  .bar { inline-size:72px; block-size:6px; background:var(--sun); margin-block:auto 28px; }
  h1 { font-size:78px; line-height:1.12; font-weight:700; }
  h1 b { font-family:'Archivo',sans-serif; font-weight:800; }
  .en { margin-block-start:18px; font-family:'Archivo',sans-serif; font-weight:500; font-size:26px; opacity:.85; direction:ltr; text-align:right; }
  .su { position:absolute; inset-block-end:56px; inset-inline-end:64px; block-size:52px; }
</style></head><body>
  <img class="ph" src="/assets/img/O05-1200.webp" alt="">
  <div class="shade"></div>
  <div class="txt">
    <div class="brand"><img src="/assets/logos/club/icpc-su-mark-ondark.svg" alt=""><div>نادي ICPC<small>جامعة صحار</small></div></div>
    <div class="bar"></div>
    <h1>جامعة صحار<br>تتأهل إلى <b>ACPC</b></h1>
    <p class="en">Sohar University qualifies for ACPC 2026</p>
  </div>
  <img class="su" src="/assets/logos/su/su-white-horizontal-icon-right.svg" alt="">
</body></html>'''


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == '/og.html':
            body = PAGE.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()


srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1200, 'height': 630})
    pg.goto(f'http://127.0.0.1:{srv.server_address[1]}/og.html', wait_until='networkidle')
    pg.evaluate('document.fonts.ready')
    out = ROOT / 'assets/icons/og.jpg'
    pg.screenshot(path=str(out), type='jpeg', quality=86)
    b.close()
srv.shutdown()
srv.server_close()
print('wrote', out.relative_to(ROOT), out.stat().st_size // 1024, 'KB')
