/* 문제은행 화면 + PDF 조립(pdf-lib).  레이아웃 계산은 js/layout.js 가 담당한다. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const SEC_RANK = { '공통': 0, '확률과 통계': 1, '미적분': 2, '기하': 3 };
  const FIELDS = [   // [키, 이름, 값 함수, 분류(time=출제 시기별 / unit=단원별)]
    ['grade', '학년', (p) => p.grade + '학년', 'time'],
    ['year', '연도', (p) => p.year + '년', 'time'],
    ['month', '월', (p) => p.month + '월', 'time'],
    ['form', '가형/나형', (p) => (p.form ? p.form + '형' : '해당 없음'), 'time'],
    ['sec', '선택', (p) => p.sec, 'time'],
    ['subject', '과목', (p) => p.subject, 'unit'],
    ['unit', '단원', (p) => p.subject + '|' + p.unit, 'unit'],
    ['points', '배점', (p) => (p.points == null ? '-' : p.points + '점'), 'extra'],
    ['type', '문제 유형', (p) => typeName(p.type), 'extra'],
  ];
  const typeName = (t) => (t === '선택형' ? '5지선다형' : t);
  const TYPE_ORDER = ['5지선다형', '단답형'];
  let DATA = null, ALL = [], filters = {}, allOn = new Set(), excluded = new Set(), mode = null, detail = false, query = '', moreOpen = false, busy = false;
  const opts = { title: '전국연합 및 모의평가 기출 연습문제', footer: '우리는 알아야만 한다. 우리는 알게 될 것이다. - David Hilbert', layout: 'auto', sol: '1' };

  const cmp = (a, b) => a.year - b.year || a.grade - b.grade || a.month - b.month || (a.form || '').localeCompare(b.form || '', 'ko') || SEC_RANK[a.sec] - SEC_RANK[b.sec] || a.n - b.n;

  // 한 묶음(그룹)에서 '전체' 알약이 켜져 있으면 그 그룹은 제한 없음, 아니면 고른 칩만 해당. 둘 다 없으면 아직 고르지 않은 상태.
  const REQ = [['grade'], ['year'], ['month'], ['form'], ['sec'], ['subject', 'unit'], ['points'], ['type']];
  const FN = Object.fromEntries(FIELDS.map((f) => [f[0], f[2]]));
  const isAll = (k) => allOn.has(k);
  const isSel = (k) => !!(filters[k] && filters[k].size);
  const isActive = (k) => isAll(k) || isSel(k);
  // 칩 개수 계산용: 고르지 않은 그룹은 제한 없음으로 본다
  function matches(p, skip) {
    for (const k of Object.keys(FN)) {
      if (k === skip || isAll(k)) continue;
      const set = filters[k];
      if (set && set.size && !set.has(FN[k](p))) return false;
    }
    return true;
  }
  const fieldCat = (k) => FIELDS.find((f) => f[0] === k)[3];
  // 지금 화면에 보이는 그룹
  function shownKeys() {
    if (!mode) return [];
    return FIELDS.filter((f) => (f[3] === mode || (moreOpen && f[3] === 'extra')) && !(GATE[f[0]] && !GATE[f[0]]())).map((f) => f[0]);
  }
  // 실제 결과: 보이는 그룹마다 '전체' 또는 칩 선택이 있어야 하고, 고른 칩 조건을 모두 만족해야 한다
  function strictMatch(p, shown) {
    for (const grp of REQ) {
      const ks = grp.filter((k) => shown.includes(k));
      if (!ks.length) continue;
      if (!ks.some(isActive)) return false;
      for (const k of ks) { if (isAll(k)) continue; const set = filters[k]; if (set && set.size && !set.has(FN[k](p))) return false; }
    }
    return true;
  }
  const picked = () => visible().filter((p) => !excluded.has(p.id));

  // 가형/나형, 선택은 학년을 골랐고 그 조건에 해당 문제가 있을 때만 보인다
  const GATE = {
    form: () => isActive('grade') && ALL.some((p) => p.form && matches(p, 'form')),
    sec: () => isActive('grade') && ALL.some((p) => p.sec !== '공통' && matches(p, 'sec')),
  };
  function renderFilters() {
    const box = $('filters'); box.innerHTML = ''; $('extras').innerHTML = '';
    if (!mode) return;
    for (const k of Object.keys(GATE)) if (!GATE[k]()) { delete filters[k]; allOn.delete(k); }   // 숨겨지는 조건은 해제
    renderGroups(box, FIELDS.filter((f) => f[3] === mode));
    if (moreOpen) FIELDS.filter((f) => f[3] === 'extra').forEach((fd) => { const d = document.createElement('div'); renderGroups(d, [fd]); $('extras').appendChild(d); });
  }
  function renderGroups(box, fields) {
    fields.forEach(([k, label, f]) => {
      if (GATE[k] && !GATE[k]()) return;
      const h = document.createElement('h3'); const hl = document.createElement('span'); hl.textContent = label; h.appendChild(hl);
      const ab = document.createElement('button'); ab.type = 'button'; ab.className = 'allbtn' + (isAll(k) ? ' on' : ''); ab.textContent = '전체';
      h.appendChild(ab); box.appendChild(h);
      const counts = new Map();
      ALL.forEach((p) => { if (matches(p, k)) counts.set(f(p), (counts.get(f(p)) || 0) + 1); });
      const keys = [...new Set(ALL.map(f))].filter((v) => !(k === 'form' && v === '해당 없음'));
      ab.onclick = () => { if (isAll(k)) allOn.delete(k); else allOn.add(k); delete filters[k]; refresh(); };
      const UO = (DATA.units || []).map((u) => u[0] + '|' + u[1]);
      const rank = (v) => { const i = UO.indexOf(v); return i < 0 ? 999 : i; };
      let wrap = document.createElement('div'); wrap.className = 'chips'; box.appendChild(wrap);
      if (k === 'unit') {                       // 단원은 과목별로 묶어서 표시 (성취기준 파일 순서)
        keys.sort((a, b) => rank(a) - rank(b));
        box.removeChild(wrap); let last = null;
        keys.forEach((v) => {
          const [sub, un] = v.split('|');
          if (sub !== last) { const g = document.createElement('div'); g.className = 'grp'; g.textContent = sub; box.appendChild(g); wrap = document.createElement('div'); wrap.className = 'chips'; box.appendChild(wrap); last = sub; }
          wrap.appendChild(chip(k, v, counts.get(v) || 0, keys, un));
        });
        return;
      }
      if (k === 'subject') keys.sort((a, b) => Math.min(...UO.map((u, i) => (u.split('|')[0] === a ? i : 999))) - Math.min(...UO.map((u, i) => (u.split('|')[0] === b ? i : 999))));
      else if (k === 'type') keys.sort((x, y) => TYPE_ORDER.indexOf(x) - TYPE_ORDER.indexOf(y));
      else if (k === 'sec') keys.sort((x, y) => SEC_RANK[x] - SEC_RANK[y]);
      else keys.sort((a, b) => String(a).localeCompare(String(b), 'ko', { numeric: true }));
      keys.forEach((v) => wrap.appendChild(chip(k, v, counts.get(v) || 0, keys)));
    });
  }
  function chip(k, v, n, allVals, label) {
    const on = isAll(k) || !!(filters[k] && filters[k].has(v));
    const b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (on ? ' on' : '') + (n === 0 && !on ? ' zero' : '');
    const l = document.createElement('span'); l.textContent = label || v;
    const c = document.createElement('span'); c.className = 'n'; c.textContent = n;
    const maxN = ALL.reduce((s, p) => s + (FN[k](p) === v ? 1 : 0), 0);          // 이 칸에 들어갈 수 있는 가장 큰 수 기준으로 폭 고정
    c.style.minWidth = 'calc(' + String(maxN).length + 'ch + 14px)';
    b.append(l, c);
    b.onclick = () => {
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

  function renderMain() {
    const m = $('main'); m.innerHTML = '';
    if (!detail) { $('main').hidden = true; return; }
    $('main').hidden = false;
    const vis = visible();                                  // 문항 목록
    const head = document.createElement('div'); head.className = 'listhead';
    head.innerHTML = '<label class="all"><input type="checkbox" id="chkAll"><span>전체선택</span></label>'
      + '<div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>'
      + '<input type="text" id="qBox" autocomplete="off"><button type="button" id="qClr" aria-label="전체 지우기">✕</button></div>'
      + '<span class="cnt" id="cnt"></span>';
    m.appendChild(head);
    const list = document.createElement('div'); list.className = 'list'; m.appendChild(list);
    const label = (p) => `${p.grade}학년${p.form ? '(' + p.form + '형)' : ''} ${p.year}년 ${p.month}월 ${p.n}번`;
    const metaParts = (p) => [p.sec === '공통' ? null : p.sec, `${p.subject} › ${p.unit}`, p.points == null ? null : p.points + '점', typeName(p.type)].filter(Boolean);
    const meta = (p) => metaParts(p).join(' ');
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
        const vb = () => { const i = document.createElement('i'); i.className = 'vb'; return i; };
        const sm = document.createElement('div'); sm.className = 's'; sm.textContent = p.summary;
        box.append(t);
        const parts = metaParts(p);
        parts.forEach((s, ix) => { const e = document.createElement('div'); e.className = ix === (p.sec === '공통' ? 0 : 1) ? 'u' : 'k'; e.textContent = s; box.append(vb(), e); });
        box.append(vb(), sm); row.append(c, box);
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
  function updateButtons() {
    $('btnMake').disabled = busy || picked().length === 0;
    $('btnDetail').className = detail ? 'on' : '';
    $('btnDetail').textContent = detail ? '문항 목록 닫기' : '문항 목록 열기';
    $('modes').hidden = !!mode; $('sideTitle').textContent = mode === 'time' ? '시행 연월로 찾기' : mode === 'unit' ? '과목/단원으로 찾기' : '';
    $('btnMore').className = moreOpen ? 'open' : ''; $('btnMore').setAttribute('aria-expanded', moreOpen);
    $('extras').hidden = !moreOpen;
    $('wrap').hidden = !mode; $('side').hidden = !mode;
    if (!$('status').dataset.busy) $('status').textContent = '';
  }
  function refresh() { renderFilters(); renderMain(); updateButtons(); }
  function setMode(m) { mode = m; refresh(); }
  function goHome() { mode = null; detail = false; filters = {}; allOn = new Set(); excluded = new Set(); query = ''; moreOpen = false; refresh(); }

  /* ---------- 양식 편집 팝업 ---------- */
  function openForm() {
    $('optTitle').value = opts.title; $('optFooter').value = opts.footer; $('optLayout').value = opts.layout; $('optSol').value = opts.sol;
    $('overlay').classList.add('show'); $('optTitle').focus(); $('optTitle').select();
  }
  function closeForm(save) {
    if (save) { opts.title = $('optTitle').value; opts.footer = $('optFooter').value; opts.layout = $('optLayout').value; opts.sol = $('optSol').value; }
    $('overlay').classList.remove('show'); $('btnForm').focus();
  }
  document.addEventListener('keydown', (e) => {
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
    const font = `${op.italic ? 'italic ' : ''}${op.bold ? 'bold ' : ''}${op.size * TEXT_S}px "Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif`;
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

  async function init() {
    const r = await fetch('data/problems.json'); DATA = await r.json();
    ALL = DATA.problems.slice().sort(cmp);
    $('modeTime').onclick = () => setMode('time'); $('modeUnit').onclick = () => setMode('unit');
    $('btnDetail').onclick = () => { detail = !detail; refresh(); };
    $('btnMake').onclick = make; $('btnMore').onclick = () => { moreOpen = !moreOpen; if (moreOpen) { allOn.add('points'); allOn.add('type'); } else { ['points', 'type'].forEach((k) => { delete filters[k]; allOn.delete(k); }); } refresh(); }; $('btnBack').onclick = goHome;
    $('btnForm').onclick = openForm;
    $('mOk').onclick = () => closeForm(true); $('mCancel').onclick = () => closeForm(false); $('mX').onclick = () => closeForm(false);
    $('busy').addEventListener('click', () => { if (!busy) showBusy(false); });
    $('overlay').addEventListener('mousedown', (e) => { if (e.target === $('overlay')) closeForm(false); });
    refresh();
  }
  init().catch((e) => { $('status').textContent = '데이터를 불러오지 못했어요: ' + e.message + ' (로컬에서 열 땐 python -m http.server 로 실행하세요)'; });
})();
