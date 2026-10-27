"""data/standards_codes.json 에서 분류 지침용 코드 목록(codes_hs.txt, codes_ms.txt)을 만든다. 사용: python3 tools/workflow/make_codes_txt.py"""
import json, os
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
c = json.load(open(f"{R}/data/standards_codes.json", encoding="utf-8"))
out = {"고등학교": [], "중학교": []}; last = {}
for code, v in c.items():
    h = f"{v['subject']} / {v['unit']}"
    if last.get(v["sheet"]) != h: out[v["sheet"]].append(f"## {h}"); last[v["sheet"]] = h
    out[v["sheet"]].append(f"{code}  {v['text']}")
for sheet, fn in (("고등학교", "codes_hs.txt"), ("중학교", "codes_ms.txt")):
    open(os.path.join(os.path.dirname(__file__), fn), "w", encoding="utf-8").write("\n".join(out[sheet]) + "\n")
print({k: len(v) for k, v in out.items()})
