"""전 시험 문제 영역 검출 + 단원 분류 + 정답을 합쳐 data/problems.json 을 만든다.
   사용: python3 tools/build_all.py
   분류 입력: 2021년 6월은 data/classification_2021_06.xlsx, 나머지는 data/classification/<연도>_<학년>_<월2자리>.json"""
import json, os, sys
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
import detect_q, detect_a

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECID = {"공통": "C", "확률과 통계": "P", "미적분": "K", "기하": "G", "미분과 적분": "D", "이산수학": "S"}
SEC_KEY = {"C": "공통", "P": "확률과 통계", "K": "미적분", "G": "기하", "D": "미분과 적분", "S": "이산수학"}
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
# 2010~2013 1학년 (단일 시험지)
for _y in (2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013):
    EXAMS += [(_y, 1, m) for m in (3, 6, 9, 11)]
# 2014~2016 (2009 개정): 1학년 단일, 2학년은 2014 A형/B형, 2015~2016 가형/나형
for _y in (2014, 2015, 2016):
    EXAMS += [(_y, 1, m) for m in (3, 6, 9, 11)]
    EXAMS += [(_y, 2, m, f) for m in (3, 6, 9, 11) for f in (("A", "B") if _y == 2014 else ("가", "나"))]
    EXAMS += [(_y, 3, m, f) for m in (3, 4, 6, 7, 9, 10, 11) for f in (("A", "B") if _y <= 2015 else ("가", "나"))]
# 2017~2019 (2009 개정): 2·3학년이 가형/나형 별도 시험지. 1학년은 단일. 중복 문항은 data/dup2017_19.json
for _y in (2017, 2018, 2019):
    EXAMS += [(_y, 1, m) for m in (3, 6, 9, 11)]
    EXAMS += [(_y, 2, m, f) for m in (3, 6, 9, 11) for f in ("가", "나")]
    EXAMS += [(_y, 3, m, f) for m in (3, 4, 6, 7, 9, 10, 11) for f in ("가", "나")]
for _y in (2010, 2011, 2012, 2013):                 # 2010~2013 2·3학년 (2학년 3월 공통: 2010~2012)
    _f2 = ("가", "나") if _y <= 2011 else ("A", "B")
    EXAMS += ([(_y, 2, 3)] if _y <= 2012 else []) + [(_y, 2, m, f) for m in ((6, 9, 11) if _y <= 2012 else (3, 6, 9, 11)) for f in _f2]
    EXAMS += [(_y, 3, m, f) for m in (3, 4, 6, 7, 9, 10, 11) for f in (("가", "나") if _y <= 2012 else ("A", "B"))]
for _y in (2006, 2007, 2008, 2009):                 # 2006~2009 2학년: 3월 공통, 6·9·11월 가형/나형
    EXAMS += [(_y, 2, 3)] + [(_y, 2, m, f) for m in (6, 9, 11) for f in ("가", "나")]
# 2006~2009 3학년: 가형/나형 별도 시험지 (2006년은 7월 없음)
for _y in (2006, 2007, 2008, 2009):
    EXAMS += [(_y, 3, m, f) for m in ((3, 4, 6, 9, 10, 11) if _y == 2006 else (3, 4, 6, 7, 9, 10, 11)) for f in ("가", "나")]
FORM_ID = {None: "", "가": "-ga", "나": "-na", "A": "-A", "B": "-B"}
STEMS = json.load(open(os.path.join(ROOT, 'data/stems.json'))) if os.path.exists(os.path.join(ROOT, 'data/stems.json')) else {}
COMBINED = {(2006, 3, 3), (2006, 3, 4), (2006, 3, 10), (2006, 2, 9), (2006, 2, 11), (2007, 3, 3), (2007, 3, 4), (2007, 3, 6), (2007, 3, 10), (2008, 3, 3), (2008, 3, 4), (2008, 3, 7), (2008, 3, 10), (2009, 3, 3), (2009, 3, 4), (2009, 3, 7), (2009, 3, 10), (2007, 2, 9), (2007, 2, 11), (2008, 2, 6), (2008, 2, 9), (2008, 2, 11), (2009, 2, 6), (2009, 2, 9), (2009, 2, 11), (2010, 3, 3), (2010, 3, 4), (2011, 3, 3), (2011, 3, 4), (2012, 3, 3), (2012, 3, 4)}     # 가형+나형 해설이 한 파일
IMGQ = {(2006, 3, 4), (2006, 3, 6), (2006, 3, 10), (2006, 3, 11), (2007, 3, 7), (2006, 2, 9), (2006, 2, 11), (2007, 2, 6), (2007, 2, 9), (2007, 2, 11), (2008, 2, 3), (2008, 2, 6), (2008, 2, 11), (2006, 1, 9), (2006, 1, 11), (2007, 1, 3), (2007, 1, 6), (2007, 1, 9), (2007, 1, 11), (2008, 1, 3), (2008, 1, 6), (2008, 1, 9), (2007, 3, 6), (2007, 3, 9), (2007, 3, 10), (2007, 3, 11), (2008, 3, 3), (2008, 3, 6), (2008, 3, 7), (2008, 3, 9), (2008, 3, 10), (2008, 3, 11), (2009, 3, 6), (2009, 3, 9)}
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
        out[(int(yr), int(g), int(str(mo).replace("월", "")), sec or "공통", int(n))] = dict(subject=(subj or '').replace('이산수학', '이산 수학'), unit=unit, code=code, standard=std, summary=yoji, note=note or "")
    return out

def load_json_class(year, g, m, codes, sfx=""):
    p = os.path.join(ROOT, f"data/classification/{year}_{g}_{m:02d}{sfx}.json")
    d = json.load(open(p, encoding="utf-8")); out = {}
    for key, v in d.items():
        sec = SEC_KEY[key[0]]; n = int(key[1:])
        c = v["code"]
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
    if os.path.exists(os.path.join(ROOT, "data/dup2010_13.json")): dup2.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data/dup2010_13.json"), encoding="utf-8")).items() if not k.startswith("_")})
    if os.path.exists(os.path.join(ROOT, "data/dup2006_09.json")): dup2.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data/dup2006_09.json"), encoding="utf-8")).items() if not k.startswith("_")})
    if os.path.exists(os.path.join(ROOT, "data/dup2007_09_g3.json")): dup2.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data/dup2007_09_g3.json"), encoding="utf-8")).items() if not k.startswith("_")})
    if os.path.exists(os.path.join(ROOT, "data/dup2006_g3.json")): dup2.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data/dup2006_g3.json"), encoding="utf-8")).items() if not k.startswith("_")})
    if os.path.exists(os.path.join(ROOT, "data/dup2014_16.json")): dup2.update({k: v for k, v in json.load(open(os.path.join(ROOT, "data/dup2014_16.json"), encoding="utf-8")).items() if not k.startswith("_")})
    _only = [x.split('=')[1] for x in sys.argv if x.startswith('--only=')]
    for ex in EXAMS:
        year, g, month = ex[:3]; form = ex[3] if len(ex) > 3 else None
        old = (year >= 2021)                      # 2021~: 공통+선택 구조, 2020: 단일 시험지
        eid = f"{year}-{g}-{month:02d}{FORM_ID[form]}"
        if _only and not any(eid.startswith(o) for o in _only): continue
        nm = f"{year}_{g}학년_{month}월" + (f"({form}형)" if form else "")
        qf = f"pdf/{year}/{nm}_문제.pdf"; af = f"pdf/{year}/{nm}_해설.pdf"
        cp = os.path.join(ROOT, f"data/detect/{eid}.json")
        if os.path.exists(cp) and not REDETECT:
            q, a = json.load(open(cp, encoding="utf-8"))
        else:
            el = (g == 3 and old) or ((g == 3 and 2006 <= year <= 2010 and form == '가' and month != 3) and 'old7')
            IMG1 = ((2020, 3, 11), (2011, 1, 6), (2011, 1, 9))
            q = None
            if (year, g, month) in IMGQ:                                                   # 그림으로 된 2단×2칸 문제지(2006~2008): 전용 검출기. 배점은 문항 그림을 보고 따로 적어 넣는다
                import detect_qimg
                detect_qimg.P0LO.update({f"2009_3학년_{_m}월({_f}형)_문제.pdf": 0.2 for _m in (6, 9) for _f in ("가", "나")})
                q = (detect_qimg.detect_old7 if el == 'old7' else detect_qimg.detect_auto)(os.path.join(ROOT, qf), {(2007, 2, 11, '가'): {3: 30}}.get((year, g, month, form), 48))
                for it in q["items"]: it["points"] = None
            if q is None and (year, g, month) not in IMG1 and not (year, g, month) in ((2011, 2, 6), (2010, 2, 9)):
                q = detect_q.detect(os.path.join(ROOT, qf), elective=el, dedupe=(year <= 2009))
                if q["items"]: detect_q.attach_meta(os.path.join(ROOT, qf), q)
                else: q = None
            if q is None:                                                                  # 글자 없는(그림으로 된) 문제지: 화면 구조로 검출
                import detect_img
                q = detect_img.detect(os.path.join(ROOT, qf), {(2011, 1, 6): {0: 288, 1: 177}, (2011, 1, 9): {0: 290, 1: 183}, (2011, 2, 6): {0: 300, 1: 170}, (2010, 2, 9): {0: 300, 1: 185}}.get((year, g, month)), old7=(el == 'old7'), drop={(2013, 3, 9, 'A'): {(4, 0, 0)}, (2013, 3, 9, 'B'): {(4, 0, 0)}}.get((year, g, month, form), ()))
                if g >= 2 and year <= 2013:                  # 2·3학년 이미지 시험지: 배점 '[N점]' 을 템플릿 매칭으로 읽는다
                    import tag_match
                    tg = tag_match.read2(os.path.join(ROOT, qf), q["items"])
                    for k, it in enumerate(q["items"]):
                        v = tg[k]; it["points"] = v[0] if (v[0] and v[2] >= 0.1) else None
                    print(eid, "배점", "".join(str(it["points"] or "?") for it in q["items"]), "합", sum(it["points"] or 0 for it in q["items"]), flush=True)
                for it in q["items"]:
                    if g == 1: it["points"] = 2 if it["n"] <= 3 else 3 if it["n"] <= 13 else 4 if it["n"] <= 21 else 3 if it["n"] <= 25 else 4
                    it["type"] = "선택형" if it["n"] <= 21 else "단답형"
            if year <= 2013:                               # 선택형 1~21, 단답형 22~30 (임시값; 정답이 있으면 아래에서 정답 모양으로 다시 정한다)
                for it in q["items"]: it["type"] = "선택형" if it["n"] <= 21 else "단답형"
            a = None
            if has_text(os.path.join(ROOT, af)):
                a = detect_a.detect(os.path.join(ROOT, af), cols={(2008, 1, 11): [(83, 420), (420, 762)], **{(_y9, 3, _m9, '가'): [(40, 210), (210, 440), (440, 632), (632, 802)] for _y9, _m9 in ((2008, 9), (2008, 11), (2009, 6), (2009, 9))}}.get((year, g, month) if g != 3 else (year, g, month, form)), elective=el, group=(1 if (form in ('나', 'B') and (year, g, month) in COMBINED) else 0), two=((year, g, month) in COMBINED))
            want = 40 if el == "old7" else 30
            if a is None or len(a["items"]) < want - 3:       # 스캔·그림 글자 해설: OCR 로 번호 줄을 찾는다
                import detect_a_img
                for nh in (False, True):
                    a2 = detect_a_img.detect(os.path.join(ROOT, af), expect=want, no_header=nh, old7=(el == 'old7'))
                    if a is None or len(a2["items"]) > len(a["items"]): a = a2
                    if len(a["items"]) >= want: break
            os.makedirs(os.path.dirname(cp), exist_ok=True)
            json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        a["columns"] = [tuple(c) for c in a["columns"]]
        if "--detect-only" in sys.argv: print(eid, "검출", len(q["items"]), len(a["items"])); continue
        if year <= 2020:
            sfx = {None: "", "가": "_ga", "나": "_na", "A": "_A", "B": "_B"}[form]
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
                f1, f2 = ("A", "B") if form in ("A", "B") else ("가", "나")
                drop.add((f2, int(nb))); also[(f1, int(na))] = f"{f2}형 {nb}번"
            for v in dm["variant"]:
                drop.add(tuple(v["drop"])); also[tuple(v["keep"])] = f"{v['drop'][0]}형 {v['drop'][1]}번"
            for x in dm["delete"]: drop.add(tuple(x))
        cnt = 0
        for it in q["items"]:
            if (form, it["n"]) in drop: continue                     # 중복(동일·단답형 우선)·삭제 문항: 수록하지 않음
            key = (it["sec"], it["n"]); c = cls[(year, g, month, it["sec"], it["n"])]
            ai = amap.get(key)
            es = (e.get(it["sec"]) or {}) if ((g == 3 and old) or "공통" in e) else e
            answer = es.get(str(it["n"]), "")
            if year <= 2013 and answer: it["type"] = "선택형" if answer in "①②③④⑤" else "단답형"
            pr = dict(
                id=f"{eid}-{SECID[it['sec']]}{it['n']:02d}", exam=eid, year=year, grade=g, month=month, n=it["n"], sec=it["sec"],
                subject=c["subject"], unit=c["unit"], code=c["code"], standard=c["standard"], summary=c["summary"],
                points=it["points"], type=it["type"], answer=answer,
                q=[box(it)], a=[box(b) for b in ai["boxes"]] if ai else [])
            for st in STEMS.get(eid, []):      # [N~M] 공통 지문(그림)은 문항 앞에 덧붙임
                if it["n"] in st["n"]: pr["q"].insert(0, box(dict(page=st["p"], x0=st["x0"], top=st["t"], x1=st["x1"], bottom=st["b"]))); pr["stem"] = True
            if form: pr["form"] = form
            if (form, it["n"]) in also: pr["also"] = also[(form, it["n"])]
            problems.append(pr); cnt += 1
        print(eid, cnt, "문제", len(a["items"]), "해설")
    if "--detect-only" in sys.argv: return
    units, seen = [], set()      # 성취기준 파일의 순서대로 (과목, 단원) 목록 -> 화면 정렬용
    used = {(p["subject"], p["unit"]) for p in problems}
    for c in codes.values():
        k = (c["subject"], c["unit"])
        # 이산 수학·고급 과목은 해당 문항이 나온 단원만 화면에 올린다 (아직 안 나온 단원은 제외)
        if (k[0] == "이산 수학" or k[0].startswith("고급")) and k not in used: continue
        if k not in seen: seen.add(k); units.append(list(k))
    json.dump(dict(version=2, units=units, exams=exams, problems=problems), open(os.path.join(ROOT, "data/problems.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(problems), "problems")

if __name__ == "__main__":
    main()
