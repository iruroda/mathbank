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

def load_json_class(year, g, m, codes):
    p = os.path.join(ROOT, f"data/classification/{year}_{g}_{m:02d}.json")
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
    for year, g, month in EXAMS:
        eid = f"{year}-{g}-{month:02d}"
        qf = f"pdf/{year}/{year}_{g}학년_{month}월_문제.pdf"; af = f"pdf/{year}/{year}_{g}학년_{month}월_해설.pdf"
        q = detect_q.detect(os.path.join(ROOT, qf), elective=(g == 3)); detect_q.attach_meta(os.path.join(ROOT, qf), q)
        a = detect_a.detect(os.path.join(ROOT, af), elective=(g == 3))
        cls = x6 if month == 6 else load_json_class(year, g, month, codes)
        exams[eid] = dict(year=year, grade=g, month=month, q=dict(file=qf, w=r1(q["width"]), h=r1(q["height"])),
                          a=dict(file=af, w=r1(a["width"]), h=r1(a["height"]), colw=r1(max(c[1] - c[0] for c in a["columns"]))))
        amap = {(i["sec"], i["n"]): i for i in a["items"]}
        e = ans[eid]
        for it in q["items"]:
            key = (it["sec"], it["n"]); c = cls[(year, g, month, it["sec"], it["n"])]
            ai = amap.get(key)
            es = (e.get(it["sec"]) or {}) if g == 3 else e
            answer = es.get(str(it["n"]), "")
            problems.append(dict(
                id=f"{eid}-{SECID[it['sec']]}{it['n']:02d}", exam=eid, year=year, grade=g, month=month, n=it["n"], sec=it["sec"],
                subject=c["subject"], unit=c["unit"], code=c["code"], standard=c["standard"], summary=c["summary"],
                points=it["points"], type=it["type"], answer=answer,
                q=[box(it)], a=[box(b) for b in ai["boxes"]] if ai else []))
        print(eid, len(q["items"]), "문제", len(a["items"]), "해설")
    units, seen = [], set()      # 성취기준 파일의 순서대로 (과목, 단원) 목록 -> 화면 정렬용
    for c in codes.values():
        k = (c["subject"], c["unit"])
        if k not in seen: seen.add(k); units.append(list(k))
    units.append([ISU["subject"], ISU["unit"]])
    json.dump(dict(version=2, units=units, exams=exams, problems=problems), open(os.path.join(ROOT, "data/problems.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(problems), "problems")

if __name__ == "__main__":
    main()
