"""분류 결과 검증. 사용: python3 tools/workflow/validate_cls.py <폴더명>  (예: 2026_3_10, 2026_1_10)  → OK 가 나올 때까지 고친다."""
import json, sys, os
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.environ.get("WORK", "/tmp/mbwork")
name = sys.argv[1]; y, g, m = name.split("_")[:3]
codes = json.load(open(f"{R}/data/standards_codes.json", encoding="utf-8"))
d = json.load(open(f"{WORK}/out/{name}.json", encoding="utf-8"))
keys = sorted(f[:-4] for f in os.listdir(f"{WORK}/cls/{name}") if f.endswith(".png"))
want = "중학교" if (g, int(m)) == ("1", 3) else "고등학교"
ok = True
for k in keys:
    if k not in d: print("MISSING", k); ok = False; continue
    c = d[k].get("code")
    if c == "12이수01-01": continue
    if c not in codes: print("BAD CODE", k, c); ok = False; continue
    if codes[c]["sheet"] != want: print("WRONG SHEET", k, c); ok = False
    if not d[k].get("summary"): print("NO SUMMARY", k); ok = False
    if d[k].get("points") not in (2, 3, 4, None): print("BAD POINTS", k, d[k].get("points")); ok = False
for k in d:
    if k not in keys: print("EXTRA", k); ok = False
print("OK" if ok else "FIX NEEDED", len(d), "/", len(keys))
