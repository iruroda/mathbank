"""문제지 PDF에서 문항별 영역(bbox)을 자동 검출한다. 좌표는 pdfplumber 기준(pt, 좌상단 원점)."""
import re, json, sys
import pdfplumber

NUM = re.compile(r'^(\d{1,2})\.')

def page_geometry(p):
    """세로 구분선 x, 본문 상단 y(머리글 선), 본문 하단 y."""
    vs = [o for o in (p.lines + p.rects) if (o["bottom"]-o["top"] > 500 and o["x1"]-o["x0"] < 3)]
    if not vs: return None
    vs.sort(key=lambda o: abs((o["x0"]+o["x1"])/2 - p.width/2))
    div = vs[0]
    hs = [o for o in (p.lines + p.rects) if (o["x1"]-o["x0"] > 500 and o["bottom"]-o["top"] < 3 and o["top"] < 300)]
    top = max([h["bottom"] for h in hs], default=div["top"])
    return dict(div=(div["x0"]+div["x1"])/2, top=max(top, div["top"]), bottom=div["bottom"])

def objects(p):
    for c in p.chars: yield c["x0"], c["top"], c["x1"], min(c["bottom"], c["top"]+40)   # 늘어난 큰 괄호 글리프의 bbox 보정
    for o in p.images + p.curves: yield o["x0"], o["top"], o["x1"], o["bottom"]
    for o in p.lines + p.rects:
        if o["x1"]-o["x0"] > 400 or o["bottom"]-o["top"] > 400: continue   # 구분선·틀 제외
        yield o["x0"], o["top"], o["x1"], o["bottom"]

def dd(t):
    """겹쳐 찍힌(가짜 굵은체) 글자 '확확인인' -> '확인' 으로 되돌린다."""
    return t[0::2] if len(t) >= 2 and len(t) % 2 == 0 and t[0::2] == t[1::2] else t

def fix_words(ws):
    """'29' + '.' 처럼 쪼개진 문항번호 토큰을 합친다."""
    out = []; used = set()
    for i, w in enumerate(ws):
        if i in used: continue
        if re.fullmatch(r'\d{1,2}', w["text"]):
            for j, n in enumerate(ws):
                if j != i and j not in used and n["text"] == "." and abs(n["top"]-w["top"]) < 6 and -4 <= n["x0"]-w["x1"] < 6:
                    w = dict(w, text=w["text"]+".", x1=n["x1"]); used.add(j); break
        out.append(w)
    return out

def detect(path, elective=False):
    out = []          # (page, col, n, top, x0, x1, bottom)
    last = 0; section = "공통"; sections = ["공통", "확률과 통계", "미적분", "기하"]; sec_i = 0
    with pdfplumber.open(path) as pdf:
        W, H = pdf.pages[0].width, pdf.pages[0].height
        for pi, p in enumerate(pdf.pages):
            g = page_geometry(p)
            if not g: continue
            div = g["div"]
            cols = [(max(div-336, 40), div-4), (div+4, min(div+336, p.width-20))]   # A4(폭 595)도 지원
            words = fix_words(p.extract_words(keep_blank_chars=False))
            # 표시 라벨 (단답형, 확인 사항 등) 위치: 이 아래 객체는 이전 문항에 포함시키지 않는다
            labels = []
            for i, w in enumerate(words):
                if dd(w["text"]) in ("단답형", "5지선다형") and w["top"] > g["top"]:
                    labels.append((w["x0"], w["top"]-10))
                if dd(w["text"]).lstrip("＊*○◦※ ") == "확인" and i+1 < len(words) and dd(words[i+1]["text"]) == "사항" and w["top"] > g["top"]:
                    labels.append((w["x0"], w["top"]-10))
            objs = list(objects(p))
            objs_t = [(c["x0"], c["top"], c["x1"], c["bottom"]) for c in p.chars if c["text"].strip()] + [(o["x0"], o["top"], o["x1"], o["bottom"]) for o in p.images + p.curves]
            for ci, (cl, cr) in enumerate(cols):
                mk = []
                for w in words:
                    m = NUM.match(w["text"])
                    if not m or w["top"] < g["top"]-8 or w["bottom"] > g["bottom"]: continue
                    if not (cl-8 <= w["x0"] <= cl+30): continue
                    mk.append((w["top"], int(m.group(1)), (w["x0"], w["top"], w["x1"], w["bottom"])))
                mk.sort()
                # 순서가 맞는 번호만 채택
                good = []
                for top, n, nb in mk:
                    exp = last+1
                    if n == exp or (elective and last in (22, 30) and n == 23):
                        if elective and n == 23 and last in (22, 30):
                            sec_i = sec_i+1 if last == 30 else 1
                        good.append((top, n, nb)); last = n
                lab_in_col = [t for x, t in labels if cl-5 <= x <= cr]
                def ext(top):
                    """표지(번호) 줄보다 위로 삐져나온 수식(분수 등)까지 이 문항의 시작으로 본다."""
                    inc = [(t, b) for x0, t, x1, b in objs_t if x0 >= cl-3 and x1 <= cr+3 and max(top-34, g["top"]+1) <= t < top-1 and b > top+2]
                    if not inc: return top
                    cur = min(t for t, b in inc)
                    while True:      # 위로 맞닿은 수식 조각을 이어서 포함
                        more = [t for x0, t, x1, b in objs_t if x0 >= cl-3 and x1 <= cr+3 and max(cur-30, g["top"]+1) <= t < cur-0.5 and b >= cur-2]
                        if not more: break
                        cur = min(more)
                    return cur
                tops = [ext(t) for t, n, nb in good]
                for k, (top, n, nb) in enumerate(good):
                    limit = tops[k+1] if k+1 < len(good) else g["bottom"]
                    top = tops[k]; mtop = good[k][0]
                    cut = min([t for t in lab_in_col if mtop+20 < t < limit], default=limit)
                    bot = top
                    for x0, t, x1, b in objs:
                        if x0 >= cl-3 and x1 <= cr+3 and t >= top-3 and t < cut-8 and b < g["bottom"]+2 and (t >= top-3):
                            bot = max(bot, b)
                    out.append(dict(page=pi, col=ci, n=n, sec=sections[min(sec_i, 3)],
                                    x0=cl+ (84-(div-420)) if False else cl, x1=cr,
                                    top=top-4, bottom=min(bot+6, limit-4) if k+1 < len(good) else bot+6, num=dict(x0=nb[0], top=nb[1], x1=nb[2], bottom=nb[3])))
    return dict(width=W, height=H, items=out)

def _fix_points(items):
    """배점 숫자가 수식 폰트(사설영역 문자)인 파일은 코드 순서대로 연속 숫자로 환산한다.
       기준값 b(가장 작은 PUA 코드의 점수)는 2·3·4 중에서, 같은 구역·같은 형식 안에서 번호가 커질수록 배점이 줄지 않는 값으로 고른다.
       (일반 숫자와 PUA 숫자가 한 시험에 섞여 있는 파일도 처리)"""
    codes = [it["pcode"] for it in items if it.get("pcode")]
    pu = sorted({ord(c) for c in codes if not c.isdigit()})
    def val(c, b): return None if c is None else int(c) if c.isdigit() else b + ord(c) - pu[0]
    best = 2
    if pu:
        for b in (2, 3, 4):
            vs = [val(it.get("pcode"), b) for it in items]
            if any(v is not None and v not in (2, 3, 4) for v in vs): continue
            ok = True; prev = {}
            for it, v in zip(items, vs):
                k = (it["sec"], it["type"] if "type" in it else "")
                if v is None: continue
                if k in prev and v < prev[k]: ok = False; break
                prev[k] = v
            if ok: best = b; break
    for it in items:
        c = it.pop("pcode", None)
        it["points"] = val(c, best)

def attach_meta(path, res):
    """배점·형식(선택형/단답형)을 문제 텍스트에서 읽는다."""
    with pdfplumber.open(path) as pdf:
        for it in res["items"]:
            p = pdf.pages[it["page"]]
            crop = p.crop((it["x0"], it["top"], it["x1"], it["bottom"]), strict=False)
            t = crop.extract_text() or ""
            m = re.search(r'\[(.)점\]', t)
            it["pcode"] = m.group(1) if m else None
            it["type"] = "선택형" if "①" in t else "단답형"
    _fix_points(res["items"])

if __name__ == "__main__":
    f = sys.argv[1]
    r = detect(f); attach_meta(f, r)
    json.dump(r, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(f, len(r["items"]), [ (i["sec"][:1], i["n"]) for i in r["items"]][:60])
