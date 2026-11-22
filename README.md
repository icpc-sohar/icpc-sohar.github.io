# نادي ICPC جامعة صحار · ICPC Sohar University Club

الموقع الرسمي لنادي البرمجة التنافسية في جامعة صحار، بالعربية والإنجليزية.
The official website of Sohar University's competitive programming club, in Arabic and English.

## البناء · Build

يحتاج Python 3 فقط (المكتبة القياسية). · Needs Python 3 only (standard library).

```bash
python3 tools/build.py                 # -> _site/
python3 -m http.server 8000 -d _site   # http://localhost:8000/
```

ينشر GitHub Actions الموقع تلقائياً عند كل دفع إلى `main` (`.github/workflows/pages.yml`).
GitHub Actions publishes the site on every push to `main`.

## أين يُعدَّل المحتوى · Where content lives

| | |
|---|---|
| `src/pages/ar/`, `src/pages/en/` | نصوص الصفحات · page text (first line: title and description) |
| `i18n/ar.json`, `i18n/en.json` | نصوص الواجهة المشتركة · shared interface text |
| `data/team.json` | الفريق والهيئة الإدارية · team and board |
| `src/layout.html` | الهيكل المشترك · shared layout |
| `assets/css/`, `assets/js/site.js` | التصميم والحركة · design and motion |

## الفحص · Checks

Playwright for Python is needed for these:

```bash
python3 tools/check.py screenshots/site 390,1440 light,dark   # layout, overflow, tap targets, alt text
python3 tools/motion_check.py                                 # intro, motion, gallery viewer
python3 tools/lighthouse.py                                   # Lighthouse (mobile), needs Node
```

## الحقوق · Rights

الصور والشعارات ملك نادي ICPC جامعة صحار وجامعة صحار، ولا يُعاد استخدامها دون إذن.
Photos and logos belong to the ICPC Sohar University Club and Sohar University; do not reuse them without permission.
