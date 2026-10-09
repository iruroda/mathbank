"""글자가 없는(이미지) 문제지 PDF에서 문항 영역을 검출한다.
   번호는 OCR 대신 구조로 찾는다: 문항번호 줄은 단의 왼쪽 기준선에 붙어 있고(보기 ①②.. 줄은 +약 8pt 들여쓰기),
   번호는 1부터 읽는 순서대로 센다. 반환 형식은 detect_q.detect 와 같다(좌표 pt, 좌상단 원점)."""
import sys, json
import numpy as np, pypdfium2 as pdfium
from collections import Counter

S = 3.0

def runs(mask):
    out = []; s = None
    for i, v in enumerate(mask):
        if v and s is None: s = i
        if not v and s is not None: out.append((s, i)); s = None
    if s is not None: out.append((s, len(mask)))
    return out

def page_layout(dark):
    H, W = dark.shape
    colsum = dark.sum(0)
    cand = [x for x in range(int(W*.3), int(W*.7)) if colsum[x] > H*.6]
    div = int(np.mean(cand)) if cand else W//2
    ys = np.where(dark[:, div-1:div+2].any(1))[0]
    bot = int(ys.max())
    rows = dark[:, 30:W-30].sum(1)
    hl = [y for y in range(int(H*.2)) if rows[y] > (W-60)*.6]
    if hl:
        e = hl[0]
        for y in hl[1:]:
            if y - e > 2: break
            e = y
        top = e + 3
    else: top = int(H*.1)
    return div, top, bot

def text_rows(sub, gap=8):
    """줄 묶음: 위·아래 첨자(분수 등)까지 한 줄로 묶는다. -> [(s, e)]"""
    rs = runs(sub.any(1)); out = []
    for s, e in rs:
        if out and s - out[-1][1] <= gap: out[-1] = (out[-1][0], e)
        else: out.append((s, e))
    return out

def is_box(sub, s, e):
    """테두리 상자(단답형/5지선다형 라벨 등)인지"""
    if e - s > 70 or e - s < 20: return False
    seg = sub[s:e]; xs = np.where(seg.any(0))[0]
    if len(xs) < 60: return False
    l, r = xs.min(), xs.max()
    return seg[:, l].mean() > .8 and seg[:, r].mean() > .8 and 120 < (r - l) < 330

def analyze(path):
    pdf = pdfium.PdfDocument(path)
    pages = []
    for pi in range(len(pdf)):
        im = pdf[pi].render(scale=S).to_pil().convert("L")
        dark = np.array(im) < 150
        H, W = dark.shape; div, top, bot = page_layout(dark)
        cols = []
        for ci, (cl, cr) in enumerate([(int(W*.05), div-6), (div+6, int(W*.96))]):
            sub = dark[top:bot-60, cl:cr]            # 하단 쪽번호 상자 제외
            rows = text_rows(sub)
            info = []
            for s, e in rows:
                seg = sub[s:e]; xs = np.where(seg.any(0))[0]
                if len(xs) == 0: continue
                info.append(dict(s=s, e=e, left=cl + int(xs.min()), box=is_box(sub, s, e)))
            cols.append(dict(cl=cl, cr=cr, sub=sub, rows=info))
        pages.append(dict(top=top, bot=bot, div=div, cols=cols, size=(W, H)))
    return pages

def detect(path):
    pdf = pdfium.PdfDocument(path); PW, PH = pdf[0].get_size()
    pages = analyze(path)
    # 단별 기준선(번호 줄 x): 줄 시작 x 의 최빈값들 중 가장 왼쪽 (보기 줄보다 왼쪽)
    M = []
    for ci in (0, 1):
        xs = [r["left"] for pg in pages for r in pg["cols"][ci]["rows"] if not r["box"]]
        cnt = Counter((x // 6) * 6 for x in xs)
        strong = sorted(b for b, c in cnt.items() if c >= 5)
        M.append(strong[0])
    items = []; n = 0
    for pi, pg in enumerate(pages):
        for ci, c in enumerate(pg["cols"]):
            sub, rows = c["sub"], c["rows"]
            marks = [i for i, r in enumerate(rows) if not r["box"] and M[ci]-4 <= r["left"] <= M[ci]+12 and (r["e"]-r["s"]) >= 14]
            for k, ri in enumerate(marks):
                if n >= 30: break
                n += 1
                s = rows[ri]["s"]
                nxt = rows[marks[k+1]]["s"] if k+1 < len(marks) else sub.shape[0]
                # 이 문항에 속하는 줄: 다음 번호 전까지, 단 라벨 상자 이후는 제외
                end = s
                for r in rows[ri:]:
                    if r["s"] >= nxt: break
                    if r["box"] and r["s"] > s + 40: break
                    end = r["e"]
                top = pg["top"] + s
                # 번호 상자(원본 번호 가리기용): 줄 안 첫 글자 덩어리(숫자+마침표)
                r0, r1 = rows[ri]["s"], rows[ri]["e"]
                cs = np.where(sub[r0:r1].any(0))[0]; xa = int(cs[0]); xb = xa
                for v in cs[1:]:
                    if v - xb > 13: break
                    xb = int(v)
                ys = np.where(sub[r0:r1, xa:xb+1].any(1))[0]
                num = dict(x0=(c["cl"]+xa)/S, x1=(c["cl"]+xb)/S+1, top=(pg["top"]+r0+int(ys.min()))/S, bottom=(pg["top"]+r0+int(ys.max()))/S+1)
                items.append(dict(page=pi, col=ci, n=n, sec="공통", x0=c["cl"]/S-1, x1=c["cr"]/S+0.5,
                                  top=top/S-4, bottom=(pg["top"] + end)/S + 6, num=num))
    return dict(width=PW, height=PH, items=items)

if __name__ == "__main__":
    r = detect(sys.argv[1])
    print(len(r["items"]), [(i["page"], i["col"], i["n"]) for i in r["items"]])


def attach_meta(path, res):
    """배점·형식. 배점은 문제 이미지를 OCR(eng)해 '[N' 에서 읽고, 못 읽으면 None."""
    import re, subprocess, tempfile, os
    pdf = pdfium.PdfDocument(path); cache = {}
    for it in res["items"]:
        if it["page"] not in cache: cache[it["page"]] = pdf[it["page"]].render(scale=4).to_pil().convert("L")
        im = cache[it["page"]]; k = 4
        c = im.crop((int(it["x0"]*k), int(it["top"]*k), int(it["x1"]*k), int(it["bottom"]*k)))
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.png"); c.save(p)
            t = subprocess.run(["tesseract", p, "stdout", "--psm", "6"], capture_output=True, text=True).stdout
        m = re.search(r"[\[\(]\s*([234])\s*[^\d\s]{0,2}\s*[\]\)]", t) or re.search(r"\[\s*([234])", t)
        it["points"] = int(m.group(1)) if m else None
        it["type"] = "선택형" if re.search(r"[①②③④⑤]|\(\)|\bO\b", t) and "①" in t else None
        it["_ocr"] = t
