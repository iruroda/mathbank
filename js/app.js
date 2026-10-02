/* 문제은행 화면 + PDF 조립(pdf-lib).  레이아웃 계산은 js/layout.js 가 담당한다. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const SEC_RANK = { '공통': 0, '확률과 통계': 1, '미적분': 2, '기하': 3 };
  const FIELDS = [
    ['year', '연도', (p) => p.year + '년'],
    ['grade', '학년', (p) => p.grade + '학년'],
    ['month', '시행월', (p) => p.month + '월'],
    ['sec', '구분', (p) => p.sec],
    ['subject', '과목', (p) => p.subject],
    ['unit', '단원', (p) => p.subject + '|' + p.unit],
    ['points', '배점', (p) => (p.points == null ? '-' : p.points + '점')],
    ['type', '형식', (p) => p.type],
  ];
  let DATA = null, ALL = [], filters = {}, selected = new Set();

  const cmp = (a, b) => a.year - b.year || a.grade - b.grade || a.month - b.month || SEC_RANK[a.sec] - SEC_RANK[b.sec] || a.n - b.n;

  function matches(p, skip) {
    for (const [k, , f] of FIELDS) {
      if (k === skip) continue;
      const set = filters[k];
      if (set && set.size && !set.has(f(p))) return false;
    }
    return true;
  }

  function renderFilters() {
    const box = $('filters'); box.innerHTML = '';
    FIELDS.forEach(([k, label, f]) => {
      const h = document.createElement('h3'); h.textContent = label; box.appendChild(h);
      const counts = new Map();
      ALL.forEach((p) => { if (matches(p, k)) counts.set(f(p), (counts.get(f(p)) || 0) + 1); });
      const keys = [...new Set(ALL.map(f))];
      const UO = (DATA.units || []).map((u) => u[0] + '|' + u[1]);
      const rank = (v) => { const i = UO.indexOf(v); return i < 0 ? 999 : i; };
      if (k === 'unit') {                       // 단원은 과목별로 묶어서 표시 (성취기준 파일 순서)
        keys.sort((a, b) => rank(a) - rank(b));
        let last = null;
        keys.forEach((v) => {
          const [sub, un] = v.split('|');
          if (sub !== last) { const g = document.createElement('div'); g.className = 'grp'; g.textContent = sub; box.appendChild(g); last = sub; }
          box.appendChild(chk(k, v, counts.get(v) || 0, un));
        });
        return;
      }
      if (k === 'subject') keys.sort((a, b) => Math.min(...UO.map((u, i) => (u.split('|')[0] === a ? i : 999))) - Math.min(...UO.map((u, i) => (u.split('|')[0] === b ? i : 999))));
      else keys.sort((a, b) => String(a).localeCompare(String(b), 'ko', { numeric: true }));
      keys.forEach((v) => box.appendChild(chk(k, v, counts.get(v) || 0)));
    });
  }
  function chk(k, v, n, label) {
    const l = document.createElement('label'); l.className = 'chk';
    const i = document.createElement('input'); i.type = 'checkbox';
    i.checked = !!(filters[k] && filters[k].has(v));
    i.onchange = () => { (filters[k] = filters[k] || new Set())[i.checked ? 'add' : 'delete'](v); refresh(); };
    l.append(i, document.createTextNode(' ' + (label || v)));
    const s = document.createElement('span'); s.className = 'n'; s.textContent = n; l.appendChild(s);
    return l;
  }

  function visible() { return ALL.filter((p) => matches(p, null)); }

  function renderRows() {
    const tb = $('rows'); tb.innerHTML = '';
    const vis = visible();
    vis.forEach((p) => {
      const tr = document.createElement('tr'); if (selected.has(p.id)) tr.className = 'sel';
      const td0 = document.createElement('td'); const c = document.createElement('input'); c.type = 'checkbox'; c.checked = selected.has(p.id);
      c.onchange = () => { c.checked ? selected.add(p.id) : selected.delete(p.id); tr.className = c.checked ? 'sel' : ''; updateCount(); };
      td0.appendChild(c); tr.appendChild(td0);
      const cells = [`${p.year}년 ${p.month}월 ${p.grade}학년 ${p.n}번`, p.sec === '공통' ? '공통' : p.sec, `${p.subject} > ${p.unit}`, p.points == null ? '-' : p.points + '점', p.type, p.summary];
      cells.forEach((t) => { const td = document.createElement('td'); td.textContent = t; tr.appendChild(td); });
      tr.onclick = (e) => { if (e.target !== c) { c.checked = !c.checked; c.onchange(); } };
      tb.appendChild(tr);
    });
    updateCount();
  }
  function updateCount() {
    $('count').innerHTML = `조건에 맞는 문제 <b>${visible().length}</b>개 · 선택 <span class="pill">${selected.size}</span>개`;
    $('btnMake').disabled = selected.size === 0;
  }
  function refresh() { renderFilters(); renderRows(); }

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
    const btn = $('btnMake'); btn.disabled = true;
    try {
      $('status').textContent = 'PDF 라이브러리 준비 중…';
      await ensurePdfLib();
      const picked = ALL.filter((p) => selected.has(p.id)).sort(cmp);
      const plan = Layout.buildPlan(picked, DATA.exams, {
        title: $('optTitle').value, footer: $('optFooter').value,
        layout: $('optLayout').value, solutions: $('optSol').value === '1',
      });
      const bytes = await renderPlan(plan, (d, n) => { $('status').textContent = `만드는 중… ${d}/${n}쪽`; });
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      const a = document.createElement('a'); a.href = url; a.download = ($('optTitle').value || '문제지') + '.pdf'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      $('status').textContent = `완료: ${picked.length}문제 / ${plan.pages.length}쪽`;
    } catch (e) {
      console.error(e); $('status').textContent = '오류: ' + e.message;
    } finally { btn.disabled = selected.size === 0; }
  }

  async function init() {
    const r = await fetch('data/problems.json'); DATA = await r.json();
    ALL = DATA.problems.slice().sort(cmp);
    $('meta').textContent = `문제 ${ALL.length}개 · 시험 ${Object.keys(DATA.exams).length}회`;
    $('btnAll').onclick = () => { visible().forEach((p) => selected.add(p.id)); renderRows(); };
    $('btnNone').onclick = () => { selected.clear(); renderRows(); };
    $('btnMake').onclick = make;
    refresh();
  }
  init().catch((e) => { $('meta').textContent = '데이터를 불러오지 못했어요: ' + e.message + ' (로컬에서 열 땐 python -m http.server 로 실행하세요)'; });
})();
