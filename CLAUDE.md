# ML for Realized Volatility Forecasting — Internship Project

## Purpose
Scratchpad for planning and executing a Goldman Sachs ML internship project (~10-12 weeks, active May 2026) focused on forecasting realized volatility. Not a production codebase.

## Repository Structure
```
ML-GS/
├── CLAUDE.md                    # this file
├── .claude/skills/              # custom skills (write-chapter, research, status)
├── deliverables/                # project deliverables (pitch, plans, scripts)
├── docs/superpowers/            # design specs and implementation plans
├── notes/                       # project notes
│   └── volatility.md            # main research/scoping document (~45 papers)
├── reference/                   # all reference materials
│   ├── books/                   # textbooks (Hull, AFML, Natenberg, etc.)
│   ├── papers/                  # general reference papers + course materials
│   ├── project-papers/          # papers specific to the vol project (32 curated)
│   └── bibliography.md
└── guides/                      # LaTeX learning guides
    ├── ml-finance/              # ML for finance (14 chapters)
    └── quant-trading/           # quant trading (38 chapters)
```

## Project Directions (one to be finalized)
1. **HARQ-X + ML residual** (Safest) — public data, clearest "where ML adds value" story
2. **Intraday RV from LOB** (Medium) — Optiver-style, options MM relevance
3. **Multivariate RC with GNNs** (Medium-Ambitious) — covariance forecasting, portfolio backtest
4. **Rough vol vs deep learning** (Ambitious) — Rosenbaum-Zhang replication + extension
5. **VRP ML trader** (Highest Wow) — variance risk premium signal, end-to-end PnL

## Key Baselines
HAR, HAR-J/CJ, SHAR, HARQ, Realized GARCH, Ridge/Lasso-HAR

## Evaluation
QLIKE (primary), MSE, Diebold-Mariano tests, Model Confidence Set, purged k-fold CV. Target: 30-80 bps QLIKE improvement + economic-value test.

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

## Conventions
- `docs/superpowers/specs/` for design documents
- `docs/superpowers/plans/` for implementation plans
- `notes/` for project notes
- `reference/project-papers/` for ML vol papers, `reference/papers/` for general
- All code follows TDD: failing test → implement → pass → commit
