/* 문제은행 화면 + PDF 조립(pdf-lib).  레이아웃 계산은 js/layout.js 가 담당한다. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const SEC_RANK = { '공통': 0, '확률과 통계': 1, '미적분': 2, '기하': 3 };
  const FIELDS = [   // [키, 이름, 값 함수, 분류(time=출제 시기별 / unit=단원별)]
    ['year', '연도', (p) => p.year + '년', 'time'],
    ['grade', '학년', (p) => p.grade + '학년', 'time'],
    ['month', '시행월', (p) => p.month + '월', 'time'],
    ['form', '형(가/나)', (p) => (p.form ? p.form + '형' : '해당 없음'), 'time'],
    ['sec', '구분', (p) => p.sec, 'time'],
    ['subject', '과목', (p) => p.subject, 'unit'],
    ['unit', '단원', (p) => p.subject + '|' + p.unit, 'unit'],
    ['points', '배점', (p) => (p.points == null ? '-' : p.points + '점'), 'unit'],
    ['type', '형식', (p) => p.type, 'unit'],
  ];
  let DATA = null, ALL = [], filters = {}, excluded = new Set(), mode = 'time', detail = false;
  const opts = { title: '전국연합 학력평가 단원별 연습', footer: '우리는 알아야만 한다. 우리는 알게 될 것이다. - David Hilbert', layout: 'auto', sol: '1' };

  const cmp = (a, b) => a.year - b.year || a.grade - b.grade || a.month - b.month || (a.form || '').localeCompare(b.form || '', 'ko') || SEC_RANK[a.sec] - SEC_RANK[b.sec] || a.n - b.n;

  function matches(p, skip) {
    for (const [k, , f] of FIELDS) {
      if (k === skip) continue;
      const set = filters[k];
      if (set && set.size && !set.has(f(p))) return false;
    }
    return true;
  }

  const activeCount = () => Object.values(filters).reduce((n, st) => n + (st ? st.size : 0), 0);
  const picked = () => visible().filter((p) => !excluded.has(p.id));

  function renderFilters() {
    const box = $('filters'); box.innerHTML = '';
    FIELDS.filter((f) => f[3] === mode).forEach(([k, label, f]) => {
      const h = document.createElement('h3'); h.textContent = label; box.appendChild(h);
      const counts = new Map();
      ALL.forEach((p) => { if (matches(p, k)) counts.set(f(p), (counts.get(f(p)) || 0) + 1); });
      const keys = [...new Set(ALL.map(f))];
      const UO = (DATA.units || []).map((u) => u[0] + '|' + u[1]);
      const rank = (v) => { const i = UO.indexOf(v); return i < 0 ? 999 : i; };
      let wrap = document.createElement('div'); wrap.className = 'chips'; box.appendChild(wrap);
      if (k === 'unit') {                       // 단원은 과목별로 묶어서 표시 (성취기준 파일 순서)
        keys.sort((a, b) => rank(a) - rank(b));
        box.removeChild(wrap); let last = null;
        keys.forEach((v) => {
          const [sub, un] = v.split('|');
          if (sub !== last) { const g = document.createElement('div'); g.className = 'grp'; g.textContent = sub; box.appendChild(g); wrap = document.createElement('div'); wrap.className = 'chips'; box.appendChild(wrap); last = sub; }
          wrap.appendChild(chip(k, v, counts.get(v) || 0, un));
        });
        return;
      }
      if (k === 'subject') keys.sort((a, b) => Math.min(...UO.map((u, i) => (u.split('|')[0] === a ? i : 999))) - Math.min(...UO.map((u, i) => (u.split('|')[0] === b ? i : 999))));
      else keys.sort((a, b) => String(a).localeCompare(String(b), 'ko', { numeric: true }));
      keys.forEach((v) => wrap.appendChild(chip(k, v, counts.get(v) || 0)));
    });
  }
  function chip(k, v, n, label) {
    const on = !!(filters[k] && filters[k].has(v));
    const b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (on ? ' on' : '') + (n === 0 && !on ? ' zero' : '');
    const l = document.createElement('span'); l.textContent = label || v;
    const c = document.createElement('span'); c.className = 'n'; c.textContent = n;
    b.append(l, c);
    b.onclick = () => { (filters[k] = filters[k] || new Set())[on ? 'delete' : 'add'](v); refresh(); };
    return b;
  }

  function visible() { return ALL.filter((p) => matches(p, null)); }

  function renderMain() {
    const m = $('main'); m.innerHTML = '';
    if (!detail) {                                          // 조건 요약
      const d = document.createElement('div'); d.className = 'sum';
      d.innerHTML = '<h3>선택한 조건</h3>';
      if (!activeCount()) {
        const t = document.createElement('div'); t.className = 'hint';
        t.innerHTML = '왼쪽 메뉴에서 조건을 골라보세요.<br>출제 시기별과 단원별 조건은 함께 적용돼요.<br>조건을 고른 뒤 <b>PDF 만들기</b>를 누르면 조건에 맞는 문제로 문제지가 만들어지고, <b>세부 설정</b>에서는 문제를 하나씩 빼거나 넣을 수 있어요.';
        d.appendChild(t);
      } else {
        FIELDS.forEach(([k, label, f]) => {
          const st = filters[k]; if (!st || !st.size) return;
          const r = document.createElement('div'); r.className = 'rowx';
          const b = document.createElement('b'); b.textContent = label; r.appendChild(b);
          [...st].forEach((v) => {
            const c = document.createElement('button'); c.className = 'chip on'; c.type = 'button';
            c.textContent = (k === 'unit' ? v.split('|')[1] : v) + '  ✕';
            c.onclick = () => { st.delete(v); refresh(); };
            r.appendChild(c);
          });
          d.appendChild(r);
        });
        const reset = document.createElement('button'); reset.className = 'linkbtn'; reset.textContent = '조건 모두 해제';
        reset.onclick = () => { filters = {}; refresh(); };
        d.appendChild(reset);
      }
      m.appendChild(d); return;
    }
    const vis = visible();                                  // 세부 설정: 문제 목록
    const head = document.createElement('div'); head.className = 'listhead';
    head.innerHTML = '<span>문제 목록 · 체크된 문제가 PDF에 들어가요</span><span>' + picked().length + ' / ' + vis.length + '</span>';
    m.appendChild(head);
    const list = document.createElement('div'); list.className = 'list'; m.appendChild(list);
    if (!vis.length) { list.innerHTML = '<div class="hint" style="color:var(--sub);font-size:13px;padding:8px 2px">조건에 맞는 문제가 없어요.</div>'; return; }
    vis.forEach((p) => {
      const row = document.createElement('div'); row.className = 'item' + (excluded.has(p.id) ? ' off' : '');
      const c = document.createElement('input'); c.type = 'checkbox'; c.checked = !excluded.has(p.id);
      c.onchange = () => { c.checked ? excluded.delete(p.id) : excluded.add(p.id); row.className = 'item' + (c.checked ? '' : ' off'); head.lastChild.textContent = picked().length + ' / ' + vis.length; updateButtons(); };
      const box = document.createElement('div');
      const t = document.createElement('div'); t.className = 't';
      t.textContent = `${p.year}년 ${p.month}월 ${p.grade}학년${p.form ? '(' + p.form + '형)' : ''} ${p.n}번`;
      if (p.also) { const sm = document.createElement('small'); sm.textContent = ' (=' + p.also + ')'; t.appendChild(sm); }
      const mt = document.createElement('div'); mt.className = 'm';
      mt.textContent = [p.sec === '공통' ? null : p.sec, `${p.subject} › ${p.unit}`, p.points == null ? null : p.points + '점', p.type].filter(Boolean).join(' · ');
      const sm = document.createElement('div'); sm.className = 's'; sm.textContent = p.summary;
      box.append(t, mt, sm); row.append(c, box);
      row.onclick = (e) => { if (e.target !== c) { c.checked = !c.checked; c.onchange(); } };
      list.appendChild(row);
    });
  }
  function updateButtons() {
    $('btnMake').disabled = !activeCount() || picked().length === 0;
    $('btnDetail').className = detail ? 'on' : '';
    $('btnDetail').textContent = detail ? '세부 설정 닫기' : '세부 설정';
    $('modeTime').className = mode === 'time' ? 'on' : ''; $('modeUnit').className = mode === 'unit' ? 'on' : '';
    if (!$('status').dataset.busy) $('status').textContent = activeCount() ? '' : '조건을 먼저 선택하세요';
  }
  function refresh() { renderFilters(); renderMain(); updateButtons(); }
  function setMode(m) { mode = m; detail = false; refresh(); }

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

  async function make() {
    const btn = $('btnMake'); btn.disabled = true; $('status').dataset.busy = '1';
    try {
      $('status').textContent = 'PDF 라이브러리 준비 중…';
      await ensurePdfLib();
      const list = picked().sort(cmp);
      const plan = Layout.buildPlan(list, DATA.exams, {
        title: opts.title, footer: opts.footer, layout: opts.layout, solutions: opts.sol === '1',
      });
      const bytes = await renderPlan(plan, (d, n) => { $('status').textContent = `만드는 중… ${d}/${n}쪽`; });
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      const a = document.createElement('a'); a.href = url; a.download = (opts.title || '문제지') + '.pdf'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      $('status').textContent = `완료: ${list.length}문제 / ${plan.pages.length}쪽`;
    } catch (e) {
      console.error(e); $('status').textContent = '오류: ' + e.message;
    } finally { delete $('status').dataset.busy; updateButtons(); }
  }

  async function init() {
    const r = await fetch('data/problems.json'); DATA = await r.json();
    ALL = DATA.problems.slice().sort(cmp);
    $('modeTime').onclick = () => setMode('time'); $('modeUnit').onclick = () => setMode('unit');
    $('btnDetail').onclick = () => { detail = !detail; refresh(); };
    $('btnMake').onclick = make;
    $('btnForm').onclick = openForm;
    $('mOk').onclick = () => closeForm(true); $('mCancel').onclick = () => closeForm(false); $('mX').onclick = () => closeForm(false);
    $('overlay').addEventListener('mousedown', (e) => { if (e.target === $('overlay')) closeForm(false); });
    refresh();
  }
  init().catch((e) => { $('status').textContent = '데이터를 불러오지 못했어요: ' + e.message + ' (로컬에서 열 땐 python -m http.server 로 실행하세요)'; });
})();
