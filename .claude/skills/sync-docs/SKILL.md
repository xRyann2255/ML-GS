---
name: sync-docs
description: Compile all LaTeX guides, commit updated PDFs, and sync the docs-only branch for downloading on restricted machines.
---

# Sync Docs-Only Branch

Recompile **only changed** guides and update the `docs-only` branch with the latest compiled PDFs, deliverables, and markdown notes.

## Execution

Use `$ROOT` = the repo root absolute path (e.g. `/c/Users/ryanv/Documents/Projects/ML`).

### Step 1 — Detect which guides need recompilation

Run a single Bash call that checks each guide for source changes (`.tex`, `.bib`, `preamble.tex`) since its PDF was last committed:

```bash
cd $ROOT && for guide in vol-learning-guide guides/ml-finance guides/quant-trading guides/vol-project-ref; do
  changed=$(git diff --name-only HEAD -- "$guide" | grep -E '\.(tex|bib)$' | head -1)
  untracked=$(git ls-files --others --exclude-standard -- "$guide" | grep -E '\.(tex|bib)$' | head -1)
  if [ -n "$changed" ] || [ -n "$untracked" ]; then
    echo "NEEDS_COMPILE: $guide"
  else
    echo "SKIP: $guide (no source changes)"
  fi
done
```

If ALL four say SKIP, jump directly to Step 3 (deliverables/notes may still need syncing).

### Step 2 — Compile ONLY changed guides in PARALLEL

Launch one Bash tool call per guide that needs compilation. Set timeout to 300000ms for each. Pipe each through `| tail -5`.

**vol-learning-guide** (if needed):
```bash
cd $ROOT/vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf 2>/dev/null | grep Pages || grep 'Output written on' main.log | tail -1)"
```

**guides/ml-finance** (if needed — no bibtex, has no references.bib):
```bash
cd $ROOT/guides/ml-finance && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf 2>/dev/null | grep Pages || grep 'Output written on' main.log | tail -1)"
```

**guides/quant-trading** (if needed):
```bash
cd $ROOT/guides/quant-trading && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf 2>/dev/null | grep Pages || grep 'Output written on' main.log | tail -1)"
```

**guides/vol-project-ref** (if needed):
```bash
cd $ROOT/guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && echo "DONE: $(pdfinfo main.pdf 2>/dev/null | grep Pages || grep 'Output written on' main.log | tail -1)"
```

### Step 3 — Commit PDFs to main (if changed)

```bash
cd $ROOT && git add vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf guides/vol-project-ref/main.pdf && git diff --cached --quiet && echo "No PDF changes" || git commit -m "chore: recompile guide PDFs" && git push
```

### Step 4 — Update docs-only branch

First stash any uncommitted work so the branch switch doesn't destroy it, then sync and return to main:

```bash
cd $ROOT && git stash && git checkout docs-only && git checkout main -- vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf guides/vol-project-ref/main.pdf deliverables/ notes/ && git add -A && git diff --cached --quiet && echo "No changes to sync" || (git commit -m "chore: sync compiled PDFs and notes from main" && git push) && git checkout main && git stash pop
```

If the stash pop reports conflicts, resolve them — the stashed changes are the user's working copy and take priority.

### Step 5 — Report

Page counts for each compiled PDF + which guides were skipped + confirmation of branches pushed.

## What stays on `docs-only`

- `vol-learning-guide/main.pdf` (volatility forecasting guide)
- `guides/ml-finance/main.pdf` (ML for finance guide)
- `guides/quant-trading/main.pdf` (quant trading guide)
- `guides/vol-project-ref/main.pdf` (volatility project reference guide)
- `deliverables/` (pitch presentations, project plans, speaker scripts)
- `notes/` (volatility.md, glossary, faq, secdb requirements)

## Critical rules

- ALWAYS check for source changes BEFORE compiling — never recompile unchanged guides.
- ALWAYS use absolute paths with `cd $ROOT/...` — never rely on working directory state.
- ALWAYS run compilations as parallel Bash tool calls in one message (only for guides that need it).
- ALWAYS chain the full compile pipeline (pdflatex + bibtex + pdflatex + pdflatex) in a SINGLE Bash command per guide.
- Use `| tail -5` on compile commands to avoid flooding context.
- Use timeout 300000ms for compile commands (quant-trading is 570+ pages).
- NEVER use `git checkout -f` — it destroys uncommitted changes. Use `git stash` / `git stash pop` to preserve working tree state across branch switches.
