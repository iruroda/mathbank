"""그림으로만 된 2단(위·아래 2칸) 문제지(2006~2008): 단마다 잉크 덩어리를 문항 영역으로 본다.
   읽는 순서는 쪽 → 왼쪽 단 위에서 아래 → 오른쪽 단 위에서 아래. 문항이 아닌 덩어리(머리글·안내문·'단답형' 안내 상자·확인사항)는 drop 에서 (쪽,단,덩어리순서)로 지정."""
import subprocess, tempfile, glob
import numpy as np
from PIL import Image

def bands(path, gap=48):
    gapd = gap if isinstance(gap, dict) else {}; gap0 = 48 if isinstance(gap, dict) else gap
    """(쪽, 단, x0, x1, [(위,아래)...]) 목록"""
    d = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", "72", "-png", path, d + "/p"], check=True)
    res = []
    for pi, f in enumerate(sorted(glob.glob(d + "/p-*.png"))):
        im = np.array(Image.open(f).convert("L")); H, W = im.shape
        mid = W // 2
        # 가운데 세로선 위치 찾기: 거의 전 높이에 걸친 어두운 열
        dark = (im < 160).sum(axis=0)
        cand = [x for x in range(mid - 40, mid + 40) if dark[x] > H * 0.5]
        div = int(np.mean(cand)) if cand else mid
        cols = [(int(W * 0.04), div - 6), (div + 6, int(W * 0.96))]
        for ci, (x0, x1) in enumerate(cols):
            ink = (im[:, x0:x1] < 200).sum(axis=1) > 0
            ink[:int(H * 0.07)] = False; ink[int(H * 0.905):] = False       # 머리글·쪽번호
            if pi > 0:                                                       # 머리글 밑줄(양쪽 단에 걸친 긴 선) 아래부터
                full = [y for y in range(int(H * 0.06), int(H * 0.24)) if (im[y, int(W * 0.05):int(W * 0.95)] < 170).mean() > 0.8]
                if full: ink[:full[-1] + 3] = False
                else: ink[:int(H * 0.15)] = False
            if pi == 0:                                                      # 1쪽: 머리글(제목·성명) 아래부터, 왼쪽 단은 안내문 밑줄 아래부터
                lo = int(H * 0.2)
                if ci == 0:
                    rule = [y for y in range(int(H * 0.2), int(H * 0.5)) if (im[y, x0:x1] < 170).mean() > 0.85]
                    lo = (rule[-1] + 3) if rule else int(H * 0.36)
                ink[:lo] = False
            ys = np.where(ink)[0]; out = []
            if len(ys):
                s = ys[0]; last = ys[0]
                for y in ys[1:]:
                    if y - last > gapd.get(pi, gap0): out.append((int(s), int(last))); s = y
                    last = y
                out.append((int(s), int(last)))
            res.append((pi, ci, x0, x1, out))
    return res, W, H

def _page(path, pi):
    d = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", "72", "-f", str(pi + 1), "-l", str(pi + 1), "-png", path, d + "/p"], check=True)
    return np.array(Image.open(sorted(glob.glob(d + "/p-*.png"))[0]).convert("L"))

def _run(row):
    best = cur = 0
    for v in row < 150:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best

def detect(path, drop=(), gap=48):
    res, W, H = bands(path, gap)
    items, n = [], 0
    ims = {}
    for pi, ci, x0, x1, bs in res:
        for k, (a, b) in enumerate(bs):
            if (pi, ci, k) in drop: continue
            n += 1
            if n == 22:                                                      # '단답형(22~30)' 안내 상자가 22번 덩어리 맨 위에 붙어 있으면 상자 아래부터
                if pi not in ims: ims[pi] = np.array(Image.open(sorted(glob.glob(path + "_tmp/p-*.png"))[pi]).convert("L")) if False else _page(path, pi)
                im = ims[pi]; rows = [y for y in range(a, min(a + 75, b)) if _run(im[y, x0:x1]) >= 45]
                if len(rows) >= 2 and rows[0] - a < 6:                        # 상자의 윗선·아랫선: 아랫선(윗선에서 8~45pt 아래) 뒤부터
                    lows = [y for y in rows if 8 <= y - rows[0] <= 45]
                    if lows: a = max(lows) + 6
            items.append(dict(n=n, sec="공통", page=pi, col=ci, x0=float(x0), x1=float(x1), top=float(a - 3), bottom=float(b + 4)))
    return dict(width=float(W), height=float(H), items=items)

if __name__ == "__main__":
    import sys
    r, W, H = bands(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 48)
    print(W, H)
    for pi, ci, x0, x1, bs in r: print(pi, ci, x0, x1, [(a, b, b - a) for a, b in bs])


def detect_auto(path, gap=48):
    """마지막 쪽 오른쪽 단 맨 아래 덩어리(확인사항 상자)를 빼고 검출한다."""
    r, W, H = bands(path, gap)
    return detect(path, drop={(r[-1][0], r[-1][1], len(r[-1][4]) - 1)}, gap=gap)
