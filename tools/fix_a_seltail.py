"""2021~ 3학년 EBSi 해설을 '확통 전체 + 미적분의 3쪽부터 + 기하의 3쪽부터' 로 합친 파일에서,
   다음 선택과목 첫 쪽 맨 위에 중복으로 들어 있는 공통 풀이 꼬리(앞 선택과목 30번 구간으로 잘못 붙음)를 잘라낸다.
   규칙: 선택과목 30번 해설 조각 중, 다음 선택과목 23번이 시작되는 쪽 이후의 조각은 뺀다.
   사용: python3 tools/fix_a_seltail.py 2026-3-10 ...   (data/detect/<eid>.json 의 a 를 고침; 그 다음 fix_abottom.py 로 빈 단 정리)"""
import json, sys, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECS = ["확률과 통계", "미적분", "기하"]
def fix(eid):
    cp = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(cp, encoding="utf-8"))
    by = {(i["sec"], i["n"]): i for i in a["items"]}; ch = 0
    for s, nxt in zip(SECS, SECS[1:]):
        if (s, 30) not in by or (nxt, 23) not in by: continue
        np_ = min(b["page"] for b in by[(nxt, 23)]["boxes"])
        it = by[(s, 30)]; keep = [b for b in it["boxes"] if b["page"] < np_]
        if len(keep) != len(it["boxes"]): print(eid, s, "30번 해설 조각", len(it["boxes"]) - len(keep), "개 제거 (쪽 >=", np_, ")"); ch += 1
        it["boxes"] = keep
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False); print(eid, "보정", ch)
if __name__ == "__main__":
    for e in sys.argv[1:]: fix(e)
