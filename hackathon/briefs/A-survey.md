# Owner A — Survey, Map, and the checkpoint keys

## Paste this into Claude Code

```
I own stage 1 (SURVEY) and stage 2 (MAP) of Trailhead, a hackathon project in this repo.

Read in this order:
  CLAUDE.md
  hackathon/briefs/A-survey.md          <- my brief, follow it
  hackathon/docs/pipeline-contracts.md  <- trailhead/survey@1 and trailhead/map@1
  hackathon/src/trailhead/survey.py     <- what already exists
  hackathon/tests/test_survey.py        <- the existing tests are the contract

Survey is deterministic and pure, so it is test-driven: write the test first,
watch it fail, then implement. I own src/trailhead/survey.py, map.py,
checkpoints.py and tests/ for those three. I touch nothing else.

Target: `python -m trailhead.survey <repo>` emits a survey.json that satisfies
trailhead/survey@1, on any Python repo, with git churn and entry points.

Start by telling me what's already implemented and what the first missing piece
is. Don't write code until we agree the order.
```

## Mission

Everything Trailhead can know about a repo **without a model**. You are the
factual floor the other four stand on: B narrates from your survey, C validates
against it, D renders your graph, and every checkpoint answer key in the artifact
is computed by you.

## You own

```
src/trailhead/survey.py       stage 1 — tree, imports, entry points, churn
src/trailhead/map.py          stage 2 — module rollup + graph layout
src/trailhead/checkpoints.py  answer keys from survey.json
tests/test_survey.py          exists, 8 tests passing
tests/test_map.py             new
tests/test_checkpoints.py     new
```

**Never touch:** `fixtures/*` (shared — ask first), `demo/`, `tools/`, anything
outside `hackathon/`.

## What already exists

`survey.py` has two functions with 8 passing tests:

- `parse_imports(source, module)` — dotted names, relative imports resolved
- `resolve_import(dotted, known)` — longest known prefix, `None` if third-party

```bash
cd hackathon && PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
# Ran 8 tests — OK
```

Read those tests before writing anything. They encode two decisions worth
keeping: a `from pkg import thing` emits `pkg.thing` because one file cannot tell
a submodule from a symbol, and resolution walks prefixes longest-first.

## Output

`trailhead/survey@1` and `trailhead/map@1`, both defined in
`docs/pipeline-contracts.md`. Reference: `fixtures/survey.sample.json`.

## Build order

1. **File walk + module index.** Every `.py` file → `{path, module, loc}`.
   Repo-relative, forward slashes, on Windows too. Skip `.git`, `node_modules`,
   `.venv`, `__pycache__`, anything gitignored.
2. **Edges.** Feed each file through the two functions you already have, resolve
   to module level, count import statements per module pair. External imports
   are not edges.
3. **Git churn.** `git log --numstat --format=%H|%an|%aI` parsed once into
   commits-per-file, last-commit date, author list. One subprocess call for the
   whole repo, not one per file — on a 4000-file repo that difference is minutes.
4. **Entry points.** Five kinds, in descending reliability:
   `console_script` (pyproject `[project.scripts]`), `module_main`
   (`__main__.py`), `main_guard` (`if __name__ == "__main__"`),
   `http_route` (FastAPI/Flask decorators via `ast`), `dockerfile_cmd`.
5. **Command candidates.** Scan `Makefile`, `pyproject.toml`, `tox.ini`,
   `.github/workflows/*.yml`, `README.md` fenced blocks. Emit with `source` as
   `file:line` and a `confidence`. **You do not run them** — that is C's runner.
6. **Map.** Collapse to top-level packages, lay out `x`/`y`/`w` at generation
   time (no layout engine in the page). More than 40 modules → collapse to
   top-level packages, per spec §4.4.
7. **Checkpoints.** Derive from what you already computed. Four kinds that work:
   most-imported-and-imports-nothing → "which directory owns X"; registry symbol
   with many references → "which file do you edit first"; static call order from
   an entry point → an `order` checkpoint; exception raised in module P but
   constructed only in module Q → "where do you look first". Each needs
   `provenance` naming the survey field it came from, and `explanation`.

## Done when

```bash
cd hackathon
PYTHONPATH=src py -3.11 -m unittest discover -s tests -v   # all green
PYTHONPATH=src py -3.11 -m trailhead.survey . > /tmp/survey.json
node tools/check-fixtures.js                                # still exit 0
```

and `survey.json` for a repo nobody has read has: every edge naming a known
module, at least one entry point, at least three command candidates, and three
checkpoints whose answers you can defend out loud from the provenance string.

## Traps

- **Windows paths.** `pathlib` gives you backslashes; the contract says forward
  slashes. Normalise once, at the boundary, or D's excerpts won't key correctly.
- **`ast.parse` raises** on Python 2 files, syntax errors, and files with odd
  encodings. Catch per file, record it, keep walking. One bad file must not kill
  a survey — you will meet this on the unfamiliar repo at hour 8.
- **Non-negotiable #6 is yours.** The moment a checkpoint answer comes from a
  model, the audit panel is theatre. If you cannot derive a key statically, cut
  the checkpoint.
- **`provenance` is displayed on screen.** Write it for a reader, not a log.
