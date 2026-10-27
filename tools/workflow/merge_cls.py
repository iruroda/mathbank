"""분류 결과($WORK/out/*.json)를 data/classification/ 에 옮기고, 그림에서 읽은 배점(points)이 있고 검출 캐시에 배점이 비어 있으면 채운다.
   사용: python3 tools/workflow/merge_cls.py [폴더명 ...]   (없으면 out 의 모두)   그 다음 python3 tools/build_all.py"""
import json, os, re, glob, sys
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.environ.get("WORK", "/tmp/mbwork")
SID = {"공통": "C", "확률과 통계": "P", "미적분": "K", "기하": "G", "미분과 적분": "D", "이산수학": "S"}
names = sys.argv[1:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(f"{WORK}/out/*.json"))
mism = []
for name in names:
    d = json.load(open(f"{WORK}/out/{name}.json", encoding="utf-8")); parts = name.split("_")
    y, g, m = parts[:3]; form = parts[3] if len(parts) > 3 else None
    cls = {k: dict(code=v["code"], summary=v["summary"], note=re.sub(r"\s*\[CROP\][^.]*\.?\s*", " ", v.get("note") or "").strip()) for k, v in d.items()}
    json.dump(cls, open(f"{R}/data/classification/{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    eid = f"{y}-{g}-{m}" + (f"-{form}" if form else ""); cp = f"{R}/data/detect/{eid}.json"
    q, a = json.load(open(cp, encoding="utf-8"))
    for it in q["items"]:
        key = f"{SID[it['sec']]}{it['n']:02d}"
        if key not in d: continue
        p = d[key].get("points")
        if it.get("points") is None: it["points"] = p
        elif p is not None and it["points"] != p: mism.append((eid, key, it["points"], p))
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
    print(name, len(cls), "문항 저장")
print("배점 불일치(검출값 우선):", mism)
