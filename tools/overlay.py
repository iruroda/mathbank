import sys, json, pypdfium2 as pdfium
from PIL import ImageDraw
pdf_path, js, page, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
r = json.load(open(js)); S = 0.7
pdf = pdfium.PdfDocument(pdf_path)
img = pdf[page].render(scale=S).to_pil().convert("RGB")
d = ImageDraw.Draw(img)
for it in r["items"]:
    boxes = it.get("boxes") or [it]
    for b in boxes:
        if b.get("page", it.get("page")) != page: continue
        d.rectangle([b["x0"]*S, b["top"]*S, b["x1"]*S, b["bottom"]*S], outline=(255,0,0), width=2)
        d.text((b["x0"]*S+4, b["top"]*S+2), str(it["n"]), fill=(255,0,0))
img.save(out)
