"""2007~2009 3학년 분류 결과(work1719/out/*.json)를 data/classification/ 에 옮기고, 읽은 배점을 data/detect 캐시에 적어 넣는다."""
import json, os, re, glob
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = "/home/claude/work1719/out"
SEC = {"C": "공통", "D": "미분과 적분", "P": "확률과 통계", "S": "이산수학"}
SID = {v: k for k, v in SEC.items()}
mism = []
for f in sorted(glob.glob(f"{OUT}/200[6789]_3_*.json")):
    name = os.path.basename(f)[:-5]; y, g, m, form = name.split("_")
    d = json.load(open(f, encoding="utf-8"))
    cls = {}
    for k, v in d.items():
        note = re.sub(r"\s*\[CROP\][^.]*\.?\s*", " ", v.get("note") or "").strip()
        cls[k] = dict(code=v["code"], summary=v["summary"], note=note)
    json.dump(cls, open(f"{R}/data/classification/{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    eid = f"{y}-3-{m}-{form}"; cp = f"{R}/data/detect/{eid}.json"
    q, a = json.load(open(cp, encoding="utf-8"))
    for it in q["items"]:
        key = f"{SID[it['sec']]}{it['n']:02d}"
        if key not in d: continue
        p = d[key].get("points")
        if it.get("points") is None: it["points"] = p
        elif p is not None and it["points"] != p: mism.append((eid, key, it["points"], p))
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
print("mismatch", mism)
