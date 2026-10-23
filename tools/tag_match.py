"""이미지 문제지에서 '[N점]' 배점 표시를 템플릿 매칭으로 판독한다(같은 시험지 안에서 글꼴이 같다).
   템플릿은 OCR 이 확실히 읽은 문항에서 따온다."""
import sys, csv, io, re, subprocess, tempfile
import numpy as np, cv2
import pypdfium2 as pdfium
sys.path.insert(0, __file__.rsplit("/", 1)[0])

S = 4.0
def crops(path, items):
    pdf = pdfium.PdfDocument(path); cache = {}; out = {}
    for k, it in enumerate(items):
        pi = it["page"]
        if pi not in cache: cache[pi] = np.array(pdf[pi].render(scale=S).to_pil().convert("L"))
        pg = cache[pi]
        out[k] = pg[int(it["top"]*S):int(it["bottom"]*S), int(it["x0"]*S):int(it["x1"]*S)]
    return out

def tsv_tags(c):
    with tempfile.TemporaryDirectory() as d:
        fp = d+"/c.png"; cv2.imwrite(fp, c)
        t = subprocess.run(["tesseract", fp, "-", "--psm", "6", "-l", "eng", "tsv"], capture_output=True, text=True).stdout
    res = []
    for r in csv.DictReader(io.StringIO(t), delimiter="\t", quoting=csv.QUOTE_NONE):
        tx = r["text"] or ""
        m = re.fullmatch(r"\[\s*([234])\S{0,2}\]?", tx) or re.fullmatch(r"\[?([234])\S{0,2}\]", tx)
        if m and ("[" in tx and "]" in tx): res.append((int(m.group(1)), int(r["left"]), int(r["top"]), int(r["width"]), int(r["height"])))
    return res

def tight(c, x, y, w, h):
    sub = c[max(y-4, 0):y+h+4, max(x-4, 0):x+w+4] < 150
    ys, xs = np.where(sub)
    return c[max(y-4, 0)+ys.min():max(y-4, 0)+ys.max()+1, max(x-4, 0)+xs.min():max(x-4, 0)+xs.max()+1]

def read(path, items, templates=None):
    cs = crops(path, items)
    if templates is None:
        votes = {2: [], 3: [], 4: []}
        for n, c in cs.items():
            for v, x, y, w, h in tsv_tags(c):
                if 60 < w < 400 and h < 120: votes[v].append((n, tight(c, x, y, w, h)))
        templates = {}
        for v, L in votes.items():
            if L: templates[v] = [t for n, t in L[:4]]
    out = {}
    for n, c in cs.items():
        sc = {}
        for v, ts in templates.items():
            best = -1
            for t in ts:
                if t.shape[0] >= c.shape[0] or t.shape[1] >= c.shape[1]: continue
                r = cv2.matchTemplate(c, t, cv2.TM_CCOEFF_NORMED); best = max(best, float(r.max()))
            sc[v] = best
        k = max(sc, key=sc.get); srt = sorted(sc.values(), reverse=True)
        out[n] = (k, round(sc[k], 2), round(srt[0]-srt[1], 2) if len(srt) > 1 else 1)
    return out, templates


def read2(path, items):
    """1) '점]' 부분을 템플릿 매칭으로 찾고 2) 그 왼쪽 '[숫자' 창을 숫자별 템플릿과 비교"""
    cs = crops(path, items)
    votes = {2: [], 3: [], 4: []}
    for n, c in cs.items():
        for v, x, y, w, h in tsv_tags(c):
            if 60 < w < 400 and h < 120: votes[v].append(tight(c, x, y, w, h))
    cut = {v: int(L[0].shape[1]*0.5) for v, L in votes.items() if L}
    suf = [L[0][:, cut[v]:] for v, L in votes.items() if L][:3]
    left = {v: [t[:, :cut[v]] for t in L[:3]] for v, L in votes.items() if L}
    out = {}
    for n, c in cs.items():
        bestloc, bs = None, -1
        for sf in suf:
            if sf.shape[0] >= c.shape[0] or sf.shape[1] >= c.shape[1]: continue
            r = cv2.matchTemplate(c, sf, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
            if mx > bs: bs, bestloc, bsf = mx, loc, sf
        if bestloc is None or bs < 0.6: out[n] = (None, round(bs, 2), 0); continue
        x, y = bestloc; h = bsf.shape[0]
        sc = {}
        for v, ts in left.items():
            best = -1
            for t in ts:
                lw = t.shape[1]
                win = c[max(y-3, 0):y+h+3, max(x-lw-6, 0):x+3]
                if t.shape[0] > win.shape[0] or t.shape[1] > win.shape[1]: continue
                r = cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED); best = max(best, float(r.max()))
            sc[v] = best
        k = max(sc, key=sc.get); srt = sorted(sc.values(), reverse=True)
        out[n] = (k, round(bs, 2), round(srt[0]-srt[1], 2))
    return out
