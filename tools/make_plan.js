// 사용: node tools/make_plan.js <단원> <출력.json>  (단원이 'ALL' 이면 전체)
const L = require('../js/layout.js'); const d = require('../data/problems.json');
const unit = process.argv[2], out = process.argv[3];
const secRank = { '공통': 0, '확률과 통계': 1, '미적분': 2, '기하': 3 };
let sel = d.problems.filter(p => unit === 'ALL' || p.unit === unit || p.subject === unit);
sel.sort((a, b) => a.year - b.year || a.grade - b.grade || a.month - b.month || secRank[a.sec] - secRank[b.sec] || a.n - b.n);
const plan = L.buildPlan(sel, d.exams, { title: '전국연합 학력평가 단원별 연습: ' + (unit === 'ALL' ? '전체' : unit), footer: '우리는 알아야만 한다. 우리는 알게 될 것이다. - David Hilbert', layout: process.argv[4] || 'auto' });
require('fs').writeFileSync(out, JSON.stringify(plan));
console.log(sel.length + '문항 -> ' + plan.pages.length + '쪽');
