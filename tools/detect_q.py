"""문제지 PDF에서 문항별 영역(bbox)을 자동 검출한다. 좌표는 pdfplumber 기준(pt, 좌상단 원점)."""
import re, json, sys
import pdfplumber

NUM = re.compile(r'^(\d{1,2})\.')

def page_geometry(p):
    """세로 구분선 x, 본문 상단 y(머리글 선), 본문 하단 y."""
    vs = [o for o in (p.lines + p.rects) if (o["bottom"]-o["top"] > 500 and o["x1"]-o["x0"] < 3)]
    if not vs: return None
    div = vs[0]
    hs = [o for o in (p.lines + p.rects) if (o["x1"]-o["x0"] > 500 and o["bottom"]-o["top"] < 3 and o["top"] < 300)]
    top = max([h["bottom"] for h in hs], default=div["top"])
    return dict(div=(div["x0"]+div["x1"])/2, top=max(top, div["top"]), bottom=div["bottom"])

def objects(p):
    for c in p.chars: yield c["x0"], c["top"], c["x1"], c["bottom"]
    for o in p.images + p.curves: yield o["x0"], o["top"], o["x1"], o["bottom"]
    for o in p.lines + p.rects:
        if o["x1"]-o["x0"] > 400 or o["bottom"]-o["top"] > 400: continue   # 구분선·틀 제외
        yield o["x0"], o["top"], o["x1"], o["bottom"]

def detect(path, elective=False):
    out = []          # (page, col, n, top, x0, x1, bottom)
    last = 0; section = "공통"; sections = ["공통", "확률과 통계", "미적분", "기하"]; sec_i = 0
    with pdfplumber.open(path) as pdf:
        W, H = pdf.pages[0].width, pdf.pages[0].height
        for pi, p in enumerate(pdf.pages):
            g = page_geometry(p)
            if not g: continue
            div = g["div"]
            cols = [(div-336, div-4), (div+4, div+336)]
            words = p.extract_words(keep_blank_chars=False)
            # 표시 라벨 (단답형, 확인 사항 등) 위치: 이 아래 객체는 이전 문항에 포함시키지 않는다
            labels = []
            for i, w in enumerate(words):
                if w["text"] in ("단답형", "5지선다형") and w["top"] > g["top"]:
                    labels.append((w["x0"], w["top"]-10))
                if w["text"].lstrip("＊*○◦ ") == "확인" and i+1 < len(words) and words[i+1]["text"] == "사항" and w["top"] > g["top"]:
                    labels.append((w["x0"], w["top"]-10))
            objs = list(objects(p))
            for ci, (cl, cr) in enumerate(cols):
                mk = []
                for w in words:
                    m = NUM.match(w["text"])
                    if not m or w["top"] < g["top"]-8 or w["bottom"] > g["bottom"]: continue
                    if not (cl+0 <= w["x0"] <= cl+30): continue
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
                for k, (top, n, nb) in enumerate(good):
                    limit = good[k+1][0] if k+1 < len(good) else g["bottom"]
                    cut = min([t for t in lab_in_col if top+20 < t < limit], default=limit)
                    bot = top
                    for x0, t, x1, b in objs:
                        if x0 >= cl-3 and x1 <= cr+3 and t >= top-3 and t < cut-8 and b < g["bottom"]+2:
                            bot = max(bot, b)
                    out.append(dict(page=pi, col=ci, n=n, sec=sections[min(sec_i, 3)],
                                    x0=cl+ (84-(div-420)) if False else cl, x1=cr,
                                    top=top-4, bottom=bot+6, num=dict(x0=nb[0], top=nb[1], x1=nb[2], bottom=nb[3])))
    return dict(width=W, height=H, items=out)

def attach_meta(path, res):
    """배점·형식(선택형/단답형)을 문제 텍스트에서 읽는다."""
    with pdfplumber.open(path) as pdf:
        for it in res["items"]:
            p = pdf.pages[it["page"]]
            crop = p.crop((it["x0"], it["top"], it["x1"], it["bottom"]), strict=False)
            t = crop.extract_text() or ""
            m = re.search(r'\[(\d)점\]', t)
            it["points"] = int(m.group(1)) if m else None
            it["type"] = "선택형" if "①" in t else "단답형"

if __name__ == "__main__":
    f = sys.argv[1]
    r = detect(f); attach_meta(f, r)
    json.dump(r, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print(f, len(r["items"]), [ (i["sec"][:1], i["n"]) for i in r["items"]][:60])
