"""해설 PDF에서 문항별 해설 구간(여러 단·쪽에 걸칠 수 있음)을 검출한다."""
import re, json, sys, unicodedata, os
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
    if vtops: top = (max(top, min(vtops) - 2) if top_rules else min(vtops) - 2)       # 단 구분선이 시작하는 곳 아래부터가 본문 (머리 규칙선이 없는 쪽은 구분선 시작점이 곧 본문 시작)
    elif not top_rules and p.chars: top = max(20, min(top, min(c['top'] for c in p.chars) - 2))     # 머리 규칙선이 없는 쪽은 첫 글자부터가 본문
    bottom = min([h["top"] for h in bot_rules], default=p.height-50) - 2
    vbots = [o["bottom"] for o in p.lines + p.rects if o["bottom"]-o["top"] > 300 and o["x1"]-o["x0"] < 3]
    if vbots and not bot_rules:
        low = max([c["bottom"] for c in p.chars if c["text"].strip() and c["bottom"] < p.height-55], default=0)
        bottom = min(bottom, max(max(vbots) + (2 if p.height > 1000 else 12), low + 2))   # 단 구분선이 끝나는 곳까지가 본문(쪽번호 제외)
    return x0, x1, top, bottom

def _gaps(cov, x0, x1, thr):
    xs = range(int(x0), int(x1)+1); out, s = [], None
    for x in xs:
        lo = cov[x] <= thr
        if lo and s is None: s = x
        if not lo and s is not None:
            if x-s >= 6 and s > x0+5 and x-1 < x1-5: out.append((s, x-1))
            s = None
    return out

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
    if not _gaps(cov, x0, x1, thr): thr = max(thr, int(0.05*max(cov)))      # 잡음이 낀 PDF: 문턱을 최대 점유의 5%로
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
    xs_ = [c["x0"] for pg in pdf.pages for c in pg.chars if c["text"].strip() and top <= c["top"] <= bottom]
    if xs_ and pdf.pages[0].width < 700 and os.environ.get('EXT_X1', '1') == '1':
        xe = sorted(c["x1"] for pg in pdf.pages for c in pg.chars if c["text"].strip() and top <= c["top"] <= bottom)
        x1 = max(x1, min(xe[int(len(xe)*0.999)-1] + 2, p.width - 20))       # 오른쪽 끝의 '답' 상자가 단 밖으로 잘리지 않게
    if xs_: x0 = min(x0, min(xs_) - 2)                      # 본문 글자가 머리 규칙선보다 왼쪽에서 시작하는 경우
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
    seen, ch2 = {}, []          # 굵게 보이려고 같은 글자를 겹쳐 찍은 PDF: 중복 제거
    for c in ch:
        kx, ky = int(c["x0"]//2), int(c["top"]//2)
        if any(abs(d["x0"]-c["x0"]) < 0.8 and abs(d["top"]-c["top"]) < 0.8 for i in (-1, 0, 1) for j in (-1, 0, 1) for d in seen.get((c["text"], kx+i, ky+j), ())): continue
        seen.setdefault((c["text"], kx, ky), []).append(c); ch2.append(c)
    ch = ch2
    out = []
    for k, c0 in enumerate(ch):
        if c0["text"] in ("동", "같") and any(d["text"] == ("일" if c0["text"] == "동" else "음") and abs(d["top"]-c0["top"]) < 3 and -2 <= d["x0"]-c0["x1"] < 4 for d in ch):
            # '[가형 2번과 동일]' / '11.A형17번과동일' 처럼 다른 형과 같은 문항 (해설 본문 없음): 같은 줄 앞쪽의 'N.' 을 머리표로
            line = sorted([d for d in ch if abs(d["top"]-c0["top"]) < 3 and c0["x0"]-130 <= d["x0"] < c0["x0"]], key=lambda d: d["x0"])
            txt = "".join(d["text"] for d in line)          # 같은 줄 왼쪽 130pt (옆 단 글자가 섞일 수 있어 맨 오른쪽의 번호만 본다)
            mr = re.search(r"(\d{1,2})\s*[-~–∼]\s*(\d{1,2})\.\D{0,8}$", txt)
            m0 = None if mr else re.search(r"(\d{1,2})\.\D{0,8}$", txt)
            if mr:                                           # '18-22. 가형과 동일' : 번호 범위 → 같은 자리에 연속 번호 머리표
                k0 = txt.index(".", mr.start(2)); num = line[mr.start(1):k0+1]
                for q in range(int(mr.group(1)), int(mr.group(2))+1):
                    out.append((q, num[0]["x0"], min(d["top"] for d in num), num[-1]["x1"], max(d["bottom"] for d in num)))
                continue
            if not m0: continue
            k0 = txt.index(".", m0.start(1)); num = line[m0.start(1):k0+1]
            out.append((int(m0.group(1)), num[0]["x0"], min(d["top"] for d in num), num[-1]["x1"], max(d["bottom"] for d in num)))
            continue
        if True:
            if c0["text"] != "출": continue
            tail = [d for d in ch if abs(d["top"]-c0["top"]) < 5 and 0 <= d["x0"]-c0["x1"]+2 < 40 and d["text"] in "제의도"]
            if len({d["text"] for d in tail}) < 3: continue
            # '출' 바로 앞의 '[' 가 있으면 그 위치를 기준으로
            pre = [d for d in ch if d["text"] == "[" and abs(d["top"]-c0["top"]) < 5 and -2 <= c0["x0"]-d["x1"] < 6]
        c = pre[0] if pre else c0
        cand = sorted([d for d in ch if abs(d["top"]-c["top"]) < 5 and d["x1"] <= c["x0"]+1 and d["x0"] >= c["x0"]-34
                       and (d["text"].isdigit() or d["text"] in ".．")], key=lambda d: -d["x1"])
        num = []
        for d in cand:                       # '[' 바로 왼쪽의 '.'부터 연속된 숫자만
            if not num:
                if (d["text"] in ".．" or d["text"].isdigit()) and c["x0"]-d["x1"] < 12: num.append(d)
            elif num[-1]["x0"]-d["x1"] < 2.5 and d["text"].isdigit(): num.append(d)
            else: break
        num.reverse()
        t = "".join(d["text"] for d in num).replace("．", ".")
        m = re.fullmatch(r"(\d{1,2})\.?", t)
        if not m:            # 평가원/EBS 해설: 번호('7.')가 '출제의도 :' 바로 윗줄 왼쪽 끝에 따로 있다
            ab = sorted([d for d in ch if -34 <= d["top"]-c["top"] <= -5 and -3 <= d["x0"]-c["x0"] < 30 and (d["text"].isdigit() or d["text"] in ".．")], key=lambda d: d["x0"])
            ab = [d for d in ab if abs(d["top"]-ab[0]["top"]) < 3] if ab else []
            t2 = "".join(d["text"] for d in ab).replace("．", ".")
            m = re.fullmatch(r"(\d{1,2})\.", t2)
            if not m:                                        # 번호 글자가 없는(그림으로 된) 머리표: 번호 미상 → 순서로 추정
                out.append((None, c["x0"]-1, c["top"], c["x0"]+5, c["bottom"])); continue
            num = ab
        elif False: pass
        out.append((int(m.group(1)), num[0]["x0"], min(d["top"] for d in num), num[-1]["x1"], max(d["bottom"] for d in num)))
    uniq, seen = [], set()
    for m in out:
        k = (m[0], round(m[2]/4), round(m[1]/40))
        if k in seen: continue
        seen.add(k); uniq.append(m)
    return uniq

def iso_marks(p, refx, have):
    """'출제의도' 표시가 없는 해설 머리표: 줄(또는 단) 맨 앞의 '13.' (뒤에 글이 이어져도 됨; 소수점 '1.5' 는 제외).
    다른 머리표와 같은 x 위치(refx)에 있을 때만 (refx=None 이면 후보를 모두 돌려준다)."""
    ch = [c for c in p.chars if c["text"].strip()]
    lines = {}
    for c in ch: lines.setdefault(round(c["top"]/3), []).append(c)
    out = []
    for k in sorted(lines):
        L = sorted(lines[k], key=lambda c: c["x0"])
        for i, c in enumerate(L):
            if not c["text"].isdigit(): continue
            if i > 0 and c["x0"]-L[i-1]["x1"] < 14 and L[i-1]["text"].strip(): continue          # 줄/단의 맨 앞 글자만
            j = i
            while j+1 < len(L) and L[j+1]["text"].isdigit() and L[j+1]["x0"]-L[j]["x1"] < 3 and j-i < 1: j += 1
            if j+1 >= len(L) or L[j+1]["text"] not in ".．" or L[j+1]["x0"]-L[j]["x1"] > 4: continue
            dot = L[j+1]
            if j+2 < len(L) and L[j+2]["text"].isdigit() and L[j+2]["x0"]-dot["x1"] < 2: continue   # 1.5 같은 소수
            n = int("".join(d["text"] for d in L[i:j+1]))
            if n in have: continue
            if refx is not None and not any(abs(c["x0"]-r) <= 16 for r in refx): continue
            out.append((n, c["x0"], min(d["top"] for d in L[i:j+2]), dot["x1"], max(d["bottom"] for d in L[i:j+2])))
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

PATCH_MARKS = {'2010_3학년_6월(가형)_해설.pdf': [(12, 0, 556, 30)],
               '2010_3학년_9월(가형)_해설.pdf': [(15, 1, 305, 30)],
               '2010_3학년_9월(나형)_해설.pdf': [(6, 1, 412, 30)],
               '2010_3학년_6월(나형)_해설.pdf': [(5, 0, 170, 23), (5, 0, 550, 24), (5, 1, 286, 25), (6, 0, 244, 26), (6, 0, 418, 27), (6, 1, 140, 28), (6, 1, 650, 29), (7, 0, 581, 30)]}

PATCH_DROP = {'2013_3학년_6월(B형)_해설.pdf': [(4, 0, 721)]}

def detect(path, elective=False, group=0, two=False, cols=None):
    with pdfplumber.open(path) as pdf:
        cols, has_lines = (([tuple(c) for c in cols], True) if cols else find_columns(pdf))
        inset = 1.5 if has_lines else 0.0
        events = []           # (page, col, top, kind, n)
        heads = []; extra = []
        pm_ = [char_marks(p) for p in pdf.pages]
        refx = {round(m[1]) for L in pm_ for m in L}
        refx_iso = None
        if not any(pm_):                                  # 머리표 글자가 전혀 없는 해설(사설형 '1.' 만 있는 번호): 번호 줄의 x 위치 최빈값을 기준으로
            from collections import Counter
            cnt = Counter(round(m[1]/3) for p in pdf.pages for m in iso_marks(p, None, set()))
            refx_iso = {b*3 for b, c in cnt.items() if c >= 6}
        frames = []
        sec_i, last = 0, 0
        pre, restart, SECTIONS_ = 22, 23, SECTIONS
        if elective == 'old7': pre, restart, SECTIONS_ = 25, 26, ['공통', '미분과 적분', '확률과 통계', '이산수학']
        for pi, p in enumerate(pdf.pages):
            x0, x1, top, bottom = page_frame(p)
            frames.append((top, bottom))
            words = p.extract_words()
            cm = pm_[pi]
            if cm and refx: cm = cm + iso_marks(p, refx, {m[0] for m in cm})
            tabs = []
            if not cm:
                cm = bold_marks(p); tabs = bold_marks.tables
                if not cm and refx_iso: cm = iso_marks(p, refx_iso, set())
                elif cm and refx: cm = cm + iso_marks(p, refx, {m[0] for m in cm if m[0] is not None})
            else:                              # 글자 검출이 놓친 번호는 굵은 점 검출로 보충
                have = {m[0] for m in cm}
                cm = cm + [m for m in bold_marks(p) if m[0] is not None and m[0] not in have and not (m[0] == 30 and pi == 0)]
            for ci, (cl, cr) in enumerate(cols):
                cw = [w for w in words if cl-2 <= w["x0"] < cr and top-8 <= w["top"] < bottom]
                if elective == "old7":                                  # 선택과목 제목줄('이산수학' 등) 위치: 제목 바로 밑의 번호 글자가 없을 때 26번 머리표를 복원하는 데 쓴다
                    rowsw = {}
                    for w in cw: rowsw.setdefault(round(w["top"]/4), []).append(w)
                    for rk, rw in rowsw.items():
                        tx = "".join(w["text"] for w in sorted(rw, key=lambda w: w["x0"])).replace(" ", "")
                        if tx in ("이산수학", "확률과통계", "미분과적분", "[이산수학]", "[확률과통계]", "[미분과적분]"):
                            heads.append((pi, ci, min(w["top"] for w in rw), max(w["bottom"] for w in rw), min(w["x0"] for w in rw)))
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
                    if cl-6 <= x0_ < cr and x0_ <= cl+60 and top-(24 if pi == 0 else 8) <= t_ < bottom:
                        events.append((pi, ci, t_, "mark", n, (x0_, t_, x1_, b_)))
        for pi_, ci_, t_, n_ in PATCH_MARKS.get(os.path.basename(path), []):     # 글자가 그림이라 코드로 못 찾는 머리표: 육안으로 읽은 위치
            events.append((pi_, ci_, t_, "mark", n_, (cols[ci_][0]+2, t_, cols[ci_][0]+12, t_+10)))
        for pi_, ci_, t_ in PATCH_DROP.get(os.path.basename(path), []):          # 단 맨 아래에 번호만 있고 본문은 다음 단에서 시작하는 문항: 아래쪽 번호 표시를 버린다
            events = [e for e in events if not (e[3] == "mark" and e[0] == pi_ and e[1] == ci_ and abs(e[2]-t_) < 8)]
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        # 번호 순서 확인 및 섹션 부여
        marks = []; gi = 0
        for e in events:
            if e[3] != "mark": continue
            n = e[4]
            if n is None: n = last+1; e = e[:4] + (n,) + e[5:]
            if elective == "old7" and n == restart+1 and last in (pre, 30) and sec_i < 3 and gi == group:       # 선택과목 첫 문항(26)의 번호가 그림이라 안 읽힌 경우: 제목줄 밑에서 복원
                prev = marks[-1] if marks else None
                hs = [h for h in heads if (prev is None or h[:3] > prev[:3]) and h[:3] < e[:3]]
                if hs:
                    h = hs[-1]; sec_i += 1
                    syn = (h[0], h[1], h[3]+1, "mark", restart, (h[4], h[3]+1, h[4]+10, h[3]+11))
                    extra.append(syn); marks.append(syn + (SECTIONS_[sec_i],)); last = restart
            if elective == 'old7' and n == 31 and last == 29: n = 30; e = e[:4] + (30,) + e[5:]
            if elective and n == restart and last in (0, pre, 30): sec_i = 1 if last in (0, pre) else sec_i+1   # last==0: 선택과목 해설만 실린 파일
            elif n == last+1: pass
            elif two and last >= 27 and n <= 4 and n < last: gi += 1; last = n-1       # 가형 해설 뒤에 나형 해설이 이어 붙은 합본
            else: continue
            if gi != group: last = n; continue
            marks.append(e); last = n; marks[-1] = e + (SECTIONS_[sec_i],)
        events.extend(extra)
        if os.environ.get('DBG'): print('events', [(e[0], e[1], round(e[2]), e[3], e[4]) for e in events if e[3] == 'mark'][:60], cols, frames[:2])
        # 흐름(쪽, 단) 순서
        flow = [(pi, ci) for pi in range(len(pdf.pages)) for ci in range(len(cols))]
        items = []
        def objs_in(p, cl, cr, lo, hi):
            r = []
            for c in p.chars: r.append((c["x0"], c["top"], c["x1"], min(c["bottom"], c["top"]+40)))   # 늘어난 큰 괄호 글리프의 bbox 보정
            for o in p.images + p.curves: r.append((o["x0"], o["top"], o["x1"], o["bottom"]))
            if len(p.lines) > 5000:                    # 글자가 윤곽선(선분)으로만 된 쪽
                for o in p.lines:
                    if (o["x1"]-o["x0"] < 3 and o["bottom"]-o["top"] > 300) or o["x1"]-o["x0"] > 200: continue       # 단 구분선·가로 규칙선은 내용이 아님
                    r.append((o["x0"], o["top"], o["x1"], o["bottom"]))
            return [(a, t, b, d) for a, t, b, d in r if a >= cl-3 and b <= cr+3 and t >= lo-2 and t < hi-8]
        WORDS_ = {}
        allev = sorted(events, key=lambda e: (e[0], e[1], e[2]))
        for k, mk in enumerate(marks):
            pi0, ci0, top0 = mk[0], mk[1], mk[2]
            # 끝 사건: 흐름상 바로 다음 사건(번호 마커 또는 구역 제목)
            idx = [(e[0], e[1], e[2], e[3]) for e in allev].index(mk[:3] + (mk[3],))
            # 정상 번호(채택된) 마커 또는 term 만 끝 사건으로
            end = None
            adopted = {(m[0], m[1], m[2], m[3]) for m in marks}
            last_item = (mk[4] == 30 and elective) or k == len(marks)-1
            for e in allev[idx+1:]:
                if e[:3] == mk[:3]: continue                 # 같은 자리에 겹친 가짜 머리표(예: '23' 의 '3')는 끝 사건이 아님
                # 맨 끝 문항 뒤에 붙은 중복(공통) 해설 쪽은 끝 사건으로 본다
                if e[3] == "term" or (last_item and e[3] == "mark" and e[4] is not None and e[4] <= mk[4]) or (e[0], e[1], e[2], e[3]) in [(m[0], m[1], m[2], m[3]) for m in marks]:
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
                if s == s1:                                                   # 답 상자(그림/윤곽선)가 본문 객체 밖에 있으면 상자 끝까지 늘린다
                    if pi not in WORDS_: WORDS_[pi] = p.extract_words()
                    lw = [w for w in WORDS_[pi] if cl-2 <= w["x0"] < cr and bot-2 <= w["top"] < hi-2 and ("\U000f00bc" in w["text"] or w["text"] in ("답", "<답>", "〈답〉") or w["text"].startswith(("<답>", "〈답〉")))]
                    if lw: bt = max(bt, max(w["bottom"] for w in lw) + 8)
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
