"""2006학년도 11월 고1 문제지(그림 PDF, 쪽당 2단×위·아래 2칸): 단마다 잉크 덩어리를 찾아 문항 영역으로 쓴다."""
import subprocess, tempfile, os, glob
import numpy as np
from PIL import Image

# 쪽 -> [(왼쪽 단 문항들), (오른쪽 단 문항들)] , None 은 '단답형' 안내 상자
LAYOUT = {0: ([1, 2], [3, 4]), 1: ([5, 6], [7, 8]), 2: ([9], [10]), 3: ([11, 12], [13, 14]),
          4: ([15, 16], [17, 18]), 5: ([19, 20], [21, None, 22]), 6: ([23, 24], [25, 26]), 7: ([27, 28], [29, 30, None])}
COLS = [(29, 290), (306, 572)]

def detect(path, gap=62):
    d = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", "72", "-png", path, d + "/p"], check=True)
    items = []
    for pi, f in enumerate(sorted(glob.glob(d + "/p-*.png"))):
        im = np.array(Image.open(f).convert("L")); H, W = im.shape
        for ci, (x0, x1) in enumerate(COLS):
            seq = LAYOUT[pi][ci]
            lo = 298 if (pi == 0 and ci == 0) else 170 if pi == 0 else 114       # 머리글(제목·안내문·쪽번호) 아래부터
            ink = (im[:, x0:x1] < 200).sum(axis=1) > 0
            ink[:lo] = False; ink[752:] = False
            ys = [y for y in range(H) if ink[y]]                     # 잉크 줄들 사이의 빈 틈 중 가장 큰 (문항 수-1)개에서 자른다
            gaps = sorted(((ys[k + 1] - ys[k], k) for k in range(len(ys) - 1)), reverse=True)[:len(seq) - 1]
            cuts = sorted(k for _, k in gaps); bands, st = [], 0
            for k in cuts: bands.append((ys[st], ys[k])); st = k + 1
            bands.append((ys[st], ys[-1]))
            for n, (a, b) in zip(seq, bands):
                if n is None: continue
                items.append(dict(n=n, sec="공통", page=pi, col=ci, x0=float(x0), x1=float(x1), top=float(a - 3), bottom=float(b + 4)))
    items.sort(key=lambda i: i["n"])
    return dict(width=596.0, height=842.0, items=items)
