# ML for Realized Volatility Forecasting -- Internship Project

## Session Workflow (READ THIS FIRST)

**Research-first, not plan-first.** Do not jump to implementation plans, sprints, or task lists. The project's value comes from deep understanding of features and data, not from shipping code fast.

### Every session should:

1. **Read `notes/research-journal.md`** to pick up where the last session left off
2. **Read `notes/open-questions.md`** to see what's queued for exploration
3. **Ask the user** what they want to explore today -- one topic, in depth
4. **Go deep** -- compute things on real data, look at distributions, test assumptions, run baselines. Do not skim.
5. **At session end**, append findings to `notes/research-journal.md` and update the relevant `notes/features/*.md` file with what was learned. Move answered questions out of `open-questions.md`.

### Do NOT:
- Create implementation plans, sprint structures, or task breakdowns unless the user explicitly asks
- Jump from "I read a paper that says X" to "let's build X" -- first verify X on our data
- Propose model architectures before the user understands the features that would feed them
- Rush to write code when the user is still exploring and learning

### The implementation plan emerges from research, not the other way around.

---

## Purpose
Research scratchpad for a Goldman Sachs ML internship project (~20 weeks, active May-Sep 2026) focused on forecasting realized volatility. Currently in the exploration and feature understanding phase.

## Repository Structure
```
ML/
├── CLAUDE.md                    # this file
├── .claude/skills/              # custom skills (write-chapter, research, status, etc.)
├── logs/progress.md             # daily progress log
├── deliverables/                # project deliverables (pitch, plans, scripts)
├── docs/                        # project plans, guide specs, and design docs
│   ├── project-plans/           # internship project directions
│   ├── vol-learning-guide/      # learning guide specs and plans
│   └── claude-code-optimization/# tooling and harness config
├── notes/                       # research notes and findings
│   ├── volatility.md            # literature survey (~45 papers)
│   ├── research-journal.md      # session-by-session findings (append-only)
│   ├── open-questions.md        # running list of things to investigate
│   ├── data-access.md           # GS data inventory
│   ├── features/                # per-feature-family exploration notes
│   │   ├── har-components.md
│   │   ├── jump-detection.md
│   │   ├── leverage-effect.md
│   │   ├── microstructure.md
│   │   ├── cross-asset.md
│   │   └── implied-vol.md
│   ├── glossary.md
│   └── faq.md
├── reference/                   # all reference materials
│   ├── books/                   # textbooks (Hull, AFML, Natenberg, etc.)
│   ├── papers/                  # general reference papers + course materials
│   ├── project-papers/          # papers specific to the vol project (32 curated)
│   └── bibliography.md
└── guides/                      # LaTeX learning guides
    ├── ml-finance/              # ML for finance (14 chapters)
    └── quant-trading/           # quant trading (38 chapters)
```

## Current Phase: Exploration & Feature Understanding

The project direction is ML forecasting for realized volatility. Before locking in a specific approach, methodology, or architecture, we are exploring the data and understanding what features capture and why.

**Key baselines to understand first:** HAR, HAR-J/CJ, SHAR, HARQ, Realized GARCH, Ridge/Lasso-HAR

**Evaluation (when we get there):** QLIKE (primary), MSE, Diebold-Mariano tests, Model Confidence Set, purged k-fold CV. Target: 30-80 bps QLIKE improvement + economic-value test.

---

## Writing Learning Guides

New guides go in `guides/<guide-name>/`. Follow existing conventions from `guides/quant-trading/` and `guides/ml-finance/`.

### Setup
- **Class**: `memoir` `[11pt, openany, a4paper, oneside]` or `report` `[11pt, a4paper]`
- **Preamble**: Shared file (`preamble.tex`) loaded via `\input{}`. No packages in chapter files
- **Structure**: `main.tex` → `\input{chapters/chXX_name.tex}`, grouped into `\part{}`
- **Citations**: `natbib` `[round, authoryear]`, `references.bib` at guide root

### Required Box Types (tcolorbox)
| Box | Colour | Purpose |
|---|---|---|
| `intuition` | Green | Plain-English explanations, analogies |
| `keyidea` | Blue/Orange | Important concepts, algorithms |
| `warning` | Red | Common mistakes, methodological errors |
| `workedexample` | Teal | Step-by-step numerical walk-throughs |
| `projectconnection` | Teal | Ties content to the GS project |
| `prereq` | Purple | Background knowledge and prerequisites |

### Style Rules
- Open with a concrete question, not an abstract definition
- Every chapter starts with a prereq box
- Worked examples mandatory for hard concepts (setup → computation → table → intuition)
- `booktabs` tables only. No vertical rules
- Cite papers from `reference/` liberally (`\citep{}` parenthetical, `\citet{}` textual)
- Teach from first principles — define every term on first use (bold it)

---

## Preparing `docs-only` Branch for Download

The `docs-only` branch contains only compiled PDFs, deliverables, and markdown notes (no source code, no reference materials). Use it to download on restricted machines that flag code files.

**To update it from main:**

1. Compile all guides that have changed:
   ```bash
   cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && cd ..
   cd guides/ml-finance && pdflatex -interaction=nonstopmode main.tex && cd ../..
   cd guides/quant-trading && pdflatex -interaction=nonstopmode main.tex && cd ../..
   cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && cd ../..
   ```
2. Commit any updated PDFs to main.
3. Switch to docs-only and reset it from main, keeping only the target files:
   ```bash
   git checkout docs-only
   git checkout main -- vol-learning-guide/main.pdf guides/ml-finance/main.pdf guides/quant-trading/main.pdf guides/vol-project-ref/main.pdf guides/vol-project-ref/markdown/ deliverables/ notes/
   git commit -m "chore: sync compiled PDFs, markdown, and notes from main"
   git push
   git checkout main
   ```

**What stays on `docs-only`:**
- `vol-learning-guide/main.pdf`, `guides/ml-finance/main.pdf`, `guides/quant-trading/main.pdf`, `guides/vol-project-ref/main.pdf`
- `guides/vol-project-ref/markdown/` (markdown conversion with Mermaid diagrams, for LLM consumption)
- `deliverables/` (all .md and .html)
- `notes/` (all .md)

---

## Conventions
- `docs/project-plans/` for internship project plans (grouped by direction)
- `docs/vol-learning-guide/` for learning guide specs and plans
- `docs/claude-code-optimization/` for tooling docs
- `notes/` for project notes
- `reference/project-papers/` for ML vol papers, `reference/papers/` for general
- All code follows TDD: failing test → implement → pass → commit
