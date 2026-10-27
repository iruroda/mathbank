"""새 시험의 문항 그림(PNG)을 만들어 단원 분류 작업용 폴더에 둔다 (data/detect 캐시가 있어야 함: 먼저 build_all.py 를 돌려 검출).
   사용: python3 tools/workflow/crop_new.py 2026-3-10 2026-1-10 ...   (eid 앞부분 일치: '2026-3-10' → 가/나형이면 -ga, -na 모두)
   출력: $WORK/cls/<연도>_<학년>_<월2자리>[_ga|_na]/C01.png, (3학년 2021~ 선택과목) P23.png K23.png G23.png ...   ($WORK 기본값 /tmp/mbwork)
         $WORK/names.txt = 만든 폴더 이름 목록"""
import json, os, sys, glob
import pypdfium2 as pdfium
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(R, "tools"))
from build_all import EXAMS, FORM_ID, SECID
WORK = os.environ.get("WORK", "/tmp/mbwork")
dups = {}
for f in sorted(glob.glob(f"{R}/data/dup*.json")):
    for k, v in json.load(open(f, encoding="utf-8")).items():
        if not k.startswith("_"): dups[k] = v
stems = json.load(open(f"{R}/data/stems.json", encoding="utf-8")) if os.path.exists(f"{R}/data/stems.json") else {}
only = sys.argv[1:]; tot = 0; names = []
for ex in EXAMS:
    y, g, m = ex[:3]; f = ex[3] if len(ex) > 3 else None
    eid = f"{y}-{g}-{m:02d}{FORM_ID[f]}"
    if not any(eid.startswith(o) for o in only): continue
    nm = f"{y}_{g}학년_{m}월" + (f"({f}형)" if f else "")
    dm = dups.get(f"{y}-{g}-{m}", {"same": {}}) if f else {"same": {}}
    drop = {int(k) for k in dm["same"]} if f in ("나", "B") else set()      # 가/나·A/B 중복 문항은 가형(A형)에만 둔다
    q, a = json.load(open(f"{R}/data/detect/{eid}.json", encoding="utf-8"))
    pdf = pdfium.PdfDocument(f"{R}/pdf/{y}/{nm}_문제.pdf")
    sfx = {None: "", "가": "_ga", "나": "_na", "A": "_A", "B": "_B"}[f]
    od = f"{WORK}/cls/{y}_{g}_{m:02d}{sfx}"; os.makedirs(od, exist_ok=True); names.append(os.path.basename(od))
    cache = {}
    def cr(pg, x0, t, x1, b):
        if pg not in cache: cache[pg] = pdf[pg].render(scale=2).to_pil().convert("RGB")
        return cache[pg].crop((int(x0 * 2), int(t * 2), int(x1 * 2), int(b * 2)))
    for it in q["items"]:
        if it["n"] in drop and it.get("sec", "공통") == "공통": continue
        parts = [cr(s["p"], s["x0"], s["t"], s["x1"], s["b"]) for s in stems.get(eid, []) if it["n"] in s["n"]]
        parts.append(cr(it["page"], it["x0"], it["top"], it["x1"], it["bottom"]))
        W = max(p.width for p in parts); H = sum(p.height for p in parts); o = Image.new("RGB", (W, H), "white"); yy = 0
        for p in parts: o.paste(p, (0, yy)); yy += p.height
        o.save(f"{od}/{SECID[it.get('sec', '공통')]}{it['n']:02d}.png"); tot += 1
open(f"{WORK}/names.txt", "w").write("\n".join(names)); print(tot, "PNG,", len(names), "폴더:", names)
