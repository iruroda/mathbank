"""[N~M] 형태의 공통 지문(그림 포함)을 찾아 data/stems.json 에 저장 (1학년 2014~2016 등)."""
import json, re, glob, os, pdfplumber
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = {}
for f in sorted(glob.glob(R + "/pdf/201[4-6]/*학년_*월*_문제.pdf")):
    m = re.search(r"(\d{4})_(\d)학년_(\d+)월(?:\((.)형\))?", f); eid = f"{m.group(1)}-{m.group(2)}-{int(m.group(3)):02d}" + ({"가": "-ga", "나": "-na", "A": "-A", "B": "-B"}[m.group(4)] if m.group(4) else "")
    q, a = json.load(open(f"{R}/data/detect/{eid}.json"))
    items = {it["n"]: it for it in q["items"]}
    with pdfplumber.open(f) as pdf:
        for pi, pg in enumerate(pdf.pages):
            for w in pg.extract_words():
                mm = re.match(r"\[(\d+)[~∼\-]?$", w["text"])
                full = re.match(r"\[(\d+)\s*[~∼-]\s*(\d+)\]", w["text"])
                if not (full or mm): continue
                n = int((full or mm).group(1)); it = items.get(n)
                if not it or it["page"] != pi: continue
                if not (it["x0"] - 5 <= w["x0"] <= it["x1"]) : continue
                top = w["top"] - 4
                if top >= it["top"]: continue
                # 같은 단에서 지문 맨 위
                st = dict(n=[n, n + 1], p=pi, x0=it["x0"], t=round(top, 1), x1=it["x1"], b=round(it["top"], 1))
                out.setdefault(eid, []).append(st); print(eid, st)
json.dump(out, open(R + "/data/stems.json", "w"), ensure_ascii=False, indent=1)
