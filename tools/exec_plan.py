"""(검증용) layout.js 가 만든 plan 을 실제 PDF 로 조립한다. 웹앱의 pdf-lib 동작과 같은 좌표 규칙을 쓴다."""
import json, sys, io, os, pikepdf
from pikepdf import Name, Pdf, Stream, Array
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
pdfmetrics.registerFont(TTFont("KR", FONT, subfontIndex=0))
pdfmetrics.registerFont(TTFont("KRB", FONT, subfontIndex=0))
plan = json.load(open(sys.argv[1])); out = sys.argv[2]
PW, PH = 595.276, 841.89
srcs = {}
def src(f):
    if f not in srcs: srcs[f] = pikepdf.open(os.path.join(ROOT, f))
    return srcs[f]

dst = Pdf.new()
for _ in plan["pages"]: dst.add_blank_page(page_size=(PW, PH))
xo_n = 0
formcache = {}
for pi, pg in enumerate(plan["pages"]):
    cmds = []; xobjs = {}
    for op in pg["ops"]:
        if op["t"] != "crop": continue
        key = (op["file"], op["page"])
        if key not in formcache:
            sp = src(op["file"]).pages[op["page"]]
            copied = dst.copy_foreign(sp.obj)
            formcache[key] = pikepdf.Page(copied).as_form_xobject()
        form = formcache[key]
        x0, t, x1, b = op["src"]; H = op["ph"]
        nf = Stream(dst, form.read_bytes())
        nf.Type = Name.XObject; nf.Subtype = Name.Form
        nf.BBox = Array([x0, H - b, x1, H - t])
        nf.Resources = form.Resources
        xo_n += 1; name = f"/Fm{xo_n}"; xobjs[name] = nf
        dx, dy, dw, dh = op["dest"]; s = dw / (x1 - x0)
        tx = dx - x0 * s; ty = (PH - dy - dh) - (H - b) * s
        cmds.append(f"q {s:.5f} 0 0 {s:.5f} {tx:.3f} {ty:.3f} cm {name} Do Q")
    page = dst.pages[pi]
    page.Contents = dst.make_stream("\n".join(cmds).encode())
    page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary({k: v for k, v in xobjs.items()}))
    # 오버레이(선·글자·가림 사각형)
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(PW, PH))
    for op in pg["ops"]:
        t = op["t"]
        if t == "line":
            c.setLineWidth(op["w"]); c.line(op["x1"], PH - op["y1"], op["x2"], PH - op["y2"])
        elif t == "rect":
            if op.get("fill"):
                c.setFillColorRGB(1, 1, 1); c.rect(op["x"], PH - op["y"] - op["h"], op["w"], op["h"], stroke=0, fill=1); c.setFillColorRGB(0, 0, 0)
            if op.get("stroke"):
                c.setLineWidth(op.get("sw", 0.6)); c.rect(op["x"], PH - op["y"] - op["h"], op["w"], op["h"], stroke=1, fill=0)
        elif t == "text":
            c.setFont("KRB" if op["bold"] else "KR", op["size"])
            y = PH - op["y"]
            if op["align"] == "center": c.drawCentredString(op["x"], y, op["s"])
            elif op["align"] == "right": c.drawRightString(op["x"], y, op["s"])
            else: c.drawString(op["x"], y, op["s"])
    c.save(); buf.seek(0)
    ov = Pdf.open(buf)
    page.add_overlay(pikepdf.Page(ov.pages[0]))
dst.save(out)
print("saved", out, os.path.getsize(out)//1024, "KB,", len(plan["pages"]), "pages")
