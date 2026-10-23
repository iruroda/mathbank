"""해설 PDF 전체에서 '<답> ③' 줄(글자)을 읽는 순서대로 모은다. -> [(쪽, 단, y, 값)]  (단: x 중앙 기준 2단)"""
import re, sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from answers_tab import words
from extract_answers import dec

def labels(path, npages, ncols=2, width=595):
    out = []
    for pi in range(npages):
        ws = words(path, pi+1)
        for w in ws:
            t = w[4].replace(" ", "")
            rest = None; xr = None
            if re.fullmatch(r"[<〈]답[>〉].*", t): rest = re.fullmatch(r"[<〈]답[>〉](.*)", t).group(1); xr = w[2]
            elif t == "답":
                lt = [u for u in ws if u[4] in ("<", "〈") and -3 <= w[0]-u[2] <= 12 and abs(u[1]-w[1]) < 14]
                gt = [u for u in ws if u[4].startswith((">", "〉")) and -3 <= u[0]-w[2] <= 12 and abs(u[1]-w[1]) < 14]
                if not lt or not gt: continue
                rest = gt[0][4][1:]; xr = gt[0][2]
            else: continue
            yc = (w[1]+w[3])/2
            if not rest:
                nx = [u for u in ws if -3 <= u[0]-xr <= 40 and abs((u[1]+u[3])/2-yc) <= 14 and u is not w and u[4] not in ("<", ">")]
                if not nx: continue
                rest = min(nx, key=lambda u: u[0])[4]
            v = dec(rest).replace(" ", "")
            if re.fullmatch(r"[①-⑤]|\d{1,3}", v):
                col = 0 if w[0] < width/ncols else 1
                out.append((pi, col, w[1], v))
    out.sort(key=lambda t: (t[0], t[1], t[2]))
    return out
