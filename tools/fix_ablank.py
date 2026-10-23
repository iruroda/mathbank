"""해설 구간(조각) 맨 아래의 긴 빈 곳을 글자·그림이 끝나는 곳에서 자른다. 사용: python3 tools/fix_ablank.py 2006-2-03 ..."""
import json, sys, os
import numpy as np, pypdfium2 as pdfium
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 2
def fix(eid, minblank=30):
    y, g, m, *fm = eid.split("-"); nm = f"{y}_{int(g)}학년_{int(m)}월" + (f"({fm[0].replace('ga', '가').replace('na', '나')}형)" if fm else "")
    cp = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(cp, encoding="utf-8"))
    pdf = pdfium.PdfDocument(f"{R}/pdf/{y}/{nm}_해설.pdf"); cache = {}; ch = 0
    for it in a["items"]:
        for b in it["boxes"]:
            if b["page"] not in cache: cache[b["page"]] = np.array(pdf[b["page"]].render(scale=S).to_pil().convert("L")) < 190
            im = cache[b["page"]][int(b["top"]*S):int(b["bottom"]*S), int(b["x0"]*S):int(b["x1"]*S)]
            ink = np.where(im.any(axis=1))[0]
            if not len(ink): continue
            blank = (im.shape[0]-1-ink[-1]) / S
            top0 = b["top"]
            if blank > minblank: b["bottom"] = round(top0 + ink[-1]/S + 8, 1); ch += 1
            if ink[0] / S > 25 and not (it["boxes"][0] is b): b["top"] = round(top0 + ink[0]/S - 6, 1); ch += 1
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False); print(eid, "빈 곳 자름", ch)
if __name__ == "__main__":
    for e in sys.argv[1:]: fix(e)
