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
    vtops = [o["top"] for o in p.lines + p.rects if o["bottom"]-o["top"] > 300 and o["x1"]-o["x0"] < 3]
    if vtops: top = max(top, min(vtops) - 2)       # 단 구분선이 시작하는 곳 아래부터가 본문
    bottom = min([h["top"] for h in bot_rules], default=p.height-50) - 2
    vbots = [o["bottom"] for o in p.lines + p.rects if o["bottom"]-o["top"] > 300 and o["x1"]-o["x0"] < 3]
    if vbots and not bot_rules: bottom = min(bottom, max(vbots) + (2 if p.height > 1000 else 12))   # 단 구분선이 끝나는 곳까지가 본문(쪽번호 제외)
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

def char_marks(p):
    """'N.[출제의도]' 머리표를 글자 단위로 찾는다(토큰이 뒤섞여도 동작). -> [(n, x0, top, x1, bottom)]"""
    ch = [c for c in p.chars if c["text"].strip()]
    out = []
    for k, c0 in enumerate(ch):
        if c0["text"] != "출": continue
        tail = [d for d in ch if abs(d["top"]-c0["top"]) < 3 and 0 <= d["x0"]-c0["x1"]+2 < 40 and d["text"] in "제의도"]
        if len({d["text"] for d in tail}) < 3: continue
        # '출' 바로 앞의 '[' 가 있으면 그 위치를 기준으로
        pre = [d for d in ch if d["text"] == "[" and abs(d["top"]-c0["top"]) < 3 and -2 <= c0["x0"]-d["x1"] < 6]
        c = pre[0] if pre else c0
        cand = sorted([d for d in ch if abs(d["top"]-c["top"]) < 3 and d["x1"] <= c["x0"]+1 and d["x0"] >= c["x0"]-34
                       and (d["text"].isdigit() or d["text"] in ".．")], key=lambda d: -d["x1"])
        num = []
        for d in cand:                       # '[' 바로 왼쪽의 '.'부터 연속된 숫자만
            if not num:
                if d["text"] in ".．" and c["x0"]-d["x1"] < 12: num.append(d)
            elif num[-1]["x0"]-d["x1"] < 2.5 and d["text"].isdigit(): num.append(d)
            else: break
        num.reverse()
        t = "".join(d["text"] for d in num).replace("．", ".")
        m = re.fullmatch(r"(\d{1,2})\.", t)
        if not m: continue
        out.append((int(m.group(1)), num[0]["x0"], min(d["top"] for d in num), num[-1]["x1"], max(d["bottom"] for d in num)))
    return out

def bold_marks(p):
    """한글이 추출되지 않는 PDF용: 굵은 '.' 바로 왼쪽의 숫자(글꼴 무관)를 문항 머리표로 본다."""
    ch = [c for c in p.chars]
    out = []
    for c in ch:
        if c["text"] != "." or "Bold" not in c["fontname"]: continue
        sp = [d for d in ch if d["text"] == " " and "Bold" in d["fontname"] and abs(d["top"]-c["top"]) < 3 and -1 <= d["x0"]-c["x1"] < 3]
        if not sp: continue
        ds = sorted([d for d in ch if d["text"].isdigit() and abs(d["top"]-c["top"]) < 5 and d["x1"] <= c["x0"]+1 and d["x0"] >= c["x0"]-22], key=lambda d: -d["x1"])
        run = []
        for d in ds:
            if not run:
                if c["x0"]-d["x1"] < 3: run.append(d)
            elif run[-1]["x0"]-d["x1"] < 3: run.append(d)
            else: break
        if not run:      # 숫자 글리프가 누락된 경우: 번호 미상(None) → 순서로 추정
            out.append((None, c["x0"]-6, c["top"], c["x1"], c["bottom"])); continue
        run.reverse()
        n = int("".join(d["text"] for d in run))
        out.append((n, run[0]["x0"], min(d["top"] for d in run), c["x1"], max(d["bottom"] for d in run)))
    # 한 줄에 여러 개 나란한 번호는 정답표이므로 제외
    from collections import Counter
    cnt = Counter(round(o[2]/3) for o in out)
    bold_marks.tables = [(min(o[1] for o in out if round(o[2]/3) == k), min(o[2] for o in out if round(o[2]/3) == k))
                         for k in cnt if cnt[k] > 1 and any(o[0] == 23 for o in out if round(o[2]/3) == k)]
    return [o for o in out if cnt[round(o[2]/3)] == 1]

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
            cm = char_marks(p)
            tabs = []
            if not cm:
                cm = bold_marks(p); tabs = bold_marks.tables
            for ci, (cl, cr) in enumerate(cols):
                cw = [w for w in words if cl-2 <= w["x0"] < cr and top-8 <= w["top"] < bottom]
                for w in cw:
                    t = unicodedata.normalize("NFKC", w["text"])
                    nxt = [x for x in cw if abs(x["top"]-w["top"]) < 4 and 0 < x["x0"]-w["x1"] < 30]
                    nt = unicodedata.normalize("NFKC", nxt[0]["text"]) if nxt else ""
                    head = (t.startswith("[선택:") or t in ("[확률과", "[미적분]", "[기하]", "[확률과통계]") or
                            (t in ("기하", "미적분", "확률과") and nt.startswith(("정답", "해설", "통계"))))
                    if head:
                        events.append((pi, ci, w["top"]-6, "term", 0))
                for tx, tt in tabs:       # 선택과목 정답표 = 구역 제목 (이전 문항 해설의 끝)
                    if cl-2 <= tx < cr and top-8 <= tt < bottom: events.append((pi, ci, max(tt-32, top), "term", 0))
                for n, x0_, t_, x1_, b_ in cm:
                    if cl-2 <= x0_ < cr and x0_ <= cl+60 and top-8 <= t_ < bottom:
                        events.append((pi, ci, t_, "mark", n, (x0_, t_, x1_, b_)))
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        # 번호 순서 확인 및 섹션 부여
        marks = []
        for e in events:
            if e[3] != "mark": continue
            n = e[4]
            if n is None: n = last+1; e = e[:4] + (n,) + e[5:]
            if elective and n == 23 and last in (0, 22, 30): sec_i = 1 if last in (0, 22) else sec_i+1   # last==0: 선택과목 해설만 실린 파일
            elif n == last+1: pass
            else: continue
            marks.append(e); last = n; marks[-1] = e + (SECTIONS[sec_i],)
        # 흐름(쪽, 단) 순서
        flow = [(pi, ci) for pi in range(len(pdf.pages)) for ci in range(len(cols))]
        items = []
        def objs_in(p, cl, cr, lo, hi):
            r = []
            for c in p.chars: r.append((c["x0"], c["top"], c["x1"], min(c["bottom"], c["top"]+40)))   # 늘어난 큰 괄호 글리프의 bbox 보정
            for o in p.images + p.curves: r.append((o["x0"], o["top"], o["x1"], o["bottom"]))
            return [(a, t, b, d) for a, t, b, d in r if a >= cl-3 and b <= cr+3 and t >= lo-2 and t < hi-8]
        allev = sorted(events, key=lambda e: (e[0], e[1], e[2]))
        for k, mk in enumerate(marks):
            pi0, ci0, top0 = mk[0], mk[1], mk[2]
            # 끝 사건: 흐름상 바로 다음 사건(번호 마커 또는 구역 제목)
            idx = [(e[0], e[1], e[2], e[3]) for e in allev].index(mk[:3] + (mk[3],))
            # 정상 번호(채택된) 마커 또는 term 만 끝 사건으로
            end = None
            for e in allev[idx+1:]:
                if e[3] == "term" or (e[0], e[1], e[2], e[3]) in [(m[0], m[1], m[2], m[3]) for m in marks]:
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
                bt = bot+5
                if end and s == s1: bt = min(bt, hi-2)
                boxes.append(dict(page=pi, x0=(cl+inset if ci > 0 else cl-2), x1=(cr-inset if ci < len(cols)-1 else cr+2), top=lo, bottom=bt))
            nb = mk[5]
            if boxes: boxes[0]["num"] = dict(x0=nb[0], top=nb[1], x1=nb[2], bottom=nb[3])
            items.append(dict(n=mk[4], sec=mk[6], boxes=boxes))
        # 선택과목이 하나만 실린 해설(예: 기하만)이면 쪽 글에서 과목명을 찾아 붙인다
        if elective and items and {i["sec"] for i in items} <= {"공통", "확률과 통계"}:
            names = set()
            for p in pdf.pages:
                names |= set(re.findall(r"(확률과 통계|미적분|기하)\s*(?:정답|해설)", p.extract_text() or ""))
            if len(names) == 1:
                nm = next(iter(names))
                for i in items:
                    if i["sec"] != "공통": i["sec"] = nm
        W, H = pdf.pages[0].width, pdf.pages[0].height
    return dict(width=W, height=H, columns=cols, items=items)

if __name__ == "__main__":
    r = detect(sys.argv[1])
    json.dump(r, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(sys.argv[1], "cols", r["columns"], "n=", len(r["items"]))
    print([(i["n"], len(i["boxes"])) for i in r["items"]])
