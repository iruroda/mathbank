"""글자로 된 문제지에서 문항 아래쪽이 잘리거나(●○ 선택지 등 객체로 잡히지 않는 그림) 확인사항 상자가 섞인 것을 화면 잉크로 바로잡는다.
   사용: python3 tools/fix_bottoms.py 2006-1-03 ...   (data/detect/<eid>.json 의 q 를 고쳐 다시 저장)"""
import json, sys, os, subprocess, tempfile, glob
import numpy as np
import pdfplumber
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fix(eid, near=34, verbose=True):
    y, g, m, *fm = eid.split("-"); nm = f"{y}_{int(g)}학년_{int(m)}월" + (f"({fm[0].replace('ga', '가').replace('na', '나')}형)" if fm else ""); pdfp = f"{R}/pdf/{y}/{nm}_문제.pdf"
    f = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(f))
    d = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", "72", "-png", pdfp, d + "/p"], check=True)
    fs = sorted(glob.glob(d + "/p-*.png")); ims = [np.array(Image.open(p).convert("L")) for p in fs]
    labels = {}
    with pdfplumber.open(pdfp) as pdf:
        for pi, p in enumerate(pdf.pages):
            ws = p.extract_words()
            for i, w in enumerate(ws[:-1]):
                t = w["text"]; t2 = ws[i + 1]["text"]
                if (t.lstrip("＊*※ ") in ("확인", "확확인인") or "확인" in t[:2]) and ("사항" in t2 or "사사항항" in t2): labels.setdefault(pi, []).append((w["x0"], w["top"]))
    sx = q["width"]
    its = sorted(q["items"], key=lambda i: (i["page"], i["col"], i["top"]))
    for k, it in enumerate(its):
        im = ims[it["page"]]; Hh, Ww = im.shape
        sc = Ww / q["width"]
        x0, x1 = int(it["x0"] * sc), int(it["x1"] * sc)
        nxt = [j["top"] for j in its if j["page"] == it["page"] and j["col"] == it["col"] and j["top"] > it["top"] + 5]
        limit = int((min(nxt) - 3) * sc) if nxt else int(Hh * 0.93)
        old = it["bottom"]
        for lx, lt in labels.get(it["page"], []):       # 확인사항 상자: 그 위에서 끝낸다
            if x0 - 10 <= lx * sc <= x1 and it["top"] < lt - 12 < it["bottom"] + 40: limit = min(limit, int((lt - 10) * sc)); it["bottom"] = min(it["bottom"], (lt - 10) - 2)
        cur = int(it["bottom"] * sc); ink = (im[:, x0:x1] < 200).sum(axis=1) > 0
        y2 = cur; yy = cur
        while yy < min(limit, Hh - 1):
            if ink[yy]: y2 = yy
            elif yy - y2 > near: break
            yy += 1
        if y2 > cur: it["bottom"] = float(y2 / sc + 4)
        if verbose and abs(it["bottom"] - old) > 3: print(eid, it["n"], round(old), "->", round(it["bottom"]))
    json.dump([q, a], open(f, "w"), ensure_ascii=False)

if __name__ == "__main__":
    for e in sys.argv[1:]: fix(e)
