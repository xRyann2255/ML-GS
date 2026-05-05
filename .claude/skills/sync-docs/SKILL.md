---
name: sync-docs
description: Compile all LaTeX guides, commit updated PDFs, and sync the docs-only branch for downloading on restricted machines.
---

# Sync Docs-Only Branch

Recompile all guides and update the `docs-only` branch with the latest compiled PDFs, deliverables, and markdown notes.

## Execution

1. **Compile all guides** (from repo root `vol-learning-guide/`, `guides/ml-finance/`, `guides/quant-trading/`):
   - For each guide directory that has a `main.tex`:
     - Run `pdflatex -interaction=nonstopmode main.tex`
     - Run `bibtex main` (if references.bib exists)
     - Run `pdflatex -interaction=nonstopmode main.tex` (twice more to resolve refs)
   - Report page counts for each PDF.

2. **Commit updated PDFs to main** (if any changed):
   ```bash
   git add vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf
   git commit -m "chore: recompile guide PDFs"
   git push
   ```
   Skip this step if no PDFs changed.

3. **Update docs-only branch**:
   ```bash
   git checkout docs-only
   git checkout main -- vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf deliverables/ notes/
   git commit -m "chore: sync compiled PDFs and notes from main"
   git push
   git checkout main
   ```

4. **Report** the final state: page counts, file list on docs-only, confirmation it pushed.

## What stays on `docs-only`

- `vol-learning-guide/main.pdf` (volatility forecasting guide)
- `guides/ml-finance/main.pdf` (ML for finance guide)
- `guides/quant-trading/main.pdf` (quant trading guide)
- `deliverables/` (pitch presentations, project plans, speaker scripts)
- `notes/` (volatility.md, glossary, faq, secdb requirements)

## Important

- Always compile from main before switching branches.
- If `git checkout docs-only` fails due to untracked files, use `git checkout -f docs-only`.
- After finishing, always return to main.
