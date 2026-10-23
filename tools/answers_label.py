"""해설 문항 영역 오른쪽 끝의 '답 ③' 상자(상자는 그림, 안의 값만 글자)에서 정답을 읽는다."""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from answers_tab import words
from extract_answers import dec

def read(path, items):
    cache = {}; res = {}
    for it in items:
        cands = []
        for b in it["boxes"]:
            pi = b["page"]
            if pi not in cache: cache[pi] = words(path, pi+1)
            ws = [w for w in cache[pi] if b["x0"]-2 <= (w[0]+w[2])/2 <= b["x1"]+2 and b["top"]-2 <= (w[1]+w[3])/2 <= b["bottom"]+2]
            for w in ws:
                v = dec(w[4]).replace(" ", "")
                if not re.fullmatch(r"[①-⑤]|\d{1,3}", v): continue
                if w[0] < b["x1"]-48 or w[2] > b["x1"]+4: continue
                yc = (w[1]+w[3])/2
                left = [u for u in ws if u is not w and abs((u[1]+u[3])/2-yc) < 6 and u[2] <= w[0]+1 and w[0]-u[2] < 22 and dec(u[4]).strip()]
                if left: continue
                cands.append((pi, w[1], v))
        res[(it["sec"], it["n"])] = cands[-1][2] if cands else None
    return res
