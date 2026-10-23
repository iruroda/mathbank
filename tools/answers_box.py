"""해설 문항 영역 안의 '<답> ③' 줄에서 정답을 읽는다 (EBS·평가원형 해설).  -> {(sec, n): 정답}"""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from answers_tab import words
from extract_answers import dec

def read(path, items):
    cache = {}; res = {}
    for it in items:
        got = None
        for b in it["boxes"]:
            pi = b["page"]
            if pi not in cache: cache[pi] = sorted(words(path, pi+1), key=lambda w: (round(w[1]/3), w[0]))
            ws = [w for w in cache[pi] if b["x0"]-2 <= (w[0]+w[2])/2 <= b["x1"]+2 and b["top"]-2 <= (w[1]+w[3])/2 <= b["bottom"]+2]
            for w in ws:
                t = w[4].replace(" ", "")
                if t not in ("답", "<답>", "〈답〉") and not re.fullmatch(r"[<〈]답[>〉].*", t): continue
                yc = (w[1]+w[3])/2
                if t == "답":
                    if not any(u[4] in ("<", "〈") and -3 <= w[0]-u[2] <= 12 and abs((u[1]+u[3])/2-yc) <= 14 for u in ws): continue
                    gt = [u for u in ws if u[4].startswith((">", "〉")) and -3 <= u[0]-w[2] <= 12 and abs((u[1]+u[3])/2-yc) <= 14]
                    if not gt: continue
                    g = gt[0]; rest = g[4][1:]
                    xr = g[2]
                else:
                    m = re.fullmatch(r"[<〈]답[>〉](.*)", t); rest = m.group(1); xr = w[2]
                if not rest:
                    nx = [u for u in ws if -3 <= u[0]-xr <= 30 and abs((u[1]+u[3])/2-yc) <= 14 and u is not w]
                    if not nx: continue
                    rest = min(nx, key=lambda u: u[0])[4]
                rest = dec(rest).replace(" ", "")
                if re.fullmatch(r"[①-⑤]|\d{1,3}", rest): got = rest
        res[(it["sec"], it["n"])] = got
    return res
