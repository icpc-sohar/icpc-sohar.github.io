"""Exercise the motion and the gallery viewer on the built site; save frames for review.
Run after tools/build.py:  python3 tools/motion_check.py
Checks: cover animation frames, film rows move with scroll, numbers count up, balloons rise,
gallery viewer next/previous/keys/close, and that reduced motion shows everything at once."""
import functools
import json
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'screenshots/motion'
OUT.mkdir(parents=True, exist_ok=True)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT / '_site')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}/'
res = {}
with sync_playwright() as p:
    b = p.chromium.launch()

    # Intro: frames over its 2.85s, gone afterwards with scrolling restored; Escape skips it early
    for vw, vh, tag in ((1440, 900, 'desk'), (390, 844, 'mob')):
        ic = b.new_context(viewport={'width': vw, 'height': vh})
        pg = ic.new_page(); ierr = []
        pg.on('pageerror', lambda e: ierr.append(str(e)))
        pg.goto(BASE, wait_until='load')
        # Exact frames: freeze every running animation and seek it to the same moment of the intro
        # (a CSS animation's currentTime counts from its start, delay included)
        for ms in (250, 500, 800, 1150, 1700, 2150, 2350, 2550, 2700):
            pg.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {ms}; }})")
            pg.wait_for_timeout(60)
            pg.screenshot(path=str(OUT / f'intro-{tag}-{ms:04d}.png'))
        pg.evaluate("document.getAnimations().forEach(a => a.play())")
        pg.wait_for_timeout(600)
        res[f'intro_{tag}'] = {'removed': pg.evaluate("!document.querySelector('.intro')"),
                               'scroll_free': pg.evaluate("document.documentElement.style.overflow === ''"),
                               'errors': ierr}
        pg.close()
        pg = ic.new_page()  # new tab = new session, so the intro shows again
        pg.goto(BASE, wait_until='load'); pg.wait_for_timeout(700)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(450)
        res[f'intro_{tag}']['escape_skips'] = pg.evaluate("!document.querySelector('.intro')")
        pg.goto(BASE, wait_until='load'); pg.wait_for_timeout(200)
        res[f'intro_{tag}']['once_per_session'] = pg.evaluate("!document.documentElement.classList.contains('intro-on')")
        ic.close()

    ctx = b.new_context(viewport={'width': 1440, 'height': 900})
    ctx.add_init_script("try{sessionStorage.setItem('icpc-intro-seen','1')}catch(e){}")
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE, wait_until='commit')
    t = 0
    for ms in (150, 600, 1400):
        pg.wait_for_timeout(ms - t); t = ms
        pg.screenshot(path=str(OUT / f'cover-{ms}.png'))
    pg.wait_for_timeout(1500)
    pg.locator('.film').scroll_into_view_if_needed()
    pg.evaluate("scrollBy(0, -300)"); pg.wait_for_timeout(400)
    t1 = pg.evaluate("[...document.querySelectorAll('[data-drift]')].map(r => r.style.transform)")
    pg.screenshot(path=str(OUT / 'film-a.png'))
    pg.evaluate("scrollBy(0, 500)"); pg.wait_for_timeout(400)
    t2 = pg.evaluate("[...document.querySelectorAll('[data-drift]')].map(r => r.style.transform)")
    pg.screenshot(path=str(OUT / 'film-b.png'))
    res['film_moves'] = t1 != t2
    res['film_transforms'] = [t1, t2]
    pg.locator('.lede').scroll_into_view_if_needed(); pg.wait_for_timeout(1500)
    res['counted'] = pg.evaluate("[...document.querySelectorAll('[data-count]')].map(e => e.textContent)")
    pg.locator('[data-rise]').scroll_into_view_if_needed(); pg.wait_for_timeout(1800)
    res['balloons_risen'] = pg.evaluate("document.querySelector('[data-rise]').classList.contains('in')")
    pg.screenshot(path=str(OUT / 'contest.png'))

    pg.goto(BASE + 'gallery/', wait_until='load'); pg.wait_for_timeout(800)
    pg.locator('.gallery figure button').nth(2).click(); pg.wait_for_timeout(700)
    c1 = pg.inner_text('.viewer-count')
    pg.locator('.viewer-nav[data-step="1"]').click(); pg.wait_for_timeout(500)
    c2 = pg.inner_text('.viewer-count')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(500)
    c3 = pg.inner_text('.viewer-count')
    pg.screenshot(path=str(OUT / 'viewer.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    res['viewer'] = {'open': c1, 'next': c2, 'arrowRight': c3, 'closed': not pg.evaluate("document.querySelector('.viewer').open")}
    res['errors'] = errs
    ctx.close()

    rm = b.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    pg = rm.new_page(); pg.goto(BASE, wait_until='load'); pg.wait_for_timeout(300)
    res['reduced_motion_no_intro'] = pg.evaluate("!document.documentElement.classList.contains('intro-on')")
    res['reduced_motion_hidden'] =pg.evaluate("[...document.querySelectorAll('main *')].filter(e => getComputedStyle(e).opacity === '0' && e.getBoundingClientRect().height > 0).length")
    rm.close()
    b.close()
srv.shutdown()
srv.server_close()
print(json.dumps(res, ensure_ascii=False, indent=1))
