/* 레이아웃 계산(순수 함수). 브라우저/Node 양쪽에서 동작한다.
 * 입력: 선택한 문제 목록 -> 출력: 페이지별 그리기 명령(ops). PDF 생성은 app.js 가 담당. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Layout = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  const PAGE = { w: 595.276, h: 841.89 };
  const G = {
    left: 44, colW: 241, divX: 297.6, col1X: 310,
    top: 72, bottom: 767, headY: 55, headRule: 63, footRule: 778, footY: 794,
  };
  const colX = (c) => (c === 0 ? G.left : G.col1X);
  const SEC_LABEL = { '공통': '', '확률과 통계': '(확률과 통계)', '미적분': '(미적분)', '기하': '(기하)' };
  const pad4 = (i) => String(i + 1).padStart(4, '0');

  function buildPlan(problems, exams, opt) {
    opt = Object.assign({ title: '전국연합 학력평가 단원별 연습', footer: '', layout: 'auto', solutions: true, grid: true, solCap: 1.35 }, opt || {});
    const pages = [];
    let pageNo = 0;
    function newPage() {
      pageNo++;
      const ops = [];
      ops.push({ t: 'text', s: opt.title, x: PAGE.w / 2, y: G.headY, size: 11, bold: true, align: 'center' });
      ops.push({ t: 'line', x1: 40, y1: G.headRule, x2: PAGE.w - 40, y2: G.headRule, w: 0.8 });
      ops.push({ t: 'line', x1: G.divX, y1: G.top, x2: G.divX, y2: G.bottom, w: 0.8 });
      ops.push({ t: 'line', x1: 40, y1: G.footRule, x2: PAGE.w - 40, y2: G.footRule, w: 0.8 });
      ops.push({ t: 'text', s: String(pageNo), x: G.left, y: G.footY, size: 10, bold: true, align: 'left' });
      if (opt.footer) ops.push({ t: 'text', s: opt.footer, x: PAGE.w - 44, y: G.footY, size: 8.5, bold: false, align: 'right', italic: true });
      const pg = { ops };
      pages.push(pg);
      return pg;
    }

    /* ---------- 1) 문제 파트 ----------
     * 한 쪽 = 2단. 한 단에는 (a) 반 단짜리 2문제(위/아래) 또는 (b) 한 단짜리 1문제가 들어간다.
     *  - auto: 2·3점이면서 혼자서도 반 단에 들어가면 반 단, 4점이거나 반 단을 넘으면 한 단
     *  - full: 항상 한 단에 1문제 / half: 반 단에 들어가면 항상 반 단
     * 한 단짜리는 반쯤 찬 단에 이어붙이지 않고 다음 단(또는 다음 쪽)으로 넘긴다. */
    const colH = G.bottom - G.top, halfH = colH / 2, BAR_H = 20, PAD = 10;
    let pg = null, col = 0, used = 0;                 // used: 0=빈 단, 1=위 칸만 사용, 2=가득
    const nextCol = () => { if (col === 0) col = 1; else { pg = null; col = 0; } used = 0; };
    const cell = G.colW / 4;
    problems.forEach((p, i) => {
      const ex = exams[p.exam].q, b = p.q[0];
      const bw = b.x1 - b.x0, bh = b.b - b.t, s0 = Math.min(G.colW / bw, 1);
      const fitsHalf = bh * s0 <= halfH - BAR_H - PAD;
      const small = p.points != null && p.points <= 3;
      const half = opt.layout === 'full' ? false : opt.layout === 'half' ? fitsHalf : (small && fitsHalf);
      if (half) { if (used === 2) nextCol(); } else { if (used !== 0) nextCol(); }
      if (!pg) pg = newPage();
      let y0, slotH;
      if (half) { y0 = G.top + (used === 1 ? halfH : 0); slotH = halfH; used = used === 1 ? 2 : 1; }
      else { y0 = G.top; slotH = colH; used = 2; }
      const x = colX(col);
      y0 += 2;
      const s = Math.min(G.colW / bw, (slotH - BAR_H - PAD) / bh, 1);
      // 라벨: 4칸(번호 | 출제연월 | 학년 | 문제번호), 칸마다 왼쪽 정렬
      const sec = SEC_LABEL[p.sec] || (p.also ? '(=' + p.also.replace(/형 (\d+)번/, '$1') + ')' : '');
      const cells = [pad4(i), `${p.year}년 ${p.month}월`, `${p.grade}학년${p.form ? '(' + p.form + ')' : ''}`, `${p.n}번`];
      cells.forEach((t, k) => {
        pg.ops.push({ t: 'text', s: t, x: x + k * cell + 4, y: y0 + 11, size: 9.5, bold: true, align: 'left', maxW: cell - 6 });
        if (k > 0) pg.ops.push({ t: 'line', x1: x + k * cell, y1: y0 + 2, x2: x + k * cell, y2: y0 + 14, w: 0.5 });
      });
      if (sec) pg.ops.push({ t: 'text', s: sec, x: x + 3 * cell + 4 + (String(p.n).length * 5.4 + 11), y: y0 + 11, size: 6.5, bold: false, align: 'left', maxW: cell - 6 - (String(p.n).length * 5.4 + 11) });
      pg.ops.push({ t: 'line', x1: x, y1: y0 + 16, x2: x + G.colW, y2: y0 + 16, w: 0.6 });
      const dy = y0 + BAR_H;
      pg.ops.push({ t: 'crop', file: ex.file, page: b.p, ph: ex.h, src: [b.x0, b.t, b.x1, b.b], dest: [x, dy, bw * s, bh * s] });
      if (b.num) {  // 원본 문제 번호 가리기
        const n = b.num;
        pg.ops.push({ t: 'rect', x: x + (n[0] - b.x0) * s - 1, y: dy + (n[1] - b.t) * s - 1, w: (n[2] - n[0]) * s + 3, h: (n[3] - n[1]) * s + 2, fill: '#ffffff' });
      }
    });

    /* ---------- 2) 해설 파트: 미주(2단 흐름) ---------- */
    if (opt.solutions && problems.length) {
      pg = newPage(); col = 0; let y = G.top;
      const room = () => G.bottom - y;
      function advance() {
        if (col === 0) { col = 1; } else { pg = newPage(); col = 0; }
        y = G.top;
      }
      function ensure(h) { if (h > room() + 0.01) advance(); }

      if (opt.grid) {
        const ROWH = 17, PAIRS = 4, cw = G.colW / (PAIRS * 2);
        for (let r0 = 0; r0 < problems.length; r0 += PAIRS) {
          ensure(ROWH);
          const x = colX(col);
          for (let j = 0; j < PAIRS; j++) {
            const idx = r0 + j;
            const cx = x + j * 2 * cw;
            pg.ops.push({ t: 'rect', x: cx, y: y, w: cw, h: ROWH, stroke: true, sw: 0.6 });
            pg.ops.push({ t: 'rect', x: cx + cw, y: y, w: cw, h: ROWH, stroke: true, sw: 0.6 });
            if (idx < problems.length) {
              pg.ops.push({ t: 'text', s: pad4(idx), x: cx + cw / 2, y: y + 12, size: 8.5, bold: true, align: 'center' });
              pg.ops.push({ t: 'text', s: String(problems[idx].answer || '-'), x: cx + cw * 1.5, y: y + 12, size: 8.5, bold: false, align: 'center' });
            }
          }
          y += ROWH;
        }
        y += 8;
      }

      problems.forEach((p, i) => {
        const ea = exams[p.exam].a;
        const HDR = 15;
        const colH = G.bottom - G.top;
        if (!p.a.length) {      // 해설 원본이 없는 문항
          ensure(HDR + 4);
          pg.ops.push({ t: 'text', s: `${pad4(i)}  [정답] ${p.answer || '-'}  [단원] ${p.subject} > ${p.unit}  (해설 없음)`, x: colX(col) + 2, y: y + 11, size: 9.5, bold: true, align: 'left' });
          y += HDR + 8; return;
        }
        const hmax = Math.max(...p.a.map((b) => b.b - b.t));
        const s = Math.min(G.colW / ea.colw, opt.solCap, (colH - HDR - 4) / hmax);
        ensure(HDR + 4 + (p.a[0].b - p.a[0].t) * s);   // 머리줄 + 첫 조각은 같은 단에
        let x = colX(col);
        pg.ops.push({ t: 'text', s: `${pad4(i)}  [정답] ${p.answer}  [단원] ${p.subject} > ${p.unit}`, x: x + 2, y: y + 11, size: 9.5, bold: true, align: 'left' });
        y += HDR;
        p.a.forEach((b, bi) => {
          const bh = (b.b - b.t) * s, bw = (b.x1 - b.x0) * s;
          ensure(bh + 2);
          x = colX(col);
          pg.ops.push({ t: 'crop', file: ea.file, page: b.p, ph: ea.h, src: [b.x0, b.t, b.x1, b.b], dest: [x, y, bw, bh] });
          if (b.num) {
            const n = b.num;
            pg.ops.push({ t: 'rect', x: x + (n[0] - b.x0) * s - 2, y: y + (n[1] - b.t) * s - 3, w: (n[2] - n[0]) * s + 5, h: (n[3] - n[1]) * s + 5, fill: '#ffffff' });
          }
          y += bh + 2;
        });
        y += 8;
      });
    }
    return { pages, options: opt };
  }

  return { buildPlan, PAGE, G };
});
