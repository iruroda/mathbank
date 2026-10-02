"""해설 PDF에서 문항별 해설 구간(여러 단·쪽에 걸칠 수 있음)을 검출한다."""
import re, json, sys, unicodedata
import pdfplumber

NUM = re.compile(r'^(\d{1,2})\.$')
SECTIONS = ["공통", "확률과 통계", "미적분", "기하"]

def wide_hlines(p):
    return sorted([o for o in p.lines + p.rects if o["x1"]-o["x0"] > 300 and o["bottom"]-o["top"] < 3], key=lambda o: o["top"])

def page_frame(p):
    hs = wide_hlines(p)
    top_rules = [h for h in hs if h["top"] < 200]
    bot_rules = [h for h in hs if h["top"] > 650]
    x0 = min([h["x0"] for h in hs], default=40); x1 = max([h["x1"] for h in hs], default=p.width-40)
    top = (max(h["bottom"] for h in top_rules) if top_rules else 100) + 2
    bottom = min([h["top"] for h in bot_rules], default=p.height-50) - 2
    return x0, x1, top, bottom

def occupancy_columns(pdf, x0, x1, top, bottom):
    cov = [0]*int(x1+2)
    for p in pdf.pages:
        for c in p.chars:
            if c["text"].strip() and top <= c["top"] and c["bottom"] <= bottom:
                for x in range(int(c["x0"]), int(c["x1"])+1):
                    if x < len(cov): cov[x] += 1
        for o in p.images + p.curves:
            if top <= o["top"] and o["bottom"] <= bottom and o["x1"]-o["x0"] < 150:
                for x in range(int(o["x0"]), int(o["x1"])+1):
                    if x < len(cov): cov[x] += 1
    thr = max(2, len(pdf.pages)//3)
    xs = range(int(x0), int(x1)+1)
    low = [cov[x] <= thr for x in xs]
    # 낮은 점유 구간(간격) 찾기
    gaps, s = [], None
    for k, x in enumerate(xs):
        if low[k] and s is None: s = x
        if (not low[k]) and s is not None:
            if x - s >= 6: gaps.append((s, x-1))
            s = None
    # 바깥쪽 여백은 제외, 안쪽 간격만 단 경계로 사용
    inner = [g for g in gaps if g[0] > x0+5 and g[1] < x1-5]
    bounds = []
    for gs, ge in inner:
        mid = (gs+ge)/2
        best = min(range(gs, ge+1), key=lambda x: (cov[x], abs(x-mid)))
        bounds.append(best)
    return bounds

def find_columns(pdf):
    p = pdf.pages[0]
    x0, x1, top, bottom = page_frame(p)
    vs = sorted(set(round((o["x0"]+o["x1"])/2) for o in p.lines + p.rects
                    if o["bottom"]-o["top"] > 300 and o["x1"]-o["x0"] < 3))
    if vs:
        edges = [x0] + vs + [x1]
        return [(edges[i], edges[i+1]) for i in range(len(edges)-1)], True
    bounds = occupancy_columns(pdf, x0, x1, top, bottom)
    edges = [x0] + bounds + [x1]
    return [(edges[i], edges[i+1]) for i in range(len(edges)-1)], False

def detect(path, elective=False):
    with pdfplumber.open(path) as pdf:
        cols, has_lines = find_columns(pdf)
        inset = 1.5 if has_lines else 0.0
        events = []           # (page, col, top, kind, n)
        frames = []
        sec_i, last = 0, 0
        for pi, p in enumerate(pdf.pages):
            x0, x1, top, bottom = page_frame(p)
            frames.append((top, bottom))
            words = p.extract_words()
            for ci, (cl, cr) in enumerate(cols):
                cw = [w for w in words if cl-2 <= w["x0"] < cr and top-8 <= w["top"] < bottom]
                for i, w in enumerate(cw):
                    t = unicodedata.normalize("NFKC", w["text"])
                    if t.startswith("[선택:") and w["x0"] <= cl+25:
                        events.append((pi, ci, w["top"]-6, "term", 0))
                    m = NUM.match(t)
                    if m and w["x0"] <= cl+25:
                        line = "".join(x["text"] for x in cw if abs(x["top"]-w["top"]) < 3 and x["x0"] >= w["x0"])
                        if "출제의도" in line[:12]:
                            events.append((pi, ci, w["top"], "mark", int(m.group(1)), (w["x0"], w["top"], w["x1"], w["bottom"])))
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        # 번호 순서 확인 및 섹션 부여
        marks = []
        for e in events:
            if e[3] != "mark": continue
            n = e[4]
            if elective and n == 23 and last in (22, 30): sec_i = 1 if last == 22 else sec_i+1
            elif n == last+1: pass
            else: continue
            marks.append(e); last = n; marks[-1] = e + (SECTIONS[sec_i],)
        # 흐름(쪽, 단) 순서
        flow = [(pi, ci) for pi in range(len(pdf.pages)) for ci in range(len(cols))]
        items = []
        def objs_in(p, cl, cr, lo, hi):
            r = []
            for c in p.chars: r.append((c["x0"], c["top"], c["x1"], c["bottom"]))
            for o in p.images + p.curves: r.append((o["x0"], o["top"], o["x1"], o["bottom"]))
            return [(a, t, b, d) for a, t, b, d in r if a >= cl-3 and b <= cr+3 and t >= lo-2 and t < hi-8]
        allev = sorted(events, key=lambda e: (e[0], e[1], e[2]))
        for k, mk in enumerate(marks):
            pi0, ci0, top0 = mk[0], mk[1], mk[2]
            # 끝 사건: 흐름상 바로 다음 사건(번호 마커 또는 구역 제목)
            idx = allev.index(mk[:6])
            # 정상 번호(채택된) 마커 또는 term 만 끝 사건으로
            end = None
            for e in allev[idx+1:]:
                if e[3] == "term" or e[:6] in [m[:6] for m in marks]:
                    end = e; break
            boxes = []
            s0 = flow.index((pi0, ci0))
            s1 = flow.index((end[0], end[1])) if end else len(flow)-1
            for s in range(s0, s1+1):
                pi, ci = flow[s]; p = pdf.pages[pi]; cl, cr = cols[ci]
                ftop, fbot = frames[pi]
                lo = top0-4 if s == s0 else ftop
                hi = (end[2] - 0) if (end and s == s1) else fbot
                oo = objs_in(p, cl, cr, lo, hi)
                if not oo: continue
                bot = max(d for _, _, _, d in oo)
                if bot - lo < 10: continue
                boxes.append(dict(page=pi, x0=(cl+inset if ci > 0 else cl-2), x1=(cr-inset if ci < len(cols)-1 else cr+2), top=lo, bottom=bot+5))
            nb = mk[5]
            if boxes: boxes[0]["num"] = dict(x0=nb[0], top=nb[1], x1=nb[2], bottom=nb[3])
            items.append(dict(n=mk[4], sec=mk[6], boxes=boxes))
        W, H = pdf.pages[0].width, pdf.pages[0].height
    return dict(width=W, height=H, columns=cols, items=items)

if __name__ == "__main__":
    r = detect(sys.argv[1])
    json.dump(r, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(sys.argv[1], "cols", r["columns"], "n=", len(r["items"]))
    print([(i["n"], len(i["boxes"])) for i in r["items"]])
