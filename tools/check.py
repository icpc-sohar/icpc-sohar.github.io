"""Render every built page and report layout problems. Run after tools/build.py:
  python3 tools/check.py [out_dir] [widths] [themes]
For each page x width x theme: full-page screenshot, horizontal overflow, broken images,
console errors, tap targets under 44px, missing alt, heading order. Writes <out_dir>/report.json."""
import json
import sys
from pathlib import Path
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'screenshots/site')
widths = [int(w) for w in (sys.argv[2] if len(sys.argv) > 2 else '390,1440').split(',')]
themes = (sys.argv[3] if len(sys.argv) > 3 else 'light').split(',')
pages = sorted(p for p in (ROOT / '_site').rglob('index.html'))
out.mkdir(parents=True, exist_ok=True)

PROBE = '''() => {
  const de = document.documentElement;
  const broken = [...document.images].filter(i => i.complete && i.naturalWidth === 0 && !i.closest('dialog')).map(i => i.src.split('/').pop());
  const noAlt = [...document.images].filter(i => !i.hasAttribute('alt')).length;
  const small = [...document.querySelectorAll('a, button, input, [role=button]')].filter(e => {
    const r = e.getBoundingClientRect();
    if (!r.width || !e.offsetParent && getComputedStyle(e).position !== 'fixed') return false;
    if (e.matches('.skip, .quiz input')) return false;
    if (e.closest('p, li p, figcaption')) return false; // inline text links are exempt (WCAG 2.5.8)
    return r.width < 44 || r.height < 44;
  }).map(e => (e.textContent.trim() || e.getAttribute('aria-label') || e.tagName).slice(0, 30));
  const hs = [...document.querySelectorAll('h1,h2,h3,h4')].filter(h => !h.closest('[hidden]')).map(h => +h.tagName[1]);
  const skips = hs.filter((h, i) => i && h > hs[i - 1] + 1).length;
  return {scrollW: de.scrollWidth, clientW: de.clientWidth, h1: hs.filter(h => h === 1).length, headingSkips: skips,
          broken, noAlt, small: [...new Set(small)].slice(0, 8)};
}'''

# Serve _site over http on a free local port for the run only (file:// blocks font preloads).
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT / '_site')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}/'

report = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in themes:
        for w in widths:
            ctx = b.new_context(viewport={'width': w, 'height': 844 if w < 600 else 900}, device_scale_factor=1,
                                is_mobile=w < 600, has_touch=w < 960, locale='ar')
            # Layout checks look at the page itself, so the home intro counts as already seen
            ctx.add_init_script(f"try{{localStorage.setItem('icpc-theme','{theme}');sessionStorage.setItem('icpc-intro-seen','1')}}catch(e){{}}")
            for page_file in pages:
                rel = page_file.parent.relative_to(ROOT / '_site').as_posix()
                name = (rel if rel != '.' else 'home').replace('/', '-')
                pg = ctx.new_page()
                errs = []
                pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.goto(BASE + ('' if rel == '.' else rel + '/'), wait_until='load')
                y, total = 0, pg.evaluate('document.documentElement.scrollHeight')
                while y < total:
                    pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(80); y += 600
                pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(300)
                m = pg.evaluate(PROBE)
                m['errors'] = errs[:5]
                pg.screenshot(path=str(out / f'{name}-{w}-{theme}.png'), full_page=True)
                report[f'{name} {w} {theme}'] = m
                pg.close()
            ctx.close()
    b.close()
srv.shutdown()
srv.server_close()

(out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
bad = {k: v for k, v in report.items() if v['scrollW'] > v['clientW'] or v['broken'] or v['errors'] or v['noAlt'] or v['h1'] != 1 or v['headingSkips'] or v['small']}
print(f'{len(report)} renders, {len(report) - len(bad)} clean')
for k, v in bad.items():
    print(k, {x: v[x] for x in v if v[x] and x not in ('clientW', 'h1') or (x == 'h1' and v[x] != 1) or (x == 'scrollW' and v['scrollW'] > v['clientW'])})
