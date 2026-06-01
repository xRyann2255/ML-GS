# .claude/skills/verify-diagram/contact_sheet.py
"""Assemble a grid PNG ("contact sheet") from per-diagram crop PNGs."""
import math, argparse, os

def grid_dims(n):
    if n <= 0:
        return (0, 0)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return (cols, rows)

def cell_origin(index, cols, cw, ch, gap):
    row, col = divmod(index, cols)
    return (gap + col * (cw + gap), gap + row * (ch + gap))

def build(crop_paths, out_path, cell=420, gap=14):
    import fitz
    paths = [p for p in crop_paths if p and os.path.exists(p)]
    if not paths:
        return None
    cols, rows = grid_dims(len(paths))
    W = gap + cols * (cell + gap)
    H = gap + rows * (cell + gap)
    sheet = fitz.open()
    page = sheet.new_page(width=W, height=H)
    for i, p in enumerate(paths):
        x, y = cell_origin(i, cols, cell, cell, gap)
        img = fitz.open(p)
        r = img[0].rect
        scale = min(cell / r.width, cell / r.height)
        w, h = r.width * scale, r.height * scale
        page.insert_image(fitz.Rect(x, y, x + w, y + h), filename=p)
        img.close()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    page.get_pixmap(dpi=150).save(out_path)
    sheet.close()
    return out_path

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--crops", nargs="*", default=[])
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    res = build(a.crops, a.out)
    print(res or "no crops")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
