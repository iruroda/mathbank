"""전 시험 문제 영역 검출 + 단원 분류 + 정답을 합쳐 data/problems.json 을 만든다.
   사용: python3 tools/build_all.py
   분류 입력: 2021년 6월은 data/classification_2021_06.xlsx, 나머지는 data/classification/<연도>_<학년>_<월2자리>.json"""
import json, os, sys
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
import detect_q, detect_a

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECID = {"공통": "C", "확률과 통계": "P", "미적분": "K", "기하": "G"}
SEC_KEY = {"C": "공통", "P": "확률과 통계", "K": "미적분", "G": "기하"}
ISU = dict(subject="이산수학", unit="선택과 배열",
           standard="원순열, 염주순열, 중복순열, 같은 것이 있는 순열을 이해하고, 그 순열의 수를 구하는 방법을 설명할 수 있다.")
EXAMS = [(2021, 1, 3), (2021, 1, 6), (2021, 1, 9), (2021, 1, 11),
         (2021, 2, 3), (2021, 2, 6), (2021, 2, 9), (2021, 2, 11),
         (2021, 3, 3), (2021, 3, 4), (2021, 3, 6), (2021, 3, 7), (2021, 3, 9), (2021, 3, 10), (2021, 3, 11)]
EXAMS += [(2022, g, m) for g in (1, 2) for m in (3, 6, 9, 11)] + [(2022, 3, m) for m in (3, 4, 6, 7, 9, 10, 11)]
# 2023~2026 (EBSi): 1·2·3학년. 3학년은 3·4(5)·6·7·9·10·11월
_M = {2023: {1: (3, 6, 9, 11), 2: (3, 6, 9, 11), 3: (3, 4, 6, 7, 9, 10, 11)},
      2024: {1: (3, 6, 9, 10), 2: (3, 6, 9, 10), 3: (3, 5, 6, 7, 9, 10, 11)},
      2025: {1: (3, 6, 9, 10), 2: (3, 6, 9, 10), 3: (3, 5, 6, 7, 9, 10, 11)},
      2026: {1: (3, 6, 9), 2: (3, 6, 9), 3: (3, 5, 6, 7, 9)}}
for _y, _d in _M.items():
    EXAMS += [(_y, _g, _m) for _g in (1, 2, 3) for _m in _d[_g]]
# 2020 (2015 개정): 3학년은 가형/나형 별도 시험지. 가형 먼저. 중복(동일) 문항은 가형만 수록 (data/dup2020.json)
EXAMS += [(2020, g, m) for g in (1, 2) for m in (3, 6, 9, 11)]
EXAMS += [(2020, 3, m, f) for m in (3, 4, 6, 7, 9, 10, 11) for f in ("가", "나")]
# 2017~2019 (2009 개정): 2·3학년이 가형/나형 별도 시험지. 1학년은 단일. 중복 문항은 data/dup2017_19.json
for _y in (2017, 2018, 2019):
    EXAMS += [(_y, 1, m) for m in (3, 6, 9, 11)]
    EXAMS += [(_y, 2, m, f) for m in (3, 6, 9, 11) for f in ("가", "나")]
    EXAMS += [(_y, 3, m, f) for m in (3, 4, 6, 7, 9, 10, 11) for f in ("가", "나")]
FORM_ID = {None: "", "가": "-ga", "나": "-na"}
REDETECT = "--redetect" in sys.argv     # 검출 결과는 data/detect/ 에 저장해 두고 재사용 (검출 코드를 고쳤을 때만 --redetect)

def has_text(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return sum(len(p.chars) for p in pdf.pages[:2]) > 50

def r1(v): return round(float(v), 1)
def box(b):
    d = dict(p=b["page"], x0=r1(b["x0"]), t=r1(b["top"]), x1=r1(b["x1"]), b=r1(b["bottom"]))
    if "num" in b: d["num"] = [r1(b["num"][k]) for k in ("x0", "top", "x1", "bottom")]
    return d

def load_xlsx_class(xlsx):
    ws = openpyxl.load_workbook(xlsx)["문항 분류"]
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        _, label, yr, g, mo, n, sec, subj, unit, code, std, yoji, note = r
        out[(int(yr), int(g), int(str(mo).replace("월", "")), sec or "공통", int(n))] = dict(subject=subj, unit=unit, code=code, standard=std, summary=yoji, note=note or "")
    return out

def load_json_class(year, g, m, codes, sfx=""):
    p = os.path.join(ROOT, f"data/classification/{year}_{g}_{m:02d}{sfx}.json")
    d = json.load(open(p, encoding="utf-8")); out = {}
    for key, v in d.items():
        sec = SEC_KEY[key[0]]; n = int(key[1:])
        c = v["code"]
        if c == "12이수01-01": info = ISU
        else:
            ci = codes[c]; info = dict(subject=ci["subject"], unit=ci["unit"], standard=ci["text"])
        out[(year, g, m, sec, n)] = dict(subject=info["subject"], unit=info["unit"], code=c, standard=info["standard"], summary=v["summary"], note=v.get("note") or "")
    return out

def main():
    codes = json.load(open(os.path.join(ROOT, "data/standards_codes.json"), encoding="utf-8"))
    ans = {}
    for f in sorted(os.listdir(os.path.join(ROOT, "data"))):
        if f.startswith("answers_") and f.endswith(".json"):
            ans.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data", f), encoding="utf-8")).items() if not k.startswith("_")})
    x6 = load_xlsx_class(os.path.join(ROOT, "data/classification_2021_06.xlsx"))
    exams, problems = {}, []
    dup = json.load(open(os.path.join(ROOT, "data/dup2020.json"), encoding="utf-8"))
    dup2 = json.load(open(os.path.join(ROOT, "data/dup2017_19.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "data/dup2017_19.json")) else {}
    for ex in EXAMS:
        year, g, month = ex[:3]; form = ex[3] if len(ex) > 3 else None
        old = (year >= 2021)                      # 2021~: 공통+선택 구조, 2020: 단일 시험지
        eid = f"{year}-{g}-{month:02d}{FORM_ID[form]}"
        nm = f"{year}_{g}학년_{month}월" + (f"({form}형)" if form else "")
        qf = f"pdf/{year}/{nm}_문제.pdf"; af = f"pdf/{year}/{nm}_해설.pdf"
        cp = os.path.join(ROOT, f"data/detect/{eid}.json")
        if os.path.exists(cp) and not REDETECT:
            q, a = json.load(open(cp, encoding="utf-8"))
        else:
            if (year, g, month) == (2020, 3, 11):          # 글자 없는 이미지 PDF
                import detect_img
                q = detect_img.detect(os.path.join(ROOT, qf))
                for it in q["items"]:
                    it["points"] = 2 if it["n"] <= 3 else 3 if it["n"] <= 13 else 4 if it["n"] <= 21 else 3 if it["n"] <= 25 else 4
                    it["type"] = "선택형" if it["n"] <= 21 else "단답형"
            else:
                q = detect_q.detect(os.path.join(ROOT, qf), elective=(g == 3 and old)); detect_q.attach_meta(os.path.join(ROOT, qf), q)
            if has_text(os.path.join(ROOT, af)):
                a = detect_a.detect(os.path.join(ROOT, af), elective=(g == 3 and old))
            else:                                           # 스캔(글자 없는) 해설: OCR 로 번호 줄을 찾는다
                import detect_a_img
                a = detect_a_img.detect(os.path.join(ROOT, af))
            os.makedirs(os.path.dirname(cp), exist_ok=True)
            json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        a["columns"] = [tuple(c) for c in a["columns"]]
        if "--detect-only" in sys.argv: print(eid, "검출", len(q["items"]), len(a["items"])); continue
        if year <= 2020:
            sfx = {None: "", "가": "_ga", "나": "_na"}[form]
            cls = load_json_class(year, g, month, codes, sfx)
        else:
            cls = x6 if (year, month) == (2021, 6) else load_json_class(year, g, month, codes)
        exams[eid] = dict(year=year, grade=g, month=month, form=form, q=dict(file=qf, w=r1(q["width"]), h=r1(q["height"])),
                          a=dict(file=af, w=r1(a["width"]), h=r1(a["height"]), colw=r1(max(c[1] - c[0] for c in a["columns"]))))
        if exams[eid]["a"]["colw"] > 450: exams[eid]["a"]["wide"] = True        # 한 단짜리 해설지 (layout.js 전폭 블록)
        amap = {(i["sec"], i["n"]): i for i in a["items"]}
        e = ans[eid]
        drop, also = set(), {}                                      # 2020 3학년 가/나형 중복 처리 (data/dup2020.json)
        if form and year <= 2020:
            dm = dup[str(month)] if (year == 2020 and g == 3) else dup2.get(f"{year}-{g}-{month}", {"same": {}, "variant": [], "delete": []})
            for nb, na in dm["same"].items():
                drop.add(("나", int(nb))); also[("가", int(na))] = f"나형 {nb}번"
            for v in dm["variant"]:
                drop.add(tuple(v["drop"])); also[tuple(v["keep"])] = f"{v['drop'][0]}형 {v['drop'][1]}번"
            for x in dm["delete"]: drop.add(tuple(x))
        cnt = 0
        for it in q["items"]:
            if (form, it["n"]) in drop: continue                     # 중복(동일·단답형 우선)·삭제 문항: 수록하지 않음
            key = (it["sec"], it["n"]); c = cls[(year, g, month, it["sec"], it["n"])]
            ai = amap.get(key)
            es = (e.get(it["sec"]) or {}) if (g == 3 and old) else e
            answer = es.get(str(it["n"]), "")
            pr = dict(
                id=f"{eid}-{SECID[it['sec']]}{it['n']:02d}", exam=eid, year=year, grade=g, month=month, n=it["n"], sec=it["sec"],
                subject=c["subject"], unit=c["unit"], code=c["code"], standard=c["standard"], summary=c["summary"],
                points=it["points"], type=it["type"], answer=answer,
                q=[box(it)], a=[box(b) for b in ai["boxes"]] if ai else [])
            if form: pr["form"] = form
            if (form, it["n"]) in also: pr["also"] = also[(form, it["n"])]
            problems.append(pr); cnt += 1
        print(eid, cnt, "문제", len(a["items"]), "해설")
    if "--detect-only" in sys.argv: return
    units, seen = [], set()      # 성취기준 파일의 순서대로 (과목, 단원) 목록 -> 화면 정렬용
    for c in codes.values():
        k = (c["subject"], c["unit"])
        if k not in seen: seen.add(k); units.append(list(k))
    units.append([ISU["subject"], ISU["unit"]])
    json.dump(dict(version=2, units=units, exams=exams, problems=problems), open(os.path.join(ROOT, "data/problems.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(problems), "problems")

if __name__ == "__main__":
    main()
