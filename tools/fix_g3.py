"""2007~2009 3학년 문항 상자 보정: 맨 위/맨 아래에 섞인 작은 틀(단답형·5지선다형 띠, 선택과목 제목 띠, 선택과목 안내·확인사항 상자)과 쪽 머리글 잔여물을 잘라 data/detect 캐시에 저장한다."""
import json, os, sys, glob
import numpy as np, pypdfium2 as pdfium
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 2
_PG = {}
def img(pdf, it, thr):
    k = (id(pdf), it["page"])
    if k not in _PG: _PG[k] = np.array(pdf[it["page"]].render(scale=S).to_pil().convert("L"))
    return _PG[k][int(it["top"]*S):int(it["bottom"]*S), int(it["x0"]*S):int(it["x1"]*S)] < thr
def runs(row):
    best = cur = 0
    for v in row:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best
def ink_runs(a, gap=3*S):
    ys = np.where(a.any(axis=1))[0]
    if not len(ys): return []
    out = []; s = last = ys[0]
    for y in ys[1:]:
        if y-last > gap: out.append((s, last)); s = y
        last = y
    out.append((s, last)); return out
def is_box(a, r, need=35*S):
    s, e = r
    return 12*S <= e-s <= 75*S and max(runs(a[y]) for y in range(s, min(s+4, e))) >= need and max(runs(a[y]) for y in range(max(e-3, s), e+1)) >= need
def top_box(pdf, it):
    """맨 위 틀(띠) 하나를 떼어 낸다."""
    cut = False
    for thr in (150, 235):
        a = img(pdf, it, thr); rs = ink_runs(a)
        if len(rs) >= 2 and is_box(a, rs[0]) and rs[1][0]-rs[0][1] >= 6*S:
            it["top"] = round(it["top"] + (rs[1][0]-4)/S, 1); return True
    return False
def bot_box(pdf, it, H):
    """맨 아래 틀(선택과목 안내·5지선다형·확인사항 상자) 하나를 떼어 낸다. 쪽 맨 아래에 놓였거나 윗부분과 40pt 이상 떨어진 틀만."""
    a = img(pdf, it, 235); rs = ink_runs(a)
    while len(rs) >= 2 and (rs[-1][1]-rs[-1][0] < 10*S and runs(a[rs[-1][0]:rs[-1][1]+1].T.reshape(-1)) < 30*S and max(runs(a[y]) for y in range(rs[-1][0], rs[-1][1]+1)) < 30*S): rs = rs[:-1]
    if len(rs) < 2: return False
    s, e = rs[-1]
    if not (12*S <= e-s <= 75*S and max(runs(a[y]) for y in range(s, min(s+4, e+1))) >= 35*S): return False
    gap = s-rs[-2][1]
    if gap < 6*S or not (it["bottom"] >= H*0.8 or gap >= 40*S): return False
    it["bottom"] = round(it["top"] + (rs[-2][1]+6)/S, 1); return True
def trim_blank(pdf, it):
    a = img(pdf, it, 150); ys = np.where(a.any(axis=1))[0]
    if len(ys): it["bottom"] = round(it["top"] + ys[-1]/S + 6, 1)
def top_rule(pdf, it, lim=0.4):
    a = img(pdf, it, 150)
    ys = [y for y in range(a.shape[0]) if runs(a[y]) >= 0.5*a.shape[1] and y < a.shape[0]*lim]
    if ys: it["top"] = round(it["top"] + ys[-1]/S + 3, 1)
def apply(eid, mode, extra=()):
    cp = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(cp, encoding="utf-8"))
    y = int(eid[:4]); m = int(eid.split("-")[2]); f = {"ga": "가", "na": "나"}[eid[-2:]]
    pdf = pdfium.PdfDocument(f"{R}/pdf/{y}/{y}_3학년_{m}월({f}형)_문제.pdf")
    log = []; _PG.clear()
    for it in q["items"]:
        k = (it["sec"], it["n"])
        t0, b0 = it["top"], it["bottom"]
        if top_box(pdf, it): log.append((k, "top_box"))
        if bot_box(pdf, it, q['height']): log.append((k, "bot_box"))
        if it["sec"] == "공통" and it["n"] <= 3:        # 쪽 머리글·안내문 밑줄 위 잔여물
            a_ = img(pdf, it, 150)
            lim = 0.75 if (it["n"] == 1 and a_.shape[0] > 150*S) else (70*S/a_.shape[0])
            ys = [y for y in range(a_.shape[0]) if runs(a_[y]) >= 0.5*a_.shape[1] and y < a_.shape[0]*min(lim, 0.75)]
            if ys: top_rule(pdf, it, min(lim, 0.75)); log.append((k, "top_rule"))
        if mode == "text":
            trim_blank(pdf, it)
            a_ = img(pdf, it, 150); ys = np.where(a_.any(axis=1))[0]
            if len(ys) and ys[0]/S > 6: it["top"] = round(it["top"] + ys[0]/S - 5, 1)
    for sec, n, kind in extra:
        it = next(i for i in q["items"] if i["sec"] == sec and i["n"] == n)
        if kind == "top_rule": top_rule(pdf, it)
        elif kind.startswith("top-"): it["top"] = round(it["top"] - float(kind[4:]), 1)
        elif kind.startswith("cut_top:"): it["top"] = round(it["top"] + float(kind[8:]), 1)
        elif kind.startswith("bot-"): it["bottom"] = round(it["bottom"] - float(kind[4:]), 1)
        elif kind.startswith("bot+"): it["bottom"] = round(it["bottom"] + float(kind[4:]), 1)
        log.append(((sec, n), kind))
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
    return log
TEXT = {"2006-3-03", "2006-3-09", "2007-3-03", "2007-3-04", "2008-3-04", "2009-3-03", "2009-3-04", "2009-3-07", "2009-3-10", "2009-3-11"}
EXTRA = json.load(open(f"{R}/data/fix_g3_extra.json", encoding="utf-8")) if os.path.exists(f"{R}/data/fix_g3_extra.json") else {}
if __name__ == "__main__":
    only = sys.argv[1:]
    for f in sorted(glob.glob(f"{R}/data/detect/200[6789]-3-*.json")):
        eid = os.path.basename(f)[:-5]
        if only and not any(eid.startswith(o) for o in only): continue
        lg = apply(eid, "text" if eid[:-3] in TEXT else "img", [tuple(x) for x in EXTRA.get(eid, [])])
        print(eid, lg)
