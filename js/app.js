/* 문제은행 화면 + PDF 조립(pdf-lib).  레이아웃 계산은 js/layout.js 가 담당한다. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const SEC_RANK = { '공통': 0, '확률과 통계': 1, '미적분': 2, '기하': 3 };
  const FIELDS = [   // [키, 이름, 값 함수]  (과목별 단원 묶음 'u:과목'은 데이터를 읽은 뒤 추가)
    ['grade', '학년', (p) => p.grade + '학년'],
    ['year', '연도', (p) => p.year + '년'],
    ['month', '월', (p) => p.month + '월'],
    ['form', '가형/나형(2020)', (p) => (p.form ? p.form + '형' : '해당 없음')],
    ['sec', '선택과목(2021-2022)', (p) => p.sec],
    ['subject', '과목', (p) => subjDisp(p.subject)],
    ['points', '배점', (p) => (p.points == null ? '-' : p.points + '점')],
    ['type', '문제 유형', (p) => typeName(p.type)],
  ];
  const MID_SUBJECTS = ['수학 1', '수학 2', '수학 3'];
  const subjDisp = (s) => (MID_SUBJECTS.includes(s) ? '중학교 수학' : s);
  const typeName = (t) => t;
  const TYPE_ORDER = ['선택형', '단답형'];
  let DATA = null, ALL = [], filters = {}, allOn = new Set(), excluded = new Set(), mode = null, detail = false, query = '', moreOpen = false, busy = false;
  const opts = { title: '전국연합 및 모의평가 기출 연습문제', footer: '우리는 알아야만 한다. 우리는 알게 될 것이다. - David Hilbert', layout: 'auto', sol: '1' };

  const cmp = (a, b) => a.year - b.year || a.grade - b.grade || a.month - b.month || (a.form || '').localeCompare(b.form || '', 'ko') || SEC_RANK[a.sec] - SEC_RANK[b.sec] || a.n - b.n;

  // 한 묶음(그룹)에서 '전체' 알약이 켜져 있으면 그 그룹은 제한 없음, 아니면 고른 칩만 해당. 둘 다 없으면 아직 고르지 않은 상태.
  let FN = {}, SUBJ_ORDER = [], DISP_ORDER = [];
  const isAll = (k) => allOn.has(k);
  const isSel = (k) => !!(filters[k] && filters[k].size);
  const inc = (k, v) => isAll(k) || !!(filters[k] && filters[k].has(v));
  const isActive = (k) => isAll(k) || isSel(k);
  const fieldOf = (k) => FIELDS.find((f) => f[0] === k);
  // 화면에 보이는 묶음(모드별 순서). 과목/단원 모드: 과목, 고른 과목의 단원 묶음들, 연도
  function modeKeys(m) {
    return m === 'time' ? ['grade', 'year', 'month', 'form', 'sec'] : ['subject', ...SUBJ_ORDER.map((s) => 'u:' + s), 'year'];
  }
  function shownKeys() {
    if (!mode) return [];
    const ks = modeKeys(mode).filter((k) => !(GATE[k] && !GATE[k]()));
    return moreOpen ? ks.concat(['points', 'type']) : ks;
  }
  // 실제 결과: 보이는 묶음마다 '전체' 또는 칩 선택이 있어야 하고, 고른 칩 조건을 모두 만족해야 한다
  function strictMatch(p, shown) {
    for (const k of shown) {
      if (!isActive(k)) return false;
      if (isAll(k)) continue;
      const v = FN[k](p);
      if (v === null) continue;                 // 다른 과목의 단원 묶음은 이 문제와 무관
      if (!filters[k].has(v)) return false;
    }
    return true;
  }
  const picked = () => visible().filter((p) => !excluded.has(p.id));

  // 가형/나형은 3학년+2020년, 선택과목은 3학년+2021·2022년, 단원 묶음은 그 과목을 골랐을 때만 보인다
  const GATE = {
    form: () => inc('grade', '3학년') && inc('year', '2020년'),
    sec: () => inc('grade', '3학년') && (inc('year', '2021년') || inc('year', '2022년')),
  };
  const groupTimers = {};
  let yearPreset = null;                     // null | 'all' | 5 | 3  (전체 / 최근 5개년 / 최근 3개년은 서로 겹쳐 선택되지 않는다)
  function renderFilters() {
    const box = $('filters');
    if (!mode) { box.innerHTML = ''; $('extras').innerHTML = ''; return; }
    for (const k of Object.keys(GATE)) if (!GATE[k]()) { delete filters[k]; allOn.delete(k); }   // 숨겨지는 조건은 해제
    // 묶음마다 고정된 래퍼를 두고 열고 닫는 애니메이션을 준다 (닫히는 동안 내용은 그대로 둔다)
    if (box.dataset.mode !== mode) { box.innerHTML = ''; box.dataset.mode = mode; }
    modeKeys(mode).forEach((k) => {
      let w = box.querySelector('[data-k="' + k + '"]');
      const show = !(GATE[k] && !GATE[k]());
      clearTimeout(groupTimers[k]);
      if (!w) {
        w = document.createElement('div'); w.className = 'collapse'; w.dataset.k = k;
        const inn = document.createElement('div'); inn.className = 'collapse-in'; w.appendChild(inn); box.appendChild(w);
        if (show) w.classList.add('open');          // 처음부터 열린 채로 만들어 움직임이 없게 한다
        w._fresh = true;
      }
      const inn = w.firstChild;
      if (show) {
        inn.innerHTML = ''; inn.appendChild(buildGroup(k));
        if (!w.classList.contains('open')) { void w.offsetWidth; w.classList.add('open'); }
      } else if (w.classList.contains('open')) {
        w.classList.remove('open');
        groupTimers[k] = setTimeout(() => { if (!w.classList.contains('open')) inn.innerHTML = ''; }, 360);
      }
    });
    if (moreOpen) { $('extras').innerHTML = ''; ['points', 'type'].forEach((k) => { const d = document.createElement('div'); d.appendChild(buildGroup(k)); $('extras').appendChild(d); }); }   // 닫히는 동안에는 내용을 그대로 둔다
  }
  const sameSet = (x, y) => x.size === y.size && [...x].every((v) => y.has(v));
  function buildGroup(k) {
    const UO = (DATA.units || []).map((u) => u[0] + '|' + u[1]);
    const rank = (s, u) => { const i = UO.indexOf(s + '|' + u); return i < 0 ? 999 : i; };
    const gp = document.createElement('div'); gp.className = 'gp';
    let label, f, keys;
    if (k.startsWith('u:')) {
      const s = k.slice(2); label = s; f = (p) => p.unit;
      keys = [...new Set(ALL.filter((p) => p.subject === s).map((p) => p.unit))].sort((x, y) => rank(s, x) - rank(s, y));
    } else {
      const fd = fieldOf(k); label = fd[1]; f = fd[2];
      keys = [...new Set(ALL.map(f))].filter((v) => !(k === 'form' && v === '해당 없음'));
      if (k === 'subject') keys.sort((x, y) => DISP_ORDER.indexOf(x) - DISP_ORDER.indexOf(y));
      else if (k === 'type') keys.sort((x, y) => TYPE_ORDER.indexOf(x) - TYPE_ORDER.indexOf(y));
      else if (k === 'sec') keys.sort((x, y) => SEC_RANK[x] - SEC_RANK[y]);
      else keys.sort((x, y) => String(x).localeCompare(String(y), 'ko', { numeric: true }));
    }
    const h = document.createElement('h3'); const hl = document.createElement('span'); hl.textContent = label; h.appendChild(hl);
    const pill = (text, on, fn) => { const b = document.createElement('button'); b.type = 'button'; b.className = 'allbtn' + (on ? ' on' : ''); b.textContent = text; b.onclick = fn; h.appendChild(b); };
    if (k === 'year') {
      const allLit = yearPreset === 'all' || (yearPreset === null && isAll(k));
      pill('전체', allLit, () => {
        if (allLit) { allOn.delete(k); delete filters[k]; yearPreset = null; }
        else { allOn.add(k); delete filters[k]; yearPreset = 'all'; }
        refresh();
      });
      const maxY = Math.max(...ALL.map((p) => p.year));      // 최근 N개년 (자료에 있는 가장 최근 연도 기준)
      [5, 3].forEach((n) => {
        const target = new Set(keys.filter((v) => parseInt(v, 10) > maxY - n));
        const on = yearPreset === n;
        pill('최근 ' + n + '개년', on, () => {
          if (on) { allOn.delete(k); delete filters[k]; yearPreset = null; }
          else {
            yearPreset = n;
            if (target.size === keys.length) { allOn.add(k); delete filters[k]; }
            else { allOn.delete(k); filters[k] = target; }
          }
          refresh();
        });
      });
    } else {
      pill('전체', isAll(k), () => { if (isAll(k)) allOn.delete(k); else allOn.add(k); delete filters[k]; refresh(); });
    }
    gp.appendChild(h);
    const wrap = document.createElement('div'); wrap.className = 'chips'; gp.appendChild(wrap);
    keys.forEach((v) => wrap.appendChild(chip(k, v, 0, keys, k === 'u:이산수학' && v === '선택과 배열' ? '선택과 배열(원순열)' : undefined)));   // 버튼 글씨만 다르게, 문항 정보는 그대로
    if (k === 'year') { const nt = document.createElement('div'); nt.className = 'note'; nt.textContent = '※ 수능, 모의평가는 시행 연도 기준(ex. 2027학년도 수능 → 2026년)'; gp.appendChild(nt); }
    return gp;
  }
  function chip(k, v, n, allVals, label) {
    const on = isAll(k) || !!(filters[k] && filters[k].has(v));
    const b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (on ? ' on' : '');
    const l = document.createElement('span'); l.textContent = label || v;
    b.append(l);
    b.onclick = () => {
      if (k === 'year') yearPreset = null;
      let set;
      if (isAll(k)) { allOn.delete(k); set = new Set(allVals); set.delete(v); }       // 전체 상태에서 하나를 끄면 나머지만 선택
      else { set = filters[k] || new Set(); set[on ? 'delete' : 'add'](v); }
      if (set.size && set.size === allVals.length) { allOn.add(k); delete filters[k]; }   // 전부 골랐으면 '전체'로
      else filters[k] = set;
      refresh();
    };
    return b;
  }

  function visible() { const sk = shownKeys(); return ALL.filter((p) => strictMatch(p, sk)); }

  let mainTimer = 0, extraTimer = 0;
  function renderMain() {
    const m = $('main');
    clearTimeout(mainTimer);
    if (!detail) {                                          // 접히는 애니메이션이 끝난 뒤에 내용을 비운다
      $('mainWrap').classList.remove('open');
      mainTimer = setTimeout(() => { if (!detail) m.innerHTML = ''; }, 360);
      return;
    }
    m.innerHTML = ''; $('mainWrap').classList.add('open');
    const vis = visible();                                  // 문항 목록
    const head = document.createElement('div'); head.className = 'listhead';
    head.innerHTML = '<label class="all"><input type="checkbox" id="chkAll"><span>전체</span></label>'
      + '<div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>'
      + '<input type="text" id="qBox" autocomplete="off"><button type="button" id="qClr" aria-label="전체 지우기">✕</button></div>'
      + '<span class="cnt" id="cnt"></span>';
    m.appendChild(head);
    const list = document.createElement('div'); list.className = 'list'; m.appendChild(list);
    const dg = Math.max(5, String(ALL.length).length);   // 최소 다섯 자리(만 단위) 기준
     $('cnt').style.minWidth = (2 * dg + 3) + 'ch'; $('cnt').style.textAlign = 'right';   // 최대 문항수 기준으로 폭 고정
    const label = (p) => `${p.grade}학년${p.form ? '(' + p.form + '형)' : ''} ${p.year}년 ${p.month}월 ${p.n}번`;
    const metaParts = (p) => [p.sec === '공통' ? null : p.sec, `${p.subject} › ${p.unit}`, p.points == null ? null : p.points + '점', typeName(p.type)].filter(Boolean);
    const meta = (p) => metaParts(p).join(' · ');
    let shown = [];
    const sync = () => {
      const all = $('chkAll'), n = shown.filter((p) => !excluded.has(p.id)).length;
      all.checked = shown.length > 0 && n === shown.length; all.indeterminate = n > 0 && n < shown.length; all.disabled = !shown.length;
      $('cnt').textContent = picked().length + ' / ' + vis.length;
      updateButtons();
    };
    const draw = () => {
      list.innerHTML = '';
      const toks = query.toLowerCase().split(/\s+/).filter(Boolean);
      shown = vis.filter((p) => { const hay = (label(p) + ' ' + (p.also || '') + ' ' + meta(p) + ' ' + p.summary).toLowerCase(); return toks.every((t) => hay.includes(t)); });
      if (!shown.length) { list.innerHTML = '<div style="color:var(--sub);font-size:13px;padding:8px 2px">' + (vis.length ? '검색 결과가 없어요.' : '조건에 맞는 문제가 없어요.') + '</div>'; sync(); return; }
      shown.forEach((p) => {
        const row = document.createElement('div'); row.className = 'item' + (excluded.has(p.id) ? ' off' : '');
        const c = document.createElement('input'); c.type = 'checkbox'; c.checked = !excluded.has(p.id);
        c.onchange = () => { c.checked ? excluded.delete(p.id) : excluded.add(p.id); row.className = 'item' + (c.checked ? '' : ' off'); sync(); };
        const box = document.createElement('div'); box.className = 'box';
        const t = document.createElement('div'); t.className = 't'; t.textContent = label(p);
        if (p.also) { const sm = document.createElement('small'); sm.textContent = ' (=' + p.also + ')'; t.appendChild(sm); }
        const sm = document.createElement('div'); sm.className = 's'; sm.textContent = p.summary;
        box.append(t);
        const mt = document.createElement('div'); mt.className = 'm'; mt.textContent = meta(p);
        box.append(mt, sm);
        const pv = document.createElement('button'); pv.type = 'button'; pv.className = 'pvbtn'; pv.setAttribute('aria-label', '문제 미리보기');
        pv.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9.5"/><path d="M12 7.5v9M7.5 12h9"/></svg>';
        pv.onclick = (e) => { e.stopPropagation(); openPreview(p); };
        row.append(c, box, pv);
        row.onclick = (e) => { if (e.target !== c) { c.checked = !c.checked; c.onchange(); } };
        list.appendChild(row);
      });
      sync();
    };
    $('chkAll').onchange = (e) => { shown.forEach((p) => { e.target.checked ? excluded.delete(p.id) : excluded.add(p.id); }); draw(); };
    const qb = $('qBox'); qb.value = query;
    qb.oninput = () => { query = qb.value; draw(); };
    $('qClr').onclick = () => { query = ''; qb.value = ''; draw(); qb.focus(); };
    draw();
  }
  /* ---------- 문제 미리보기 (시험 PDF의 해당 쪽을 통째로 보여준다 / pdf.js는 처음 누를 때만 불러온다) ---------- */
  const labelOf = (p) => `${p.grade}학년${p.form ? '(' + p.form + '형)' : ''} ${p.year}년 ${p.month}월 ${p.n}번`;
  let pdfjsP = null; const pdfDocs = new Map(); let pvToken = 0;
  function loadPdfjs() {
    if (!pdfjsP) pdfjsP = import('../vendor/pdf.min.mjs').then((m) => { m.GlobalWorkerOptions.workerSrc = new URL('vendor/pdf.worker.min.mjs', document.baseURI).href; return m; });
    return pdfjsP;
  }
  function getPdfDoc(file) {
    if (!pdfDocs.has(file)) pdfDocs.set(file, loadPdfjs().then((m) => m.getDocument({ url: encodeURI(file) }).promise));
    return pdfDocs.get(file);
  }
  async function openPreview(p) {
    const tok = ++pvToken, ov = $('pvOverlay'), body = $('pvBody');
    $('pvTitle').textContent = labelOf(p); body.innerHTML = '<div class="pvmsg">불러오는 중…</div>'; ov.classList.add('show');
    try {
      const file = DATA.exams[p.exam].q.file;
      const doc = await getPdfDoc(file);
      const pages = [...new Set(p.q.map((b) => b.p))];
      const cssW = Math.min(body.clientWidth - 2, 900), dpr = Math.min(window.devicePixelRatio || 1, 2);
      const frag = [];
      for (const pn of pages) {
        const page = await doc.getPage(pn + 1);
        const v0 = page.getViewport({ scale: 1 }), sc = cssW / v0.width, vp = page.getViewport({ scale: sc * dpr });
        const cv = document.createElement('canvas'); cv.width = Math.floor(vp.width); cv.height = Math.floor(vp.height);
        cv.style.width = cssW + 'px'; cv.style.height = (cv.height / dpr) + 'px';
        await page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;
        const g = cv.getContext('2d'); g.strokeStyle = 'rgba(36,86,214,.85)'; g.lineWidth = 2 * dpr;      // 이 문제 위치 표시
        p.q.filter((b) => b.p === pn).forEach((b) => { const k = sc * dpr; g.strokeRect((b.x0 - 4) * k, (b.t - 4) * k, (b.x1 - b.x0 + 8) * k, (b.b - b.t + 8) * k); });
        frag.push(cv);
      }
      if (tok !== pvToken) return;
      body.innerHTML = ''; frag.forEach((c) => body.appendChild(c));
      const first = p.q[0]; body.scrollTop = 0;
      const k = cssW / (await doc.getPage(first.p + 1)).getViewport({ scale: 1 }).width; body.scrollTop = Math.max(0, first.t * k - 60);
    } catch (err) { if (tok === pvToken) body.innerHTML = '<div class="pvmsg">미리보기를 불러오지 못했어요.<br>' + String(err.message || err) + '</div>'; }
  }
  function closePreview() { pvToken++; $('pvOverlay').classList.remove('show'); }
  function fixTotalWidth() {              // "N 문항" 칸 폭 고정 (자릿수가 달라져도 버튼이 늘었다 줄지 않게)
    const t = $('total'), cs = getComputedStyle(t), c = document.createElement('canvas').getContext('2d');
    c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
    const w = Math.max(...['0,000 문항', '8,888 문항', '1,760 문항'].map((x) => c.measureText(x).width));
    t.style.width = Math.ceil(w) + 'px'; t.style.boxSizing = 'content-box';
  }
  function updateButtons() {
    const nPick = picked().length;
    $('total').textContent = nPick.toLocaleString('ko-KR') + ' 문항';
    $('btnMake').disabled = busy || nPick === 0;
    $('btnDetail').className = detail ? 'on' : '';
    $('btnDetail').textContent = detail ? '문항 목록 닫기' : '문항 목록 열기';
    if (!animating) { $('modes').hidden = !!mode; $('wrap').hidden = !mode; $('side').hidden = !mode; }
    $('sideTitle').textContent = mode === 'time' ? '시행 연월로 찾기' : mode === 'unit' ? '과목/단원으로 찾기' : '';
    $('btnMore').className = moreOpen ? 'open' : ''; $('btnMore').setAttribute('aria-expanded', moreOpen);
    $('extrasWrap').classList.toggle('open', moreOpen);
    clearTimeout(extraTimer);
    if (!moreOpen) extraTimer = setTimeout(() => { if (!moreOpen) $('extras').innerHTML = ''; }, 360);
    if (!$('status').dataset.busy) $('status').textContent = '';
  }
  function refresh() { renderFilters(); renderMain(); updateButtons(); }
  /* 모드 버튼 → 선택 화면: 버튼이 옆 칸까지 넓어지고 높이도 선택 창에 맞춘 뒤, 뒤에 깔린 선택 창이 보이도록 버튼이 서서히 사라진다. 뒤로 가기는 그 역순. */
  let animating = false;
  const reduceMotion = () => window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const nextFrame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  async function setMode(m) {
    if (animating) return;
    if (reduceMotion()) { mode = m; yearPreset = null; refresh(); return; }
    animating = true;
    const modes = $('modes'), wrap = $('wrap'), side = $('side');
    const me = $(m === 'time' ? 'modeTime' : 'modeUnit'), other = $(m === 'time' ? 'modeUnit' : 'modeTime');
    mode = m; yearPreset = null;
    wrap.hidden = false; side.hidden = false; wrap.classList.add('measure');
    refresh();                                               // 선택 창은 보이지 않는 채로 크기만 잰다 (뒤에 깔아두지 않는다)
    const H = side.getBoundingClientRect().height;
    const h0 = me.getBoundingClientRect().height;
    [me, other].forEach((b) => { b.style.aspectRatio = 'auto'; b.style.height = h0 + 'px'; });
    me.classList.add('fading'); other.classList.add('fading', 'gone');
    void modes.offsetWidth;
    modes.classList.add(m === 'time' ? 'go-left' : 'go-right');
    [me, other].forEach((b) => { b.style.height = H + 'px'; });
    me.style.borderRadius = '10px';
    await wait(450);
    // 버튼이 선택 창과 똑같은 크기로 다 커진 순간: 같은 자리에서 버튼을 치우고 선택 창을 놓고, 글씨만 서서히 나타낸다
    modes.hidden = true; modes.className = 'modes'; [me, other].forEach((b) => { b.className = ''; b.style.cssText = ''; });
    wrap.classList.remove('measure'); side.classList.add('reveal');
    animating = false; refresh();
    await wait(480);
    side.classList.remove('reveal');
  }
  function resetState() { mode = null; detail = false; filters = {}; allOn = new Set(); excluded = new Set(); query = ''; moreOpen = false; yearPreset = null; }
  async function goHome() {
    if (animating) return;
    if (reduceMotion() || !mode) { resetState(); refresh(); return; }
    animating = true;
    const modes = $('modes'), wrap = $('wrap'), side = $('side'), m = mode;
    const me = $(m === 'time' ? 'modeTime' : 'modeUnit'), other = $(m === 'time' ? 'modeUnit' : 'modeTime');
    const H = side.getBoundingClientRect().height;
    wrap.classList.add('fadeout');                                   // 선택 창 글씨(와 목록)만 서서히 지운다
    await wait(330);
    // 빈 선택 창과 같은 크기의 버튼으로 같은 자리에서 바꿔치기
    modes.classList.add('notrans', m === 'time' ? 'go-left' : 'go-right');
    me.classList.add('fading'); other.classList.add('fading', 'gone');
    [me, other].forEach((b) => { b.style.aspectRatio = 'auto'; b.style.height = H + 'px'; });
    me.style.borderRadius = '10px';
    modes.hidden = false; wrap.hidden = true;
    void modes.offsetWidth; modes.classList.remove('notrans');
    await nextFrame();
    const sq = (modes.getBoundingClientRect().width - 10) / 2;       // 다시 정사각형 두 칸으로 줄어든다
    modes.classList.remove('go-left', 'go-right');
    me.classList.remove('fading'); other.classList.remove('fading', 'gone');
    [me, other].forEach((b) => { b.style.height = sq + 'px'; }); me.style.borderRadius = '';
    await wait(450);
    modes.className = 'modes'; [me, other].forEach((b) => { b.className = ''; b.style.cssText = ''; });
    wrap.classList.remove('fadeout');
    resetState(); animating = false; refresh();
  }

  /* ---------- 양식 편집 팝업 ---------- */
  function openForm() {
    $('optTitle').value = opts.title; $('optFooter').value = opts.footer; $('optLayout').value = opts.layout; $('optSol').value = opts.sol;
    $('overlay').classList.add('show'); if (document.activeElement) document.activeElement.blur();
  }
  function closeForm(save) {
    if (save) { opts.title = $('optTitle').value; opts.footer = $('optFooter').value; opts.layout = $('optLayout').value; opts.sol = $('optSol').value; }
    $('overlay').classList.remove('show'); $('btnForm').focus();
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && $('pvOverlay').classList.contains('show')) { closePreview(); return; }
    if (!$('overlay').classList.contains('show')) return;
    if (e.key === 'Escape') { e.preventDefault(); closeForm(false); }
    else if (e.key === 'Enter') { e.preventDefault(); closeForm(true); }
  });

  /* ---------- PDF 생성 ---------- */
  function loadScript(src) { return new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = rej; document.head.appendChild(s); }); }
  async function ensurePdfLib() {
    if (window.PDFLib) return;
    for (const u of ['vendor/pdf-lib.min.js', 'https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js', 'https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js']) {
      try { await loadScript(u); if (window.PDFLib) return; } catch (e) { /* 다음 후보 */ }
    }
    throw new Error('pdf-lib 를 불러오지 못했어요 (vendor/pdf-lib.min.js 를 넣거나 인터넷 연결을 확인하세요)');
  }

  const TEXT_S = 4;   // 글자 이미지 해상도 배율
  function textImage(op) {
    const font = `${op.italic ? 'italic ' : ''}${op.bold ? 'bold ' : ''}${op.size * TEXT_S}px ${getComputedStyle(document.body).fontFamily}`;
    const c = document.createElement('canvas'); const g = c.getContext('2d');
    g.font = font; const w = Math.ceil(g.measureText(op.s).width) + 4;
    c.width = w; c.height = Math.ceil(op.size * 1.5 * TEXT_S);
    const g2 = c.getContext('2d'); g2.font = font; g2.fillStyle = '#000'; g2.textBaseline = 'alphabetic';
    g2.fillText(op.s, 2, op.size * 1.15 * TEXT_S);
    return new Promise((res) => c.toBlob(async (b) => res({ bytes: new Uint8Array(await b.arrayBuffer()), wpt: w / TEXT_S, hpt: c.height / TEXT_S }), 'image/png'));
  }

  async function renderPlan(plan, onProgress) {
    const { PDFDocument, StandardFonts, rgb } = PDFLib;
    const PH = Layout.PAGE.h;
    const out = await PDFDocument.create();
    const fonts = { n: await out.embedFont(StandardFonts.Helvetica), b: await out.embedFont(StandardFonts.HelveticaBold) };
    const srcDocs = new Map(), imgCache = new Map(), embCache = new Map();
    const getSrc = async (file) => {
      if (!srcDocs.has(file)) {
        const r = await fetch(encodeURI(file)); if (!r.ok) throw new Error(file + ' 를 불러오지 못했어요');
        srcDocs.set(file, await PDFDocument.load(await r.arrayBuffer()));
      }
      return srcDocs.get(file);
    };
    const need = new Map();                            // 파일 -> 쓰는 쪽 번호
    plan.pages.forEach((pg) => pg.ops.forEach((op) => { if (op.t === 'crop') { if (!need.has(op.file)) need.set(op.file, new Set()); need.get(op.file).add(op.page); } }));
    for (const [file, set] of need) {
      const src = await getSrc(file), pages = [...set].sort((x, y) => x - y);
      const embs = await out.embedPages(pages.map((p) => src.getPage(p)));
      pages.forEach((p, i) => embCache.set(file + '|' + p, embs[i]));
    }
    let done = 0;
    for (const pg of plan.pages) {
      const page = out.addPage([Layout.PAGE.w, PH]);
      for (const op of pg.ops) {
        if (op.t === 'line') {
          page.drawLine({ start: { x: op.x1, y: PH - op.y1 }, end: { x: op.x2, y: PH - op.y2 }, thickness: op.w, color: rgb(0, 0, 0) });
        } else if (op.t === 'rect') {
          const o = { x: op.x, y: PH - op.y - op.h, width: op.w, height: op.h };
          if (op.fill) o.color = rgb(1, 1, 1);
          if (op.stroke) { o.borderColor = rgb(0, 0, 0); o.borderWidth = op.sw || 0.6; }
          page.drawRectangle(o);
        } else if (op.t === 'text') {
          if (/^[\x20-\x7e]*$/.test(op.s) && !op.italic) {          // 영문·숫자만이면 기본 글꼴
            const f = op.bold ? fonts.b : fonts.n; let size = op.size, w = f.widthOfTextAtSize(op.s, size);
            if (op.maxW && w > op.maxW) { size = size * op.maxW / w; w = op.maxW; }
            const x = op.align === 'center' ? op.x - w / 2 : op.align === 'right' ? op.x - w : op.x;
            page.drawText(op.s, { x, y: PH - op.y, size, font: f });
          } else {                                                   // 한글 등은 캔버스로 그려 이미지로 삽입
            const key = [op.s, op.size, op.bold, op.italic].join('|');
            if (!imgCache.has(key)) { const t = await textImage(op); imgCache.set(key, { ...t, img: await out.embedPng(t.bytes) }); }
            const t = imgCache.get(key);
            const k = op.maxW && t.wpt > op.maxW ? op.maxW / t.wpt : 1;       // 칸보다 길면 글자를 줄여 맞춘다
            const wpt = t.wpt * k, hpt = t.hpt * k;
            const x = op.align === 'center' ? op.x - wpt / 2 : op.align === 'right' ? op.x - wpt : op.x - 0.5;
            page.drawImage(t.img, { x, y: PH - op.y - 0.35 * op.size * k, width: wpt, height: hpt });
          }
        } else if (op.t === 'crop') {
          const key = op.file + '|' + op.page;           // 원본 쪽은 파일별로 한꺼번에 한 번만 넣고(글꼴·그림 중복 방지), 필요한 부분만 잘라(클리핑) 그린다 -> 용량 절약
          const emb = embCache.get(key);
          const [x0, t, x1, b] = op.src;
          const [dx, dy, dw, dh] = op.dest;
          const s = dw / (x1 - x0), by = PH - dy - dh;
          page.pushOperators(PDFLib.pushGraphicsState(), PDFLib.rectangle(dx, by, dw, dh), PDFLib.clip(), PDFLib.endPath());
          page.drawPage(emb, { x: dx - x0 * s, y: by - (op.ph - b) * s, xScale: s, yScale: s });
          page.pushOperators(PDFLib.popGraphicsState());
        }
      }
      onProgress && onProgress(++done, plan.pages.length);
    }
    return out.save();
  }

  const CIRC = 2 * Math.PI * 42;
  function setProgress(r) {
    $('ringFg').style.strokeDashoffset = CIRC * (1 - Math.max(0, Math.min(1, r)));
    $('ringTxt').textContent = Math.round(r * 100) + '%';
  }
  function showBusy(on, msg) {
    $('busy').classList.toggle('show', on); $('busyMsg').textContent = msg || 'PDF 생성중입니다';
    $('busy').classList.remove('err'); if (on) setProgress(0);
  }
  async function make() {
    $('btnMake').disabled = true; busy = true; showBusy(true);
    try {
      await ensurePdfLib(); setProgress(0.03);
      const list = picked().sort(cmp);
      const plan = Layout.buildPlan(list, DATA.exams, {
        title: opts.title, footer: opts.footer, layout: opts.layout, solutions: opts.sol !== '0', answersOnly: opts.sol === '2',
      });
      setProgress(0.05);
      const bytes = await renderPlan(plan, (d, n) => setProgress(0.05 + 0.9 * d / n));
      setProgress(1);
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      const a = document.createElement('a'); a.href = url; a.download = (opts.title || '문제지') + '.pdf'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      await new Promise((r) => setTimeout(r, 350)); showBusy(false);
    } catch (e) {
      console.error(e); showBusy(true, '오류: ' + e.message); $('busy').classList.add('err');
    } finally { busy = false; updateButtons(); }
  }

  /* 우클릭 메뉴, 드래그 시작, 글자 선택 시작 차단 (입력칸은 제외) */
  ['contextmenu', 'dragstart', 'selectstart'].forEach((t) => document.addEventListener(t, (e) => {
    if (t === 'selectstart' && e.target && e.target.closest && e.target.closest('input, textarea, select')) return;
    e.preventDefault();
  }));

  /* 스크롤바 표시: 스크롤 중이거나(1초), 마우스가 화면 오른쪽 끝에 있을 때만 */
  (function () {
    const timers = new Map();
    const show = (el) => { el.classList.add('sb'); clearTimeout(timers.get(el)); timers.set(el, setTimeout(() => el.classList.remove('sb'), 1000)); };
    document.addEventListener('scroll', (e) => show(e.target === document ? document.documentElement : e.target), true);
    document.addEventListener('mousemove', (e) => { if (e.clientX >= document.documentElement.clientWidth - 2) show(document.documentElement); });
  })();

  /* 헤더: 제목 대문자 높이를 재서 상자 높이로 쓰고, 각 글씨의 기준선이 상자 아래에 오도록 맞춘다 */
  function alignHeader() {
    const h1 = document.querySelector('header h1'), meta = document.querySelector('header .meta');
    const tx = h1.querySelector('.tx'), cs = getComputedStyle(h1);
    const c = document.createElement('canvas').getContext('2d');
    c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const m = c.measureText('MATH BANK');
    const H = Math.round((m.actualBoundingBoxAscent + m.actualBoundingBoxDescent) * 10) / 10;
    const hd = document.querySelector('header'); hd.style.setProperty('--th', H + 'px');
    [h1, meta].forEach((box) => {
      const t = box.querySelector('.tx'), p = t.querySelector('.bl');
      box.style.setProperty('--d', '0px');
      const d = t.getBoundingClientRect().bottom - p.getBoundingClientRect().bottom;   // 기준선에서 글자줄 아래까지 거리
      box.style.setProperty('--d', d + 'px');
    });
  }
  alignHeader(); fixTotalWidth();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(alignHeader);

  async function init() {
    const r = await fetch('data/problems.json', { cache: 'no-cache' }); DATA = await r.json();
    ALL = DATA.problems.slice().sort(cmp);
    SUBJ_ORDER = [...new Set((DATA.units || []).map((u) => u[0]))];                // 성취기준 파일 순서
    ALL.forEach((p) => { if (!SUBJ_ORDER.includes(p.subject)) SUBJ_ORDER.push(p.subject); });
    const ix = SUBJ_ORDER.indexOf('확률과 통계'), at = SUBJ_ORDER.indexOf('대수');   // 확률과 통계를 대수 바로 다음에
    if (ix >= 0 && at >= 0) { SUBJ_ORDER.splice(ix, 1); SUBJ_ORDER.splice(SUBJ_ORDER.indexOf('대수') + 1, 0, '확률과 통계'); }
    DISP_ORDER = [...new Set(SUBJ_ORDER.map(subjDisp))];
    SUBJ_ORDER.forEach((s) => { FIELDS.push(['u:' + s, s, (p) => (p.subject === s ? p.unit : null)]); GATE['u:' + s] = () => inc('subject', subjDisp(s)); });
    FN = Object.fromEntries(FIELDS.map((f) => [f[0], f[2]]));
    $('modeTime').onclick = () => setMode('time'); $('modeUnit').onclick = () => setMode('unit');
    $('btnDetail').onclick = () => { detail = !detail; refresh(); };
    $('total').style.minWidth = (Math.max(5, String(ALL.length).length) + 3) + 'ch';   // 숫자가 바뀌어도 버튼 폭이 흔들리지 않게
    $('btnMake').onclick = make; $('btnMore').onclick = () => { moreOpen = !moreOpen; if (moreOpen) { allOn.add('points'); allOn.add('type'); } else { ['points', 'type'].forEach((k) => { delete filters[k]; allOn.delete(k); }); } refresh(); }; $('pvClose').onclick = closePreview; $('pvOverlay').onclick = (e) => { if (e.target === $('pvOverlay')) closePreview(); };
    $('btnBack').onclick = goHome;
    $('btnForm').onclick = openForm;
    $('mOk').onclick = () => closeForm(true); $('mCancel').onclick = () => closeForm(false); $('mX').onclick = () => closeForm(false);
    $('busy').addEventListener('click', () => { if (!busy) showBusy(false); });
    $('overlay').addEventListener('mousedown', (e) => { if (e.target === $('overlay')) closeForm(false); });
    refresh();
  }
  init().catch((e) => { $('status').textContent = '데이터를 불러오지 못했어요: ' + e.message + ' (로컬에서 열 땐 python -m http.server 로 실행하세요)'; });
})();
