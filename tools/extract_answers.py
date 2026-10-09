"""해설 PDF의 정답표에서 정답을 읽는다 (표 형식: 교육청형 표 / 평가원형 '01. ④' 줄글).
   한글 수식 글꼴의 숫자(사설영역 U+E033~E03C)는 0~9 로 되돌린다.
   사용: python3 tools/extract_answers.py <연도> <학년> <월>  -> 읽은 값 출력"""
import re, sys, json, os
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIR = "①②③④⑤"
SECS = ["확률과 통계", "미적분", "기하"]

def dec(s):
    out = []
    for ch in s or "":
        o = ord(ch)
        if 0xE033 <= o <= 0xE03C: out.append(str(o - 0xE033))
        elif 0x2780 <= o <= 0x2784: out.append(CIR[o - 0x2780])      # ➀~➄
        elif 0x24F5 <= o <= 0x24F9: out.append(CIR[o - 0x24F5])      # ⓵~⓹ (평가원형 글머리 숫자)
        elif ch in CIR or ch.isdigit(): out.append(ch)
        elif ch.isspace(): out.append(" ")
        # 그 밖의 글자(부호·조각)는 버린다
    return re.sub(r"\s+", " ", "".join(out)).strip()

def cell_text(page, bbox):
    c = page.crop(bbox, strict=False)
    return dec("".join(ch["text"] for ch in sorted(c.chars, key=lambda x: (round(x["top"]/3), x["x0"]))))

def table_pairs(page):
    """교육청형 표: 한 행에 [번호, 정답] 칸이 번갈아 나온다."""
    res = []
    for t in page.find_tables():
        for row in t.rows:
            cells = [cell_text(page, c) if c else "" for c in row.cells]
            k = 0
            while k + 1 < len(cells):
                lab, ans = cells[k], cells[k+1]
                if re.fullmatch(r"\d{1,2}", lab) and ans:
                    res.append((int(lab), ans.replace(" ", ""), t.bbox[1]))
                    k += 2
                else:
                    k += 1
    return res

ANS = r"([①-⑤]|\d{1,3})"
def text_pairs(page):
    """평가원형 줄글: '01. ④ 02. ④ ...' / '■ [선택: 미적분] 23. ③ 24. ② ...' 를 (머리표, 번호, 정답) 으로"""
    ws = page.extract_words(keep_blank_chars=False)
    chs = [c for c in page.chars if c["text"].strip()]
    return chs

def read_b(path):
    """평가원형 줄글 정답: '01. ④ 02. ④ ...' -> (쪽, y, 번호, 정답)  (한 줄에 2쌍 이상인 줄만)"""
    out = []
    with pdfplumber.open(path) as pdf:
        for pi, p in enumerate(pdf.pages):
            ws = p.extract_words(keep_blank_chars=False, extra_attrs=[])
            rows = {}
            for w in ws: rows.setdefault(round(w["top"]/3), []).append(w)
            for k in sorted(rows):
                r = sorted(rows[k], key=lambda w: w["x0"])
                toks = [(dec(w["text"]), w) for w in r]
                found = []
                for a in range(len(toks)-1):
                    t, w = toks[a]; u, w2 = toks[a+1]
                    if re.fullmatch(r"\d{1,2}\.", r[a]["text"].strip()) and re.fullmatch(r"[①-⑤]|\d{1,3}", u) and -2 <= w2["x0"]-w["x1"] < 20:
                        found.append((int(r[a]["text"].strip()[:-1]), u, w["top"]))
                if len(found) >= 2:
                    for n, u, y in found: out.append((pi, y, n, u))
    return out

def read(path, grade, elective):
    pairs = []
    with pdfplumber.open(path) as pdf:
        for pi, p in enumerate(pdf.pages):
            for n, a, y in table_pairs(p):
                pairs.append((pi, y, n, a))
    return pairs

def norm(n, a):
    """칸에 끼어든 낱숫자 조각을 걷어 낸다: 선택형 칸은 ①~⑤ 한 글자만, 아니면 그대로."""
    c = [ch for ch in a if ch in CIR]
    return c[-1] if c else a

def assemble(pairs, grade, elective):
    """표에서 읽은 (쪽, y, 번호, 정답) -> 정답 dict.  3학년: {'공통':{1..22}, '확률과 통계':{23..30}, ...}"""
    if not (grade == 3 and elective):
        out = {}
        for _, _, n, a in pairs:
            if 1 <= n <= 30: out.setdefault(str(n), norm(n, a))
        return out
    out = {"공통": {}}
    def fits(n, a):       # 선택형(1~15, 23~28) = ①~⑤, 단답형 = 숫자  (끼워진 중복 쪽의 다른 표를 거른다)
        return (a in tuple(CIR)) if (n <= 15 or 23 <= n <= 28) else a.isdigit()
    pairs = [(a_, b_, c_, norm(c_, d_)) for a_, b_, c_, d_ in pairs]
    pairs = [t for t in pairs if 1 <= t[2] <= 30 and fits(t[2], t[3])]
    for pi, y, n, a in pairs:               # 공통 1~22: 처음 나온 것
        if n <= 22 and str(n) not in out["공통"]: out["공통"][str(n)] = a
    si, want = -1, 23
    for pi, y, n, a in pairs:               # 선택 23~30: 23부터 차례로 이어지는 묶음만
        if n == 23 and want in (23, 31) and si < 2:
            si += 1; want = 23
        if si >= 0 and n == want and want <= 30:
            out.setdefault(SECS[si], {})[str(n)] = a; want += 1
            if want == 31: want = 31
    return out

if __name__ == "__main__":
    y, g, m = sys.argv[1:4]
    f = os.path.join(ROOT, f"pdf/{y}/{y}_{g}학년_{m}월_해설.pdf")
    for pr in read(f, int(g), int(g) == 3): print(pr)
