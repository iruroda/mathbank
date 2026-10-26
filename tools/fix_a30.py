"""가형·나형 해설이 한 파일일 때 가형 30번 해설 구간에 따라붙은 '나형 정답' 표(제목 '[나 형]'·'수리 나형 정답')를 잘라낸다."""
import json, sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from answers_tab import words
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def fix(eid):
    y, g, m, f = eid.split("-"); af = f"{R}/pdf/{y}/{y}_{int(g)}학년_{int(m)}월(가형)_해설.pdf"
    cp = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(cp, encoding="utf-8"))
    it = a["items"][-1]; assert it["n"] == 30; keep = []
    for b in it["boxes"]:
        ws = words(af, b["page"]+1); hy = None
        inb = [w for w in ws if b["x0"]-3 <= (w[0]+w[2])/2 <= b["x1"]+3 and b["top"] <= w[1] <= b["bottom"]]
        for w in inb:
            t = w[4]
            if t in ("[나", "나형]", "‘나형’", "“나”") or re.fullmatch(r"수리[‘“]?나[’”]?형", t) or (t == "‘나’형"):
                hy = w[1] if hy is None else min(hy, w[1])
        if hy is None: keep.append(b); continue
        if hy - b["top"] < 30: print(eid, "상자 제거", b["page"]); continue
        b["bottom"] = round(hy - 8, 1); keep.append(b); print(eid, "p", b["page"], "->", b["bottom"])
    it["boxes"] = keep
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
if __name__ == "__main__":
    for e in sys.argv[1:]: fix(e)
