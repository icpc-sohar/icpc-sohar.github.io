// Site behaviour. No dependencies. Each block runs only if its markup is on the page.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5m6-6-6 6 6 6"/></svg>';
  const COLORS = ['#1561A4', '#F2B43C', '#BA2735', '#7FB8EC', '#0B427B', '#FF8A93']; // one colour per problem
  const balloon = (letter, color) => `<svg class="balloon" viewBox="0 0 44 80" aria-hidden="true">
    <path class="string" d="M22 50c-4 8 4 14 0 28"/>
    <path class="body" d="M22 2C10.4 2 3 11.4 3 23c0 13 10.2 23.6 17 25h4c6.8-1.4 17-12 17-25C41 11.4 33.6 2 22 2Z" fill="${color}"/>
    <path class="knot" d="M18.5 50h7L22 45.5z" fill="${color}"/>
    <ellipse class="shine" cx="14" cy="15" rx="4" ry="7" transform="rotate(20 14 15)"/>
    ${letter ? `<text x="22" y="29">${letter}</text>` : ''}</svg>`;

  $$('[data-arrow]').forEach(el => el.insertAdjacentHTML('beforeend', ARROW));
  $$('[data-cluster]').forEach(el => { el.innerHTML = balloon('', COLORS[0]) + balloon('', COLORS[1]) + balloon('', COLORS[2]); });

  // Theme: light by default; the inline head script already applied any saved choice.
  const setTheme = t => {
    document.documentElement.dataset.theme = t;
    $$('.theme').forEach(b => b.setAttribute('aria-pressed', String(t === 'dark')));
  };
  setTheme(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
  $$('.theme').forEach(b => b.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('icpc-theme', next); } catch (_) { /* storage blocked: the choice lasts for this page */ }
  }));

  // Mobile menu
  const header = $('.header'), menu = $('.menu');
  if (menu) {
    const close = () => { header.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); };
    menu.addEventListener('click', () => {
      const open = !header.classList.contains('open');
      header.classList.toggle('open', open);
      menu.setAttribute('aria-expanded', String(open));
      if (open) $('.nav a', header)?.focus();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && header.classList.contains('open')) { close(); menu.focus(); } });
    matchMedia('(min-width: 960px)').addEventListener('change', close);
  }

  // Scoreboard simulator. ICPC rule: more problems solved first, then less total time.
  // Each problem: [minute of the accepted run, rejected runs before it]; each rejected run adds 20 minutes.
  const sim = $('[data-sim]');
  if (sim) {
    const P = [[12, 0], [38, 1], [71, 0], [104, 0], [160, 2], [233, 0]];
    const rival = { name: sim.dataset.rival, solved: 4, time: 300 };
    const solved = new Set([0, 1, 2]);
    const list = $('.problems', sim);
    list.innerHTML = P.map(([m, wa], i) => {
      const L = 'ABCDEF'[i];
      const sep = document.documentElement.lang === 'ar' ? '، ' : ', ';
      const label = `${sim.dataset.problem} ${L}${sep}${sim.dataset.minute} ${m}${wa ? `${sep}${wa} ${sim.dataset.rejected}` : ''}`;
      return `<li><button type="button" data-i="${i}" aria-label="${label}">${balloon(L, COLORS[i])}<b>${L}</b><small>${m}′${wa ? `<em>+${wa * 20}</em>` : ''}</small></button></li>`;
    }).join('');
    const msgs = JSON.parse($('[data-msgs]', sim).textContent);
    const fill = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => v[k]);
    const render = () => {
      $$('button', list).forEach(b => b.setAttribute('aria-pressed', String(solved.has(+b.dataset.i))));
      const time = [...solved].reduce((t, i) => t + P[i][0] + 20 * P[i][1], 0);
      const you = { name: sim.dataset.you, solved: solved.size, time, you: true };
      const rows = [you, rival].sort((a, b) => b.solved - a.solved || a.time - b.time);
      $('tbody', sim).innerHTML = rows.map((r, k) => `<tr${r.you ? ' class="you"' : ''}><td class="r">${k + 1}</td><td>${r.name}</td><td class="n">${r.solved}</td><td class="n">${r.time}</td></tr>`).join('');
      const v = { ys: you.solved, rs: rival.solved, yt: you.time, rt: rival.time };
      const key = you.solved > rival.solved ? 'ahead' : you.solved < rival.solved ? 'behind' : you.time < rival.time ? 'tieWin' : 'tieLose';
      $('.status', sim).textContent = fill(msgs[key], v);
    };
    list.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      const i = +b.dataset.i; solved.has(i) ? solved.delete(i) : solved.add(i); render();
    });
    render();
  }

  // "Test your level" quiz: one question at a time, points decide the suggested track.
  const quiz = $('[data-quiz]');
  if (quiz) {
    const data = JSON.parse($('[data-quiz-data]', quiz).textContent);
    const body = $('.quiz-body', quiz), bar = $('.quiz-bar i', quiz), count = $('.quiz-count', quiz);
    const prev = $('[data-prev]', quiz), next = $('[data-next]', quiz), nav = $('.quiz-nav', quiz);
    const answers = [];
    let step = 0;
    const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const show = () => {
      const q = data.questions[step];
      count.textContent = `${data.ui.question} ${step + 1} ${data.ui.of} ${data.questions.length}`;
      bar.style.transform = `scaleX(${(step + 1) / data.questions.length})`;
      body.innerHTML = `<fieldset><legend>${esc(q.q)}</legend>${q.code ? `<pre><code>${esc(q.code)}</code></pre>` : ''}
        ${q.options.map((o, i) => `<label><input type="radio" name="q${step}" value="${i}"${answers[step] === i ? ' checked' : ''}>${esc(o[0])}</label>`).join('')}</fieldset>`;
      prev.disabled = step === 0;
      next.disabled = answers[step] === undefined;
      next.textContent = step === data.questions.length - 1 ? data.ui.result : data.ui.next;
    };
    body.addEventListener('change', e => { answers[step] = +e.target.value; next.disabled = false; });
    prev.addEventListener('click', () => { if (step > 0) { step--; show(); } });
    next.addEventListener('click', () => {
      if (answers[step] === undefined) return;
      if (step < data.questions.length - 1) { step++; show(); $('input', body)?.focus(); return; }
      const score = answers.reduce((s, a, i) => s + data.questions[i].options[a][1], 0);
      const r = data.results.find(x => score >= x.min);
      nav.hidden = true;
      count.textContent = data.ui.track;
      body.innerHTML = `<div class="quiz-result" tabindex="-1"><b>${esc(r.title)}</b><p>${esc(r.text)}</p>
        <div class="cta"><a class="btn btn-sun" href="${quiz.dataset.join}">${esc(data.ui.join)}</a><button class="btn btn-ghost" type="button" data-again>${esc(data.ui.again)}</button></div></div>`;
      $('.quiz-result', body).focus();
    });
    body.addEventListener('click', e => {
      if (!e.target.closest('[data-again]')) return;
      answers.length = 0; step = 0; nav.hidden = false; show(); $('input', body)?.focus();
    });
    show();
  }

  // Gallery: filter by event, full-size viewer with previous/next, arrow keys and swipe.
  const gallery = $('[data-gallery]');
  const dlg = $('.viewer');
  const rtl = document.documentElement.dir === 'rtl';
  if (gallery && dlg) {
    const figs = $$('figure', gallery);
    $$('.filters button').forEach(b => b.addEventListener('click', () => {
      $$('.filters button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      figs.forEach(f => { f.hidden = b.dataset.f !== 'all' && f.dataset.event !== b.dataset.f; });
    }));
    const vImg = $('.viewer-fig img', dlg), vCap = $('.viewer-cap', dlg), vCount = $('.viewer-count', dlg);
    let list = [], at = 0;
    const largest = img => img.srcset.split(',').pop().trim().split(' ')[0];
    const show = i => {
      at = (i + list.length) % list.length;
      const img = $('img', list[at]);
      vImg.classList.add('swap');
      const next = new Image();
      next.onload = next.onerror = () => { vImg.src = next.src; vImg.alt = img.alt; vImg.classList.remove('swap'); };
      next.src = largest(img);
      vCap.textContent = $('figcaption', list[at])?.textContent || '';
      vCount.textContent = `${at + 1} / ${list.length}`;
    };
    gallery.addEventListener('click', e => {
      const btn = e.target.closest('button'); if (!btn) return;
      list = figs.filter(f => !f.hidden);
      show(list.indexOf(btn.closest('figure')));
      dlg.showModal();
    });
    $$('.viewer-nav', dlg).forEach(b => b.addEventListener('click', () => show(at + +b.dataset.step)));
    $('.viewer-close', dlg).addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft') show(at + (rtl ? 1 : -1));
      if (e.key === 'ArrowRight') show(at + (rtl ? -1 : 1));
    });
    let x0 = null;
    dlg.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
    dlg.addEventListener('touchend', e => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 50) show(at + ((dx > 0) === rtl ? 1 : -1));
    });
  }

  // The club mark turning slowly behind page titles and the join call (decoration only)
  const MARK = '<svg viewBox="-100 -100 200 200" aria-hidden="true" focusable="false"><g transform="scale(0.118)" fill="currentColor"><g transform="rotate(0)"><path d="M248 -535 L-7 -605 Q-140 -430 -357 -420 L-417 -115 Q-360 85 -197 150" fill="none" stroke="currentColor" stroke-width="138" stroke-linecap="round" stroke-linejoin="round"/><circle cx="-260" cy="-660" r="105"/></g><g transform="rotate(120)"><path d="M248 -535 L-7 -605 Q-140 -430 -357 -420 L-417 -115 Q-360 85 -197 150" fill="none" stroke="currentColor" stroke-width="138" stroke-linecap="round" stroke-linejoin="round"/><circle cx="-260" cy="-660" r="105"/></g><g transform="rotate(240)"><path d="M248 -535 L-7 -605 Q-140 -430 -357 -420 L-417 -115 Q-360 85 -197 150" fill="none" stroke="currentColor" stroke-width="138" stroke-linecap="round" stroke-linejoin="round"/><circle cx="-260" cy="-660" r="105"/></g><path d="M-32 -118H32V-88H92V-30H122V30H92V88H32V118H-32V88H-92V30H-122V-30H-92V-88H-32Z"/></g></svg>';
  $$('.page-head, .join').forEach(el => el.insertAdjacentHTML('beforeend', `<span class="deco-mark" aria-hidden="true">${MARK}</span>`));

  // ---- Motion: transform and opacity only, nothing moves for reduced motion ----
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hdr = $('.header');

  // Contest section: one balloon per problem, rising when seen
  $$('[data-rise]').forEach(el => {
    el.innerHTML = COLORS.map((c, i) => balloon('ABCDEF'[i], c).replace('<svg class="balloon"', `<svg class="balloon" style="--i:${i}"`)).join('');
  });

  // Numbers count up from zero when they come into view
  const countUp = el => {
    const to = +(el.dataset.count || el.textContent);
    if (!to || still) return;
    const t0 = performance.now(), dur = 1100;
    const tick = t => {
      const k = Math.min(1, (t - t0) / dur);
      el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  if (!still && 'IntersectionObserver' in window) {
    const SEL = '.section h2, .media-text > p, .media-text > dl, .media-text > a, .media-photo, .pset li, .stats > div, .timeline li, .path li, .vm > div, .steps-plain li, .person, .gallery figure, .strip figure, .split-photo > *, .sec-head > p, .quiz, .sim, .join h2, .join-line, .join .btn, .filters';
    const items = $$(SEL).filter(el => !el.closest('.cover, .page-head, [hidden]'));
    const seen = new Map();
    // Content already on screen at load stays put: hiding it to fade it in would only delay the first paint (LCP)
    const fold = innerHeight;
    const tops = items.map(el => el.getBoundingClientRect().top);
    items.forEach((el, k) => {
      if (tops[k] < fold) return;
      const n = seen.get(el.parentElement) || 0;
      seen.set(el.parentElement, n + 1);
      el.style.setProperty('--i', Math.min(n, 6));
      el.classList.add('reveal');
    });
    const io = new IntersectionObserver(entries => entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('in');
      const nums = $$('[data-count], .stats dt', e.target);
      if (e.target.matches('[data-count], .stats dt')) nums.push(e.target);
      nums.forEach(countUp);
      io.unobserve(e.target);
    }), { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    items.concat($$('[data-rise]')).forEach(el => io.observe(el));
    $$('.media-photo, .split-photo > figure').forEach(f => f.setAttribute('data-parallax', ''));
  } else {
    $$('[data-rise]').forEach(el => el.classList.add('in'));
  }

  // Scroll-linked: film rows drift, the timeline line draws, photos shift slightly
  const rows = $$('[data-drift]');
  const timeline = $('.timeline');
  let ticking = false;
  const frame = () => {
    ticking = false;
    const vh = innerHeight;
    if (hdr) hdr.classList.toggle('scrolled', scrollY > 8);
    rows.forEach(row => {
      const r = row.parentElement.getBoundingClientRect();
      const spare = Math.max(0, row.scrollWidth - innerWidth);
      const base = (rtl ? 1 : -1) * spare / 2; // start centred
      if (still) { row.style.transform = `translateX(${base}px)`; return; }
      const p = Math.min(1, Math.max(0, (vh - r.top) / (vh + r.height)));
      const dist = Math.min(spare, 640);
      row.style.transform = `translateX(${(base + (p - 0.5) * dist * +row.dataset.drift).toFixed(1)}px)`;
    });
    if (still) return;
    if (timeline) {
      const r = timeline.getBoundingClientRect();
      timeline.style.setProperty('--p', Math.min(1, Math.max(0, (vh * 0.65 - r.top) / r.height)).toFixed(3));
    }
    $$('[data-parallax] img').forEach(img => {
      const r = img.parentElement.getBoundingClientRect();
      const p = (r.top + r.height / 2 - vh / 2) / vh;
      img.style.setProperty('--py', `${(p * -28).toFixed(1)}px`);
    });
  };
  const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  frame();

  // Reading progress bar
  const bar = document.createElement('div');
  bar.className = 'progress';
  bar.setAttribute('aria-hidden', 'true');
  document.body.append(bar);

  // Year sentence: wrap each word so it can light up while scrolling (numbers stay whole)
  const lede = !still && $('.lede');
  if (lede) {
    const wrap = node => {
      [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.append(part); return; }
            const w = document.createElement('span'); w.className = 'w'; w.textContent = part; frag.append(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1) {
          n.classList.add('w');
        }
      });
    };
    wrap(lede);
    lede.classList.add('words');
  }
  const words = lede ? $$('.w', lede) : [];

  // Gallery filter: let newly shown photos settle in
  $$('.filters button').forEach(b => b.addEventListener('click', () => {
    if (still) return;
    $$('[data-gallery] figure:not([hidden])').forEach((f, k) => {
      f.classList.remove('pop'); void f.offsetWidth;
      f.style.setProperty('--k', Math.min(k, 12)); f.classList.add('pop');
    });
  }));

  const cover = $('.cover');
  const touch = () => {
    const vh = innerHeight;
    const max = document.documentElement.scrollHeight - vh;
    bar.style.setProperty('--sp', max > 0 ? (scrollY / max).toFixed(4) : 0);
    if (still) return;
    if (cover) {
      const h = cover.offsetHeight;
      cover.style.setProperty('--co', Math.min(1, Math.max(0, scrollY / h)).toFixed(3));
    }
    if (words.length) {
      const r = lede.getBoundingClientRect();
      const p = Math.min(1, Math.max(0, (vh * 0.85 - r.top) / (vh * 0.5)));
      const on = Math.ceil(p * words.length);
      words.forEach((w, i) => w.classList.toggle('on', i < on));
    }
  };
  let tTick = false;
  addEventListener('scroll', () => { if (!tTick) { tTick = true; requestAnimationFrame(() => { tTick = false; touch(); }); } }, { passive: true });
  addEventListener('resize', touch);
  touch();

  // Home intro (timeline lives in CSS): hold the page still, skip on the button or Escape, then remove it
  const intro = document.documentElement.classList.contains('intro-on') && $('.intro');
  if (intro) {
    const root = document.documentElement;
    root.style.overflow = 'hidden';
    $('.intro-skip', intro).focus({ preventScroll: true });
    // Where the mark should land: the header logo's centre and size
    const mark = $('.intro-mark', intro), logo = $('.brand img');
    const aim = () => {
      if (!logo) return;
      const m = mark.getBoundingClientRect(), l = logo.getBoundingClientRect();
      intro.style.setProperty('--fx', `${(l.left + l.width / 2 - (m.left + m.width / 2)).toFixed(1)}px`);
      intro.style.setProperty('--fy', `${(l.top + l.height / 2 - (m.top + m.height / 2)).toFixed(1)}px`);
      intro.style.setProperty('--fs', (l.width / m.width).toFixed(3));
    };
    aim();
    addEventListener('resize', aim);
    const done = () => {
      root.style.overflow = '';
      removeEventListener('keydown', onKey);
      removeEventListener('resize', aim);
      intro.remove();
    };
    const skip = () => {
      const now = document.timeline.currentTime / 1000;
      if (now > 1.9 || root.classList.contains('intro-skipped')) return; // already lifting
      root.style.setProperty('--intro-delay', `${now.toFixed(2)}s`); // the cover starts right away
      root.classList.add('intro-skipped');
    };
    const onKey = e => { if (e.key === 'Escape') skip(); };
    addEventListener('keydown', onKey);
    $('.intro-skip', intro).addEventListener('click', skip);
    intro.addEventListener('animationend', e => {
      if (e.target === intro && (e.animationName === 'intro-gone' || e.animationName === 'intro-out')) done();
    });
  }
})();
