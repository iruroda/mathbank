"""해설 PDF 의 정답표(행: 번호 ① 번호 ② ...)를 읽는다 (pdftotext -bbox 단어 좌표 사용; pdfminer 가 놓치는 ①~⑤ 도 읽힌다).
   -> [(쪽, y, x, 번호, 정답)]  (쪽·읽는 순서)"""
import re, sys, os, subprocess, html
sys.path.insert(0, os.path.dirname(__file__))
from extract_answers import dec

W = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
def words(path, p):
    t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-bbox", path, "-"], capture_output=True, text=True).stdout
    return [(float(a), float(b), float(c), float(d), html.unescape(e)) for a, b, c, d, e in W.findall(t)]

def read_tables(path, pages):
    """번호 칸 바로 오른쪽(같은 줄 ±8pt) 칸을 정답으로 읽는다. 한 줄에 번호가 1씩 늘며 3개 이상 있어야 표로 본다. -> [(쪽, y, x, 번호, 정답)]"""
    res = []
    for pi in pages:
        ws = words(path, pi+1)
        toks = sorted([((w[1]+w[3])/2, w[0], w[2], dec(w[4])) for w in ws], key=lambda t: (round(t[0]/3), t[1]))
        used = set(); found = []
        for a, t in enumerate(toks):
            if a in used or not re.fullmatch(r"\d{1,2}", t[3]) or not (1 <= int(t[3]) <= 30): continue
            best = None
            for b, u in enumerate(toks):
                if b == a or b in used: continue
                if 2 <= u[1]-t[2] <= 40 and abs(u[0]-t[0]) <= 8 and re.fullmatch(r"[①-⑤]|\d{1,3}", u[3]):
                    if best is None or u[1] < toks[best][1]: best = b
            if best is not None: found.append((a, best)); used.add(best)
        # 같은 줄(±8pt)에서 번호가 이어지는 묶음만 (표가 아닌 글 속 숫자 제거)
        cand = [(toks[a][0], toks[a][1], int(toks[a][3]), toks[b][3]) for a, b in found]
        for y, x, n, ans in cand:
            neigh = [c for c in cand if abs(c[0]-y) <= 8 and c[2] != n and abs(c[2]-n) <= 5]
            if len(neigh) >= 2: res.append((pi, y, x, n, ans))
    return res

if __name__ == "__main__":
    r = read_tables(sys.argv[1], [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0])
    print(len(r)); print([(p, round(y), n, a) for p, y, x, n, a in r])

def blocks(path, pages):
    """정답표 묶음들: [[(번호, 정답), ...], ...] (읽는 순서). 번호가 1씩 이어지는 줄(3개 이상)들을 이어 붙인다."""
    cand = read_tables(path, pages)
    rows = {}
    for pi, y, x, n, a in cand: rows.setdefault((pi, round(y/8)), []).append((x, n, a))
    out = []; cur = []; last = None
    for key in sorted(rows):
        r = sorted(rows[key])
        # 가장 긴 연속(+1) 부분열
        best = []; seq = [r[0]]
        for t in r[1:]:
            if t[1] == seq[-1][1]+1 and t[0]-seq[-1][0] > 15: seq.append(t)
            else:
                if len(seq) > len(best): best = seq
                seq = [t]
        if len(seq) > len(best): best = seq
        if len(best) < 3: continue
        pairs = [(n, a) for x, n, a in best]
        if cur and pairs[0][0] == cur[-1][0]+1: cur += pairs
        else:
            if cur: out.append(cur)
            cur = list(pairs)
    if cur: out.append(cur)
    return out
