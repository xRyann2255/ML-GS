---
name: sync-docs
description: Compile all LaTeX guides, commit updated PDFs, and sync the docs-only branch for downloading on restricted machines.
---

# Sync Docs-Only Branch

Recompile all guides and update the `docs-only` branch with the latest compiled PDFs, deliverables, and markdown notes.

## Execution

Use `$ROOT` = the repo root absolute path (e.g. `/c/Users/ryanv/Documents/Projects/ML`).

### Step 1 — Compile all three guides in PARALLEL

Launch three Bash tool calls in a single message (one per guide). Each is a self-contained pipeline using absolute paths. Set timeout to 300000ms for each.

**vol-learning-guide:**
```bash
cd $ROOT/vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf | grep Pages)"
```

**guides/ml-finance** (no bibtex — has no references.bib):
```bash
cd $ROOT/guides/ml-finance && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf | grep Pages)"
```

**guides/quant-trading:**
```bash
cd $ROOT/guides/quant-trading && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf | grep Pages)"
```

Pipe each through `| tail -5` to keep output short. If `pdfinfo` is not available, grep "Output written on" from the pdflatex output for page counts.

### Step 2 — Commit PDFs to main (if changed)

```bash
cd $ROOT && git add vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf && git diff --cached --quiet && echo "No changes" || git commit -m "chore: recompile guide PDFs" && git push
```

### Step 3 — Update docs-only branch

Run as a single chained command:
```bash
cd $ROOT && git checkout -f docs-only && git checkout main -- vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf deliverables/ notes/ && git commit -m "chore: sync compiled PDFs and notes from main" && git push && git checkout main
```

Use `-f` on the checkout to avoid stale aux file conflicts.

### Step 4 — Report

Page counts for each PDF + confirmation both branches pushed.

## What stays on `docs-only`

- `vol-learning-guide/main.pdf` (volatility forecasting guide)
- `guides/ml-finance/main.pdf` (ML for finance guide)
- `guides/quant-trading/main.pdf` (quant trading guide)
- `deliverables/` (pitch presentations, project plans, speaker scripts)
- `notes/` (volatility.md, glossary, faq, secdb requirements)

## Critical rules

- ALWAYS use absolute paths with `cd $ROOT/...` — never rely on working directory state.
- ALWAYS run the three compilations as parallel Bash tool calls in one message.
- ALWAYS chain the full compile pipeline (pdflatex + bibtex + pdflatex + pdflatex) in a SINGLE Bash command per guide.
- Use `| tail -5` on compile commands to avoid flooding context.
- Use timeout 300000ms for compile commands (quant-trading is 570+ pages).
- Use `git checkout -f docs-only` to handle leftover aux files.
