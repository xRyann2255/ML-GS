# ML for Realized Volatility Forecasting

Internship project repo: planning, research, and learning guides for a Goldman Sachs ML internship focused on forecasting realized volatility.

## Guides (Compiled PDFs)

| Guide | Pages | Topic |
|-------|-------|-------|
| `vol-learning-guide/main.pdf` | 213 | RV estimation, forecasting, and applications (17 chapters) |
| `guides/ml-finance/main.pdf` | — | ML methods for finance (14 chapters) |
| `guides/quant-trading/main.pdf` | — | Quant trading fundamentals (38 chapters) |

## Repository Structure

```
ML-GS/
├── deliverables/          # pitch decks, project plans, speaker scripts
├── docs/superpowers/      # design specs and implementation plans
├── guides/
│   ├── ml-finance/        # ML for finance LaTeX guide
│   └── quant-trading/     # quant trading LaTeX guide
├── notes/                 # project notes (volatility.md, glossary, faq)
├── reference/             # books, papers, course materials
├── vol-learning-guide/    # volatility forecasting LaTeX guide
└── .claude/skills/        # Claude Code slash commands (see below)
```

## Claude Code Slash Commands

These are custom skills you can invoke in any Claude Code session within this repo.

### `/sync-docs`
Recompile all LaTeX guides and push updated PDFs to the `docs-only` branch (for downloading on restricted machines that flag code files).

**What it does:**
1. Runs pdflatex + bibtex on all three guides
2. Commits updated PDFs to main
3. Syncs compiled PDFs, deliverables, and notes to the `docs-only` branch
4. Pushes both branches

### `/write-chapter`
Write a complete LaTeX chapter using a 4-pass quality pipeline.

**Usage:** Specify a topic, target guide, and optionally source papers.

**Passes:**
1. Writer (main agent) drafts the full chapter
2. Cross-referencer finds and adds citations from reference papers
3. Condenser tightens prose and cuts redundancy
4. Naive reader flags confusing jumps and undefined terms

### `/research`
Parallel 3-agent research pipeline on any topic.

**Usage:** `/research <topic>` (e.g., "research QLIKE loss function properties")

**Agents run in parallel:**
1. Internal search (notes, guides, existing coverage)
2. Paper search (reference PDFs)
3. Web search (recent arXiv, GitHub, blogs)

Then synthesizes into a structured brief with project relevance and next steps.

### `/status`
Show current project status by reading memory files and recent git history.

**Output:** Current phase, recently completed items, next steps, open decisions.

---

## Common Workflows

### Adding content to a guide

```
/write-chapter
> Topic: variance swaps
> Guide: vol-learning-guide
> Source papers: Bennett 2014, CBOE methodology
```

Or for targeted additions to existing chapters, describe what to add and which chapter. Claude will follow the box conventions (prereq, intuition, warning, workedexample, keyidea, application).

### Researching a new topic

```
/research rough volatility vs deep learning approaches
```

Returns a synthesis of what's in your notes, what the reference papers say, and what's new on the web. Decide after whether to save it to `notes/`.

### Preparing guides for download on work laptop

```
/sync-docs
```

Then on your work machine: `git clone -b docs-only --single-branch https://github.com/xRyann2255/ML-GS.git`

### Writing deliverables (pitches, scripts, plans)

Describe what you need. Output goes to `deliverables/`. Previous examples: pitch presentations (HTML), speaker scripts, QA battle cards, project plans.

### Planning a multi-step addition

For larger additions (multiple sections, new chapters), the workflow is:
1. Describe what you want to add
2. Claude brainstorms the design with you (spec)
3. Creates an implementation plan
4. Executes via subagent-driven development (parallel where possible)
5. Compiles and commits after each section

---

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Full repo with all source, references, and compiled PDFs |
| `docs-only` | Lightweight: only compiled PDFs, deliverables, and markdown notes |

---

## Key References

The vol-learning-guide draws on ~45 papers. Core ones:
- HAR model: Corsi (2009)
- Roughness: Gatheral, Jaisson, Rosenbaum (2018)
- VRP: Bollerslev, Tauchen, Zhou (2009)
- Vol targeting: Moreira & Muir (2017)
- TSMOM: Moskowitz, Ooi, Pedersen (2012)
- Local vol: Dupire (1994)
- Microstructure: Glosten & Milgrom (1985), Kyle (1985)

Full bibliography in `vol-learning-guide/references.bib`.
