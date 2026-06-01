import fitz, base64, os, json

PDF = "guides/vol-project-ref/main.pdf"
OUT = ".superpowers/brainstorm/demo_assets"
os.makedirs(OUT, exist_ok=True)

targets = {
    "ensemble": "Three ensemble architectures",
    "pipeline": "Pipeline architecture with plug points",
}

doc = fitz.open(PDF)

def find_page(term):
    for i, page in enumerate(doc):
        if term in page.get_text():
            return i
    return None

def figure_bbox(page):
    # union of vector drawing rects = the TikZ diagram extent
    rects = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > 1 and r.height > 1:
            rects.append(r)
    if not rects:
        return None
    bb = rects[0]
    for r in rects[1:]:
        bb = bb | r
    # include text spans intersecting the (slightly expanded) drawing region
    exp = fitz.Rect(bb.x0-30, bb.y0-30, bb.x1+30, bb.y1+30)
    td = page.get_text("dict")
    for blk in td.get("blocks", []):
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                sr = fitz.Rect(sp["bbox"])
                if sr.intersects(exp):
                    bb = bb | sr
    # pad
    bb = fitz.Rect(bb.x0-8, bb.y0-8, bb.x1+8, bb.y1+8)
    return bb & page.rect

results = {}
for name, term in targets.items():
    pi = find_page(term)
    if pi is None:
        print(f"{name}: NOT FOUND")
        continue
    page = doc[pi]
    # current approach: full page at 250 dpi
    full = page.get_pixmap(dpi=250)
    full_path = f"{OUT}/full_{name}.png"
    full.save(full_path)
    # proposed: crop to figure bbox at 300 dpi
    bb = figure_bbox(page)
    crop_path = f"{OUT}/crop_{name}.png"
    if bb:
        crop = page.get_pixmap(dpi=300, clip=bb)
        crop.save(crop_path)
    print(f"{name}: page {pi+1}, full={full.width}x{full.height}, "
          f"crop_bbox={[round(v,1) for v in bb] if bb else None}, "
          f"crop={crop.width}x{crop.height if bb else 0}")
    results[name] = {"page": pi+1, "full": full_path, "crop": crop_path,
                     "full_dims": [full.width, full.height],
                     "crop_dims": [crop.width, crop.height] if bb else None}

with open(f"{OUT}/manifest.json", "w") as f:
    json.dump(results, f, indent=2)
print("DONE")
