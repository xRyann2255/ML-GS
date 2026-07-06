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
cd $ROOT && for guide in guides/vol-learning-guide guides/quant-trading guides/vol-project-ref; do
  changed=$(git diff --name-only HEAD -- "$guide" | grep -E '\.(tex|bib)$' | head -1)
  untracked=$(git ls-files --others --exclude-standard -- "$guide" | grep -E '\.(tex|bib)$' | head -1)
  if [ -n "$changed" ] || [ -n "$untracked" ]; then
    echo "NEEDS_COMPILE: $guide"
  else
    echo "SKIP: $guide (no source changes)"
  fi
done
```

If ALL three say SKIP, jump directly to Step 3 (deliverables/notes may still need syncing).

### Step 2 — Compile ONLY changed guides in PARALLEL, to the pagination fixpoint

Launch one Bash tool call per guide that needs compilation (substitute `<guide>`). Set timeout to 600000ms for each. Do NOT use a fixed pass count: a shifted page break can leave the TOC one page stale after three passes (this happened on 2026-07-06 — 369pp vol-learning-guide, TOC off by one from mid-ch1). Loop until `.toc`/`.aux`/`.ind` stop changing:

```bash
cd $ROOT/guides/<guide> && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1; bibtex main >/dev/null 2>&1
converged=0
for i in 1 2 3 4 5; do
  before=$(md5sum main.toc main.aux main.ind 2>/dev/null)
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  [ "$before" = "$(md5sum main.toc main.aux main.ind 2>/dev/null)" ] && converged=$i && break
done
[ $converged -gt 0 ] && echo "CONVERGED after $converged post-bibtex pass(es)" || echo "WARNING: pagination did NOT converge in 5 passes — investigate before committing"
echo "DONE: $(grep 'Output written on' main.log | tail -1)"
```

If the block prints the non-convergence WARNING, do not commit that PDF — investigate (usually an oscillating float or longtable).

### Step 3 — Commit PDFs to main (if changed)

```bash
cd $ROOT && git add guides/vol-learning-guide/main.pdf guides/quant-trading/main.pdf guides/vol-project-ref/main.pdf && git diff --cached --quiet && echo "No PDF changes" || git commit -m "chore: recompile guide PDFs" && git push
```

### Step 4 — Update docs-only branch

First stash any uncommitted work so the branch switch doesn't destroy it, then sync and return to main:

```bash
cd $ROOT && git stash && git checkout docs-only && git checkout main -- guides/vol-learning-guide/main.pdf guides/vol-learning-guide/markdown/ guides/quant-trading/main.pdf guides/vol-project-ref/main.pdf guides/vol-project-ref/markdown/ deliverables/ notes/ && find guides deliverables notes -name '*.py' -exec sh -c 'mv -f "$1" "$1.txt"' _ {} \; && git add -A -- guides deliverables notes && git diff --cached --quiet && echo "No changes to sync" || (git commit -m "chore: sync compiled PDFs, markdown, and notes from main" && git push) && git checkout main && git stash pop
```

The `find ... mv` step renames any `.py` pulled over from main to `.py.txt` — docs-only must never contain Python files (restricted machines flag them). A pre-commit hook (`.githooks/pre-commit` on main, installed at `.git/hooks/pre-commit`) enforces this as a backstop on every docs-only commit.

If the stash pop reports conflicts, resolve them — the stashed changes are the user's working copy and take priority.

### Step 5 — Report

Page counts for each compiled PDF + which guides were skipped + confirmation of branches pushed.

## What stays on `docs-only`

- `guides/vol-learning-guide/main.pdf` (volatility forecasting guide)
- `guides/quant-trading/main.pdf` (quant trading guide)
- `guides/vol-project-ref/main.pdf` (volatility project reference guide)
- `guides/vol-learning-guide/markdown/` (markdown conversion of learning guide, with Mermaid diagrams)
- `guides/vol-project-ref/markdown/` (markdown conversion of vol-project-ref, with Mermaid diagrams)
- `deliverables/` (pitch presentations, project plans, speaker scripts)
- `notes/` (volatility.md, glossary, faq, secdb requirements)

## Critical rules

- ALWAYS check for source changes BEFORE compiling — never recompile unchanged guides.
- ALWAYS use absolute paths with `cd $ROOT/...` — never rely on working directory state.
- ALWAYS run compilations as parallel Bash tool calls in one message (only for guides that need it).
- ALWAYS compile to the pagination fixpoint (the Step 2 convergence loop), never a fixed pass count — the final pass must leave `.toc`/`.aux`/`.ind` unchanged.
- Compile output is already quiet (pdflatex redirected to /dev/null); the CONVERGED/DONE echoes are the report.
- Use timeout 600000ms for compile commands (quant-trading is 570+ pages and may need extra passes).
- NEVER use `git checkout -f` — it destroys uncommitted changes. Use `git stash` / `git stash pop` to preserve working tree state across branch switches.
- NEVER commit a `.py` file to docs-only — rename to `.py.txt`. The pre-commit hook does this automatically; keep it installed (`cp .githooks/pre-commit .git/hooks/pre-commit`).
