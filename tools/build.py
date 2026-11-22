"""Build the static site into _site/. Python standard library only (runs as-is on GitHub Actions).
Run: python3 tools/build.py

Inputs
  src/layout.html            page shell (head, header, footer)
  src/pages/<lang>/<slug>.html  page bodies; first line: <!--meta {"title": "...", "description": "..."}-->
  i18n/<lang>.json           shared interface text
  data/team.json             people on the Team page (single source of truth)
  assets/                    css (fonts.css + tokens.css + site.css are joined), js, fonts, logos, icons, img

Macros inside page bodies
  {{root}}                   relative path to the site root ('' or '../' ...), so file:// previews work too
  {{t:key}}                  interface text from i18n
  {{img CODE|alt|sizes}}     responsive WebP from assets/img; add |eager for the first image on a page
  {{team:founders}} {{team:advisors}} {{team:board}}
"""
import html
import json
import re
import urllib.parse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / '_site'
SITE_URL = 'https://icpc-sohar.github.io/'  # suggested org name (DECISIONS.md, section و); change at publish time
PAGES = ['index', 'about', 'competition', 'achievements', 'team', 'gallery', 'join']
LANGS = ['ar', 'en']
IMG_WIDTHS = (400, 640, 960, 1200, 1800)

sizes = json.loads((ROOT / 'assets/img/sizes.json').read_text())
team = json.loads((ROOT / 'data/team.json').read_text())
layout = (ROOT / 'src/layout.html').read_text()


def url_path(slug, lang):
    return ('' if lang == 'ar' else 'en/') + ('' if slug == 'index' else slug + '/')


def page_exists(slug, lang):
    return (ROOT / 'src/pages' / lang / f'{slug}.html').exists()


def img(code, alt, sizes_attr, mode, root):
    w0, h0 = sizes[code]
    widths = [w for w in IMG_WIDTHS if w <= w0] or [IMG_WIDTHS[0]]
    srcset = ', '.join(f'{root}assets/img/{code}-{w}.webp {min(w, w0)}w' for w in widths)
    mid = widths[min(1, len(widths) - 1)]
    # eager: the page's main image, fetched first. first: on screen at load, not lazy. default: lazy
    load = {'eager': 'fetchpriority="high"', 'first': ''}.get(mode, 'loading="lazy"')
    return (f'<img src="{root}assets/img/{code}-{mid}.webp" srcset="{srcset}" sizes="{sizes_attr}" '
            f'width="{w0}" height="{h0}" alt="{html.escape(alt)}" decoding="async" {load}>')


def initials(en_name):
    words = [w for w in re.split(r'[\s.]+', en_name) if w and w.lower() not in ('prof', 'dr', 'eng')]
    return (words[0][0] + (words[-1][0] if len(words) > 1 else '')).upper()


def field(v, lang):
    if isinstance(v, dict):
        return v.get(lang) or v.get('en') or v.get('ar') or ''
    return v or ''


def person(p, lang, root, kind):
    name = field(p['name'], lang)
    name_lang = '' if p['name'].get(lang) else ' lang="en" dir="ltr"'
    if p.get('photo'):
        ph = f'<img src="{root}{p["photo"]}" alt="" width="400" height="500" loading="lazy">'
    else:
        ph = f'<span class="ini" aria-hidden="true">{initials(p["name"]["en"])}</span>'
    role = field(p.get('role'), lang)
    dept = field(p.get('department'), lang)
    role_html = f'<span class="role" lang="en" dir="ltr">{html.escape(role)}</span>' if kind == 'board' else f'<span class="role">{html.escape(role)}</span>'
    dept_html = f'<span class="dept">{html.escape(dept)}</span>' if dept else ''
    state = '' if p.get('photo') else ' no-photo'
    return (f'<li class="person person-{kind}{state}"><div class="ph">{ph}</div>'
            f'<div class="who"><b{name_lang}>{html.escape(name)}</b>{role_html}{dept_html}</div></li>')


def team_block(which, lang, root):
    people = team[which]
    if which == 'board':
        people = sorted(people, key=lambda p: p['order'])
    kind = {'founders': 'founder', 'advisors': 'advisor', 'board': 'board'}[which]
    return '\n'.join(person(p, lang, root, kind) for p in people)


def external_links(out, note):
    """Every link that leaves the site (social accounts, the join form, icpc.global) opens in a
    new tab, and says so to screen readers: in its aria-label when it has one, else in hidden text."""
    def fix(m):
        attrs, inner = m.group(1), m.group(2)
        href = re.search(r'href="([^"]+)"', attrs).group(1)
        if not href.startswith(('http://', 'https://')) or href.startswith(SITE_URL):
            return m.group(0)
        attrs = re.sub(r'\s(?:rel|target)="[^"]*"', '', attrs) + ' target="_blank" rel="noopener noreferrer"'
        if 'aria-label="' in attrs:
            attrs = re.sub(r'aria-label="([^"]*)"', lambda a: f'aria-label="{a.group(1)} ({note})"', attrs)
        else:
            inner += f'<span class="sr-only"> ({note})</span>'
        return f'<a{attrs}>{inner}</a>'
    return re.sub(r'<a(\s[^>]*href="[^"]+"[^>]*)>(.*?)</a>', fix, out, flags=re.S)


def render(slug, lang, t):
    body = (ROOT / 'src/pages' / lang / f'{slug}.html').read_text()
    first, body = body.split('\n', 1)
    meta = json.loads(re.match(r'<!--meta (.*)-->', first).group(1))
    path = url_path(slug, lang)
    root = '../' * path.count('/')

    body = re.sub(r'\{\{img ([A-Z]\d+)\|([^|}]*)\|([^|}]*)(?:\|(\w+))?\}\}',
                  lambda m: img(m.group(1), m.group(2), m.group(3), m.group(4), root), body)
    body = re.sub(r'\{\{team:(\w+)\}\}', lambda m: team_block(m.group(1), lang, root), body)

    current = ' aria-current="page"'
    nav = '\n'.join(
        f'<a href="{root}{url_path(s, lang)}"{current if s == slug else ""}>{t["nav"][s]}</a>'
        for s in PAGES if s != 'join')
    other = 'en' if lang == 'ar' else 'ar'
    alt_link = ''
    if page_exists(slug, other):
        alt_link = f'<a class="icon-btn" href="{root}{url_path(slug, other)}" lang="{other}" hreflang="{other}" aria-label="{t["other_lang_label"]}">{t["other_lang_short"]}</a>'
    title = meta['title'] if slug == 'index' else f'{meta["title"]} · {t["site_name"]}'
    out = layout
    vals = {
        'lang': t['lang'], 'dir': t['dir'], 'title': html.escape(title), 'description': html.escape(meta['description']),
        'canonical': SITE_URL + path, 'og_image': SITE_URL + 'assets/icons/og.jpg', 'nav': nav, 'alt_link': alt_link,
        'join_url': f'{root}{url_path("join", lang)}', 'home_url': f'{root}{url_path("index", lang)}',
        'content': body, 'page': slug,
        'intro': (ROOT / 'src/intro.html').read_text() if slug == 'index' else '',
        'alternates': '\n'.join(
            f'<link rel="alternate" hreflang="{l}" href="{SITE_URL}{url_path(slug, l)}">' for l in LANGS if page_exists(slug, l))
            + (f'\n<link rel="alternate" hreflang="x-default" href="{SITE_URL}{url_path(slug, "ar")}">' if page_exists(slug, 'en') else ''),
    }
    for k, v in vals.items():
        out = out.replace('{{' + k + '}}', v)
    out = re.sub(r'\{\{t:([\w.]+)\}\}', lambda m: t[m.group(1)], out)
    out = out.replace('{{root}}', root)
    out = external_links(out, t['new_tab'])
    # The stylesheet (11 KB compressed) goes inside each page: one round trip fewer before anything can paint
    css = (OUT / 'assets/css/site.css').read_text().replace("url('../fonts/", f"url('{root}assets/fonts/")
    css = re.sub(r'\s+', ' ', re.sub(r'/\*.*?\*/', '', css, flags=re.S))
    out = out.replace(f'<link rel="stylesheet" href="{root}assets/css/site.css">', f'<style>{css}</style>')
    dest = OUT / path / 'index.html'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)
    return SITE_URL + path


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / 'assets/css').mkdir(parents=True)
    fonts = (ROOT / 'assets/fonts/fonts.css').read_text().replace("url('", "url('../fonts/")
    css = '\n'.join([fonts, (ROOT / 'assets/css/tokens.css').read_text(), (ROOT / 'assets/css/site.css').read_text()])
    # Small SVGs used as CSS backgrounds go inline, so the browser needn't find and fetch them after the CSS
    def inline_svg(m):
        f = ROOT / 'assets' / m.group(1)
        if f.stat().st_size > 4096:
            return m.group(0)
        return "url('data:image/svg+xml," + urllib.parse.quote(f.read_text().strip(), safe=' /=:;,"-.') + "')"
    css = re.sub(r"url\('\.\./(logos/[\w/-]+\.svg)'\)", inline_svg, css)
    (OUT / 'assets/css/site.css').write_text(css)
    shutil.copytree(ROOT / 'assets/fonts', OUT / 'assets/fonts', ignore=shutil.ignore_patterns('*.css'))
    shutil.copytree(ROOT / 'assets/js', OUT / 'assets/js')
    shutil.copytree(ROOT / 'assets/icons', OUT / 'assets/icons')
    shutil.copytree(ROOT / 'assets/img', OUT / 'assets/img', ignore=shutil.ignore_patterns('*.json'))
    shutil.copytree(ROOT / 'assets/logos', OUT / 'assets/logos')

    urls = []
    for lang in LANGS:
        i18n = ROOT / 'i18n' / f'{lang}.json'
        if not i18n.exists():
            continue
        t = json.loads(i18n.read_text())
        urls += [render(s, lang, t) for s in PAGES if page_exists(s, lang)]

    (OUT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n')
    (OUT / '.nojekyll').write_text('')
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    print(f'{len(urls)} pages · {size // 1024} KB in _site/')


if __name__ == '__main__':
    main()
