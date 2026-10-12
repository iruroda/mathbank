"""글자 없는(이미지) 문제지에서 문항별 배점 '[N점]' 을 OCR 로 읽는다. -> {n: 2|3|4|None}"""
import re, subprocess, tempfile, os
import pypdfium2 as pdfium

def read_points(path, items, scale=4.0):
    pdf = pdfium.PdfDocument(path); res = {}; cache = {}
    for it in items:
        pi = it["page"]
        if pi not in cache: cache[pi] = pdf[pi].render(scale=scale).to_pil().convert("L")
        im = cache[pi]
        crop = im.crop((int(it["x0"]*scale), int(it["top"]*scale), int(it["x1"]*scale), int(min(it["bottom"], it["top"]+220)*scale)))
        m = None
        for sc, psm in ((1.0, "6"), (0.6, "6"), (1.0, "4"), (0.5, "6"), (1.5, "6"), (0.7, "11")):
            c2 = crop if sc == 1.0 else crop.resize((int(crop.width*sc), int(crop.height*sc)))
            with tempfile.TemporaryDirectory() as d:
                fp = os.path.join(d, "c.png"); c2.save(fp)
                out = subprocess.run(["tesseract", fp, "-", "--psm", psm, "-l", "eng"], capture_output=True, text=True).stdout
            ms = re.findall(r"[\[\(\{]\s*([234])\s*\S{0,2}\s*[\]\)\}]", out)
            if ms: m = ms[-1]; break
        res[it["n"]] = int(m) if m else None
        continue
        ms = re.findall(r"[\[\(\{]\s*([234])\s*\S{0,2}\s*[\]\)\}]", out); m = ms[-1] if ms else None
        res[it["n"]] = int(m) if m else None
    return res
