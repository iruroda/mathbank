"""2006~2009 2학년 문항 상자 보정: 단답형(22~30) 안내 상자·확인사항 상자·1쪽 안내문이 섞인 문항의 위/아래를 잘라 data/detect 캐시에 저장한다."""
import json, os, sys
import numpy as np, pypdfium2 as pdfium
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 2
def region(pdf, it, pad=0):
    im = pdf[it["page"]].render(scale=S).to_pil().convert("L")
    return np.array(im.crop((int(it["x0"]*S), int((it["top"]-pad)*S), int(it["x1"]*S), int(it["bottom"]*S)))) < 150
def runs(row):
    best = cur = 0
    for v in row:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best
def rule_rows(a, frac):
    w = a.shape[1]
    return [y for y in range(a.shape[0]) if runs(a[y]) >= frac*w]
def banner(a):
    """'단답형(22~30)' 안내 상자: 위·아랫선 쌍(좌우 길이 100~170pt, 간격 14~30pt). -> (윗선, 아랫선) 행 또는 None"""
    rows = [y for y in range(a.shape[0]) if 100*S <= runs(a[y]) <= 175*S]
    for y in rows:
        for y2 in rows:
            if 14*S <= y2-y <= 30*S:
                xs1 = np.where(a[y])[0]; xs2 = np.where(a[y2])[0]
                if abs(xs1[0]-xs2[0]) <= 3 and a[y+3:y2-2].any(): return y, y2
    return None
def fix(eid, nm, edits):
    cp = f"{R}/data/detect/{eid}.json"; q, a = json.load(open(cp, encoding="utf-8"))
    y = int(eid[:4]); pdf = pdfium.PdfDocument(f"{R}/pdf/{y}/{nm}_문제.pdf")
    for n, kind in edits:
        it = q["items"][n-1]; assert it["n"] == n
        im = region(pdf, it)
        if kind == "top_rule":        # 안내문 밑줄(가장 아래 긴 줄) 아래부터
            ys = [y for y in rule_rows(im, 0.5) if y < im.shape[0]*0.7]
            if ys: it["top"] = round(it["top"] + ys[-1]/S + 3, 1)
        elif kind == "top_banner":    # 맨 위 안내 상자 아래부터
            b = banner(im)
            if b: it["top"] = round(it["top"] + b[1]/S + 5, 1)
        elif kind == "bot_banner":    # 아래쪽 안내 상자 위까지
            b = banner(im)
            if b: it["bottom"] = round(it["top"] + b[0]/S - 3, 1)
        elif kind == "bot_confirm":   # 확인사항 상자 위까지
            ys = [y for y in rule_rows(im, 0.85) if y > im.shape[0]*0.3]
            if ys: it["bottom"] = round(it["top"] + ys[0]/S - 4, 1)
        elif kind == "trim_bottom":   # 아래쪽에 멀리 떨어진 잔여물 제거 (60pt 이상 빈 줄 뒤)
            ink = im.any(axis=1); last = None; gap = 0
            for yy in range(im.shape[0]):
                if ink[yy]: 
                    if last is not None and yy-last > 60*S: it["bottom"] = round(it["top"] + last/S + 4, 1); break
                    last = yy
        elif kind == "trim_blank":    # 맨 아래 빈 곳 제거
            ink = np.where(im.any(axis=1))[0]
            if len(ink): it["bottom"] = round(it["top"] + ink[-1]/S + 6, 1)
        elif kind.startswith("top-"):  # 위로 N pt 늘림 (글자 윗부분 잘림)
            it["top"] = round(it["top"] - float(kind[4:]), 1)
    json.dump([q, a], open(cp, "w", encoding="utf-8"), ensure_ascii=False)
    return q["items"]
if __name__ == "__main__":
    E = {
     ("2006-2-09-ga", "2006_2학년_9월(가형)"): [(1, "top_rule")],
     ("2008-2-11-ga", "2008_2학년_11월(가형)"): [(1, "top_rule"), (3, "top_rule")],
     ("2008-2-11-na", "2008_2학년_11월(나형)"): [(3, "top_rule")],
     ("2006-2-11-ga", "2006_2학년_11월(가형)"): [(22, "top_banner")],
     ("2006-2-11-na", "2006_2학년_11월(나형)"): [(22, "top_banner")],
     ("2009-2-06-ga", "2009_2학년_6월(가형)"): [(21, "bot_banner")],
     ("2007-2-03", "2007_2학년_3월"): [(21, "bot_banner")],
     ("2009-2-11-ga", "2009_2학년_11월(가형)"): [(30, "bot_confirm"), (1, "top-3"), (1, "trim_bottom"), (2, "top-3")],
     ("2009-2-11-na", "2009_2학년_11월(나형)"): [(30, "bot_confirm"), (1, "top-3")],
    }
    for (e, nm), ed in E.items():
        its = fix(e, nm, ed); print(e, [(n, its[n-1]["top"], its[n-1]["bottom"]) for n, k in ed])
