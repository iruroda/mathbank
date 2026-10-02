"""문제 영역 검출 결과 + 단원 분류(xlsx) + 정답을 합쳐 data/problems.json 을 만든다."""
import json, os, sys, glob, re
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
import detect_q, detect_a

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECID = {"공통": "C", "확률과 통계": "P", "미적분": "K", "기하": "G"}
def r1(v): return round(float(v), 1)
def box(b, with_page=True):
    d = dict(p=b["page"], x0=r1(b["x0"]), t=r1(b["top"]), x1=r1(b["x1"]), b=r1(b["bottom"]))
    if "num" in b: d["num"] = [r1(b["num"][k]) for k in ("x0", "top", "x1", "bottom")]
    return d

def load_class(xlsx):
    ws = openpyxl.load_workbook(xlsx)["문항 분류"]
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        _, label, yr, g, mo, n, sec, subj, unit, code, std, yoji, note = r
        out[(int(yr), int(g), int(str(mo).replace("월", "")), sec or "공통", int(n))] = dict(subject=subj, unit=unit, code=code, standard=std, summary=yoji, note=note or "")
    return out

def main(year, month, xlsx, answers):
    cls = load_class(xlsx); ans = json.load(open(answers, encoding="utf-8"))
    exams, problems = {}, []
    for g in (1, 2, 3):
        eid = f"{year}-{g}-{month:02d}"
        qf = f"pdf/{year}/{year}_{g}학년_{month}월_문제.pdf"; af = f"pdf/{year}/{year}_{g}학년_{month}월_해설.pdf"
        q = detect_q.detect(os.path.join(ROOT, qf), elective=(g == 3)); detect_q.attach_meta(os.path.join(ROOT, qf), q)
        a = detect_a.detect(os.path.join(ROOT, af), elective=(g == 3))
        exams[eid] = dict(year=year, grade=g, month=month, q=dict(file=qf, w=r1(q["width"]), h=r1(q["height"])), a=dict(file=af, w=r1(a["width"]), h=r1(a["height"]), colw=r1(max(c[1]-c[0] for c in a["columns"]))))
        amap = {(i["sec"], i["n"]): i for i in a["items"]}
        for it in q["items"]:
            key = (it["sec"], it["n"]); c = cls[(year, g, month, it["sec"], it["n"])]
            ai = amap[key]
            e = ans[eid]; answer = (e[it["sec"]] if g == 3 else e)[str(it["n"])]
            qb = box(it)
            problems.append(dict(
                id=f"{eid}-{SECID[it['sec']]}{it['n']:02d}", exam=eid, year=year, grade=g, month=month, n=it["n"], sec=it["sec"],
                subject=c["subject"], unit=c["unit"], code=c["code"], standard=c["standard"], summary=c["summary"],
                points=it["points"], type=it["type"], answer=answer,
                q=[qb], a=[box(b) for b in ai["boxes"]]))
    json.dump(dict(version=1, exams=exams, problems=problems), open(os.path.join(ROOT, "data/problems.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(problems), "problems")

if __name__ == "__main__":
    main(2021, 6, os.path.join(ROOT, "data/classification_2021_06.xlsx"), os.path.join(ROOT, "data/answers_2021_06.json"))
