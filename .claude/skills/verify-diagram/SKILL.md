---
name: verify-diagram
description: Visually verify TikZ diagrams by compiling the LaTeX, rendering the page to a PNG, and inspecting it for layout issues. Use after creating or modifying any TikZ diagram.
---

# Verify Diagram

Compile a LaTeX document containing a TikZ diagram, render the relevant page to an image, and visually inspect it for layout problems. Fix any issues found and re-verify until clean.

## When to Use

- After creating or modifying any TikZ diagram in a LaTeX guide
- When a user reports visual issues with a diagram
- Called automatically by the `write-chapter` skill after any diagram is written

## Procedure

### Step 1: Compile

Compile the guide containing the diagram. Run `pdflatex` (and `bibtex` if needed) from the guide root:

```bash
cd guides/<guide-name>
pdflatex -interaction=nonstopmode main.tex
```

If references are unresolved, run `bibtex main` then `pdflatex` twice more.

### Step 2: Find the Page

Use PyMuPDF to find which page contains the diagram. Search for a unique string from the figure caption or nearby text:

```python
import fitz
doc = fitz.open('main.pdf')
for i, page in enumerate(doc):
    text = page.get_text()
    if '<search term>' in text:
        print(f'Page {i+1}')
```

### Step 3: Render to PNG

Render the page at high DPI (220-300) using PyMuPDF:

```python
pix = doc[page_index].get_pixmap(dpi=250)
pix.save('verify_diagram.png')
```

Use `PYTHONIOENCODING=utf-8` as an env var prefix when running `py` on Windows to avoid encoding errors.

### Step 4: Visual Inspection

Read the PNG using the `Read` tool (which renders images visually). Check for:

1. **Arrows going through boxes**: any arrow line that passes through a node boundary
2. **Overlapping arrows**: two arrow paths that run on top of each other or are indistinguishable
3. **Arrows entering wrong nodes**: an arrow that appears to connect to the wrong node
4. **Overlapping or clipped nodes**: boxes that overlap each other or extend beyond the figure boundary
5. **Unreadable labels**: text too small, truncated, or overlapping other elements
6. **Broken routing**: right-angle paths that create unnecessary crossings when a cleaner route exists
7. **Dependency accuracy**: arrows match the stated dependencies (from table, caption, or spec)
8. **Visual balance**: diagram isn't lopsided, excessive whitespace, or oddly proportioned

### Step 5: Fix and Re-verify

If any issues are found:

1. Edit the TikZ code to fix the problem
2. Go back to Step 1 and repeat
3. Continue until the diagram passes all checks

### Step 6: Clean Up

Delete all temporary PNG files created during verification:

```bash
rm -f guides/<guide-name>/verify_diagram.png
```

## Common TikZ Fixes

### Arrows going through nodes

Use explicit routing with intermediate coordinates:
```latex
% Instead of direct paths that cross nodes:
\draw[arrow] (a) -- (c);  % BAD: goes through node b

% Route around with right-angle paths:
\draw[arrow] (a.south) -- ++(0,-0.5) -| (c.north);  % GOOD: drops below then routes
```

### Fan-out from one node to many

Use a bus pattern instead of multiple overlapping paths from the same anchor:
```latex
\draw (source.south) -- ++(0,-1) coordinate (branch);
\fill (branch) circle (2pt);
\draw (branch) -- (branch -| last_target.north);
\draw[arrow] (branch -| target1.north) -- (target1.north);
\draw[arrow] (branch -| target2.north) -- (target2.north);
```

### Arrows that must skip over intermediate nodes

Route above or below the obstructing node:
```latex
% Route above: use north anchors + vertical offset
\draw[arrow] (a.north east) -- ++(0,0.5) -| (c.north west);

% Route below: use south anchors + vertical offset
\draw[arrow] (a.south) -- ++(0,-0.5) -| (c.south);
```

### Separating arrows that share an axis

Use offset anchors (north east, south west, etc.) or `xshift`/`yshift` to keep lines visually distinct:
```latex
\draw[arrow] (a.north east) -- (b.south east);  % right side
\draw[arrow] (a.north) -- (b.south);             % center (separate path)
```

## Dependencies

- Requires `py` (Python) with `PyMuPDF` (`pip install PyMuPDF`)
- Requires `pdflatex` (MiKTeX or TeX Live)
- Uses the `Read` tool's image rendering capability for visual inspection
