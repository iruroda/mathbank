"""글자 층이 없는(스캔 이미지) 해설 PDF 에서 문항별 해설 영역을 검출한다.
   번호 줄('15. [출제의도] ...')은 영어 OCR(tesseract) 로 첫 단어 '15.' 만 읽어 찾는다 (한글은 못 읽어도 상관없음).
   번호는 1부터 차례로 이어지는 것만 채택. 반환 형식은 detect_a.detect 와 같다(좌표 pt, 좌상단 원점)."""
import sys, os, io, re, csv, json, subprocess, tempfile
import numpy as np, pypdfium2 as pdfium

S = 3.0

def runs(mask):
    out = []; s = None
    for i, v in enumerate(mask):
        if v and s is None: s = i
        if not v and s is not None: out.append((s, i)); s = None
    if s is not None: out.append((s, len(mask)))
    return out

def find_columns(dark, top, bot):
    H, W = dark.shape
    # 단 구분 세로선이 있으면 그것으로 나눈다 (본문 높이의 60% 이상 이어진 세로 잉크)
    cnt = dark[top:bot].sum(0); rule = cnt > 0.6 * (bot - top)
    rr = [r for r in runs(rule) if r[1] - r[0] < 25]
    if rr:
        cents = [(a + b) // 2 for a, b in rr]; xs = np.where(dark[top:bot].any(0))[0]
        edges = [int(xs.min())] + [c for c in cents if xs.min() + 150 < c < xs.max() - 150] + [int(xs.max())]
        out = []
        for a, b in zip(edges[:-1], edges[1:]):
            seg = np.where(dark[top:bot, a + 6:b - 6].any(0))[0]
            if len(seg) and seg.max() - seg.min() > 150: out.append((a + 6 + int(seg.min()), a + 6 + int(seg.max()) + 1))
        if len(out) > 1: return out
    cs = dark[top:bot].sum(0) > 0
    rs = runs(cs); m = []
    for r in rs:
        if m and r[0] - m[-1][1] < 12: m[-1] = (m[-1][0], r[1])
        else: m.append(r)
    return [r for r in m if r[1] - r[0] > 150]

def ocr_marks(img, x0, x1):
    """열 이미지를 OCR 해 번호 후보 [(번호, 좌, 위, 우, 아래)] (px)"""
    c = img.crop((max(0, x0 - 6), 0, min(img.width, x1 + 6), img.height))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t: path = t.name
    c.save(path)
    out = subprocess.run(["tesseract", path, "stdout", "--psm", "6", "tsv"], capture_output=True, text=True).stdout
    os.unlink(path)
    rows = list(csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE))
    lines = {}
    for r in rows:
        if r.get("text") and r["text"].strip():
            lines.setdefault((r["block_num"], r["par_num"], r["line_num"]), []).append(r)
    res = []
    off = max(0, x0 - 6)
    for v in lines.values():
        w = v[0]; t = w["text"].strip()
        mt = re.fullmatch(r"(\d{1,2})[.,]", t)
        if not mt: continue
        l = int(w["left"]) + off; tp = int(w["top"]); r_ = l + int(w["width"]); b = tp + int(w["height"])
        res.append((int(mt.group(1)), l, tp, r_, b))
    return res

def detect(path, expect=30):
    pdf = pdfium.PdfDocument(path)
    pages = []; W0 = H0 = None
    for pi in range(len(pdf)):
        im = pdf[pi].render(scale=S).to_pil().convert("L")
        dark = np.array(im) < 150
        H, W = dark.shape
        if W0 is None: W0, H0 = W / S, H / S
        # 첫 쪽 머리(제목 상자)를 건너뛴다
        top = 0
        if pi == 0:
            rows = dark[:, int(W*.03):int(W*.97)].any(1)
            rs = runs(rows); g = [list(rs[0])] if rs else []
            for r in rs[1:]:
                if r[0] - g[-1][1] < 25: g[-1][1] = r[1]
                else: break
            top = g[0][1] + 5 if g else 0
            hl = [r for r in runs(dark[:int(H*.35)].sum(1) > 0.6 * W)]          # 제목 상자의 가로 테두리(위·아래)
            hl = [r for r in hl if r[1] - r[0] < 30]
            if len(hl) >= 2: top = max(top if top < H*.3 else 0, hl[1][1] + 5)
        pages.append((im, dark, H, W, top))
    # 열 위치는 가장 열이 많이 잡힌 쪽 기준 (모든 쪽에서 같다고 본다)
    cand = []
    for im, dark, H, W, top in pages[1:] or pages:
        cand.append(find_columns(dark, int(H*.04), int(H*.93)))
    cols = max(cand, key=len)
    pcols = []                       # 쪽마다 단 위치가 조금씩 다를 수 있다
    for pi, (im, dark, H, W, top) in enumerate(pages):
        c = find_columns(dark, int(H*.04), int(H*.93))
        pcols.append(c if len(c) >= 2 and len(c) <= len(cols) else cols)
    events = []   # (page, col, y_px, n, l, tp, r, b)
    last = 0
    allm = []
    for pi, (im, dark, H, W, top) in enumerate(pages):
        for ci, (c0, c1) in enumerate(pcols[pi]):
            for n, l, tp, r, b in ocr_marks(im, c0, c1):
                if l - c0 > 45: continue          # 단의 왼쪽 끝에 붙은 번호만
                if tp < top and pi == 0: continue
                allm.append((pi, ci, tp, n, l, tp, r, b))
    allm.sort(key=lambda e: (e[0], e[1], e[2]))
    marks = []
    for e in allm:
        if e[3] == last + 1 and last < expect:
            marks.append(e); last = e[3]
    # 흐름: 쪽 -> 단
    flow = [(pi, ci) for pi in range(len(pages)) for ci in range(len(pcols[pi]))]
    items = []
    def content_rows(dark, c0, c1, lo, hi):
        sub = dark[lo:hi, max(0, c0 - 3):c1 + 3]
        rs = runs(sub.any(1))
        # 쪽 아래 쪽번호(작은 덩어리)는 뺀다
        while rs and (rs[-1][1] - rs[-1][0]) < 60:
            seg = sub[rs[-1][0]:rs[-1][1]]; xs = np.where(seg.any(0))[0]
            gap = rs[-1][0] - rs[-2][1] if len(rs) > 1 else 999
            if len(xs) and (xs.max() - xs.min()) < 110 and gap >= 25 and lo + rs[-1][0] > 0.9 * dark.shape[0]: rs = rs[:-1]
            else: break
        if not rs: return None
        return lo + rs[0][0], lo + rs[-1][1]
    for k, mk in enumerate(marks):
        pi0, ci0, y0 = mk[0], mk[1], mk[2]
        end = marks[k + 1] if k + 1 < len(marks) else None
        s0 = flow.index((pi0, ci0)); s1 = flow.index((end[0], end[1])) if end else len(flow) - 1
        boxes = []
        for s in range(s0, s1 + 1):
            pi, ci = flow[s]; im, dark, H, W, top = pages[pi]; c0, c1 = pcols[pi][ci]
            lo = max(0, y0 - 4) if s == s0 else (top if pi == 0 else 0)
            hi = (end[2] - 4) if (end and s == s1) else H
            if hi - lo < 20: continue
            cr = content_rows(dark, c0, c1, lo, hi)
            if not cr: continue
            t, bt = cr
            if s == s0: t = max(0, y0 - 4)
            if bt - t < 30: continue
            b = dict(page=pi, x0=c0 / S - 3, x1=c1 / S + 3, top=t / S, bottom=(bt + 5) / S)
            boxes.append(b)
        if boxes: boxes[0]["num"] = dict(x0=mk[4] / S, top=mk[5] / S, x1=mk[6] / S, bottom=mk[7] / S)
        items.append(dict(n=mk[3], sec="공통", boxes=boxes))
    return dict(width=W0, height=H0, columns=[(c0 / S - 3, c1 / S + 3) for c0, c1 in cols], items=items)

if __name__ == "__main__":
    r = detect(sys.argv[1])
    if len(sys.argv) > 2: json.dump(r, open(sys.argv[2], "w"), ensure_ascii=False)
    print(len(r["items"]), [(i["n"], len(i["boxes"])) for i in r["items"]])
