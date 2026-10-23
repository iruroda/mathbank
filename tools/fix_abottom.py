"""해설지에서 해설 구간이 쪽 아래 쪽번호 상자('3 ─ 16')까지 내려간 것(여러 단에 걸친 해설의 첫 조각)과, 마지막 문항(30번)이 남은 단·쪽의 빈 곳까지 늘어난 것을
   글자·그림이 끝나는 곳에서 자른다. 내용이 없는 단은 뺀다.
   사용: python3 tools/fix_abottom.py 2006-1-03 ...  (data/detect/<eid>.json 의 a 를 고침)"""
import json, sys, os, subprocess, tempfile, glob
import numpy as np
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def footer_top(im):
    """쪽 아래 가운데에 있는 쪽번호 상자('3 ─ 16')의 위 끝. 없으면 None."""
    H, W = im.shape; x0, x1 = int(W / 2 - 80), int(W / 2 + 80)
    ink = (im[int(H * 0.86):, x0:x1] < 190).sum(axis=1) > 0; ys = np.where(ink)[0]
    if not len(ys): return None
    blocks = [[ys[0], ys[0]]]
    for yy in ys[1:]:
        if yy - blocks[-1][1] > 3: blocks.append([yy, yy])
        else: blocks[-1][1] = yy
    b = blocks[-1]                                             # 맨 아래 덩어리 (높이 14~40)
    return int(H * 0.86) + b[0] if 12 <= b[1] - b[0] + 1 <= 45 else None

def fix(eid, gap=60):
    y, g, m, *fm = eid.split("-"); nm = f"{y}_{int(g)}학년_{int(m)}월" + (f"({fm[0].replace('ga', '가').replace('na', '나')}형)" if fm else ""); pdfp = f"{R}/pdf/{y}/{nm}_해설.pdf"
    f = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(f))
    d = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", "72", "-png", pdfp, d + "/p"], check=True, stderr=subprocess.DEVNULL)
    fs = sorted(glob.glob(d + "/p-*.png")); ims = {}; footer_tops = {}
    lastn = max(i["n"] for i in a["items"])
    for it in a["items"]:
        out = []
        for b in it["boxes"]:
            im = ims.setdefault(b["page"], np.array(Image.open(fs[b["page"]]).convert("L"))); H, W = im.shape; sc = W / a["width"]
            x0, x1 = int((b["x0"] + 6) * sc), int((b["x1"] - 6) * sc)
            ft = footer_tops.setdefault(b["page"], footer_top(im)); lim = (ft - 3) if ft else int(H * 0.975)
            top, bot = int(b["top"] * sc), min(int(b["bottom"] * sc), lim)
            reach = int(b["bottom"] * sc) > lim                          # 쪽번호 상자 자리까지 내려간 조각만 손댄다
            if not reach and it["n"] != lastn: out.append(b); continue
            ink = (im[top:bot, x0:x1] < 190).sum(axis=1) > 0
            ys = np.where(ink)[0]
            if len(ys) < 6: print(eid, it["n"], "빈 조각 제거", b["page"], round(b["x0"])); continue
            lastink = ys[0]
            if it["n"] == lastn:
                for yy in ys[1:]:
                    if yy - lastink > gap: break
                    lastink = yy
            else: lastink = ys[-1]
            nb = (top + lastink) / sc + 5
            if nb < b["bottom"] - 8: print(eid, it["n"], "끝", b["page"], round(b["x0"]), round(b["bottom"]), "->", round(nb)); b["bottom"] = float(nb)
            out.append(b)
        it["boxes"] = out
    json.dump([q, a], open(f, "w"), ensure_ascii=False)

if __name__ == "__main__":
    for e in sys.argv[1:]: fix(e)
