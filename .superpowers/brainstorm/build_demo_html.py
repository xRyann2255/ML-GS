import fitz, base64, os

PDF = "guides/vol-project-ref/main.pdf"
SCREEN = ".superpowers/brainstorm/2902-1780308503/content"
os.makedirs(SCREEN, exist_ok=True)

doc = fitz.open(PDF)
PAGE = 49 - 1  # pipeline figure page (1-indexed 49)
page = doc[PAGE]

# full page, modest dpi (just to show the diagram is small within the page)
full = page.get_pixmap(dpi=110)
full_b64 = base64.b64encode(full.tobytes("png")).decode()

# cropped figure at high dpi
rects = [d["rect"] for d in page.get_drawings() if d["rect"].width > 1 and d["rect"].height > 1]
bb = rects[0]
for r in rects[1:]:
    bb = bb | r
exp = fitz.Rect(bb.x0-30, bb.y0-30, bb.x1+30, bb.y1+30)
for blk in page.get_text("dict")["blocks"]:
    for ln in blk.get("lines", []):
        for sp in ln.get("spans", []):
            sr = fitz.Rect(sp["bbox"])
            if sr.intersects(exp):
                bb = bb | sr
bb = fitz.Rect(bb.x0-8, bb.y0-8, bb.x1+8, bb.y1+8) & page.rect
crop = page.get_pixmap(dpi=300, clip=bb)
crop_b64 = base64.b64encode(crop.tobytes("png")).decode()

html = f"""<h2>What the skill inspects now vs. what it could inspect</h2>
<p class="subtitle">Same real diagram from your vol-project-ref guide (Fig 17.1). Left = today's behavior. Right = the crop+zoom you expected.</p>

<div class="split">
  <div class="mockup">
    <div class="mockup-header">NOW &mdash; renders the whole page at 250 DPI, reads that</div>
    <div class="mockup-body" style="background:#fff;text-align:center">
      <img src="data:image/png;base64,{full_b64}" style="max-width:100%;border:1px solid #ddd"/>
      <p class="label" style="margin-top:10px">Diagram is ~1/6 of the frame. Box labels render tiny &mdash; overlapping or cramped text is nearly invisible at this scale, so it slips through.</p>
    </div>
  </div>
  <div class="mockup">
    <div class="mockup-header">PROPOSED &mdash; auto-crop to the figure, render at 300 DPI</div>
    <div class="mockup-body" style="background:#fff;text-align:center">
      <img src="data:image/png;base64,{crop_b64}" style="max-width:100%;border:1px solid #ddd"/>
      <p class="label" style="margin-top:10px">Figure fills the frame. Every label is legible; overlaps, clipping, and cramped spacing become obvious to both a human and the inspecting agent.</p>
    </div>
  </div>
</div>

<div class="section">
  <p class="label">Two distinct gaps this reveals</p>
  <div class="pros-cons">
    <div class="pros"><h4>Gap 1 &mdash; Resolution</h4><ul>
      <li>It never crops/zooms &mdash; it reads a full page, so fine text problems are sub-pixel</li>
      <li>Fix: detect the figure bbox, crop, render high-DPI (optionally tile dense diagrams)</li>
      <li>Plus a deterministic pass: PyMuPDF exposes every glyph's bbox, so overlapping/clipped/too-small text can be flagged numerically, not just by eye</li>
    </ul></div>
    <div class="cons"><h4>Gap 2 &mdash; What it judges</h4><ul>
      <li>Checks are mechanical (arrows, routing) &mdash; nothing asks "does this teach the concept?"</li>
      <li>Same agent that drew it also grades it &mdash; confirmation bias</li>
      <li>Fix: an independent reviewer that sees only the image, judging legibility + learning-clarity</li>
    </ul></div>
  </div>
</div>
"""

with open(os.path.join(SCREEN, "before-after.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("wrote before-after.html;", "full", full.width, "x", full.height,
      "crop", crop.width, "x", crop.height)
