---
name: SEARCH
description: Fast skill and memory search with cached inverted index
---

# SEARCH — Fast Skill & Memory Search

> **Purpose:** Search skills and memory files using a cached inverted index. Returns ranked results with priority-weighted scoring in under 15ms (warm) or 100ms (cold).

**Out of scope:** Full-text content retrieval (use `read_file`), Slang codebase search (use SLANG_GLIMPSE), GitLab code search (use GITLAB_SEARCH).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SEARCH` |
| **Scope** | Search skill and memory files by keyword with priority-weighted ranking |
| **Inputs** | Query string, optional `--top N`, `--json`, `--rebuild` |
| **Outputs** | Ranked list of matching skill/memory file paths with scores |
| **Authority** | Read-only utility, no side effects |

## When to Use

- Before starting any task, find relevant skills and memory files to load.
- When you need to discover which skill handles a domain (e.g. "trade booking").
- When looking up memory files by topic instead of scanning INDEX.md manually.
- As a fast alternative to grep when you need ranked, priority-aware results.

## How It Works

1. **Inverted index** built from all `skills/*/SKILL.md` and `memory/**/*.md` files.
2. **Structured field extraction** — name, tags, description, headings, triggers, body text.
3. **Priority-weighted scoring** — Skills rank highest (5x), then P0 (4x) > P1 (3x) > P2 (2x) > P3 (1x). Field weights: name (10x) > tags/triggers (8x) > description (6x) > headings (4x) > body (1x).
4. **Bigram support** — multi-word concepts like "trade lifecycle" match tightly.
5. **Prefix matching** — partial terms match with 0.5x weight.
6. **Disk cache** — pickled index at `workspace/tmp/.search_index.pkl`, invalidated by file mtime/size hash.

## Usage

### Task-Based Execution (preferred)

Write args JSON to `workspace/tmp/search_args.json`, then run the `search` task:

```json
{ "query": "trade booking lifecycle", "top": 10, "json": true, "out_file": "h:\\ml-vol-estimator\\workspace\\tmp\\search_out.txt" }
```

Args JSON fields:
- `query` — search query string (required unless `rebuild` is true)
- `top` — max results (optional, default 10)
- `json` — output as JSON (optional, default false)
- `rebuild` — force index rebuild (optional, default false)
- `out_file` — path to write output (optional, prints to console if omitted)

Pattern: `create_file` (write search_args.json) → `run_task("search")` → `read_file` (read search_out.txt)

### Direct CLI (fallback)

```bash
H:\venv311\Scripts\python.exe skills/SEARCH/src/search.py "trade booking lifecycle"
H:\venv311\Scripts\python.exe skills/SEARCH/src/search.py "atlas clearing" --top 20
H:\venv311\Scripts\python.exe skills/SEARCH/src/search.py "query" --json
H:\venv311\Scripts\python.exe skills/SEARCH/src/search.py --rebuild
```

### Output (table)

```
  (10 results, 8.2ms, index cached)

    #   Score  Pri    Path                                          Match
  ───  ──────  ────── ─────────────────────────────────────────────  ────────────────────
    1    42.0  SKILL  skills/ETI_TRADE/SKILL.md                     trade, booking
    2    31.0  P1     memory/ref/secdb-trade-model.md               trade, booking
    3    28.0  P2     memory/sys/gs-trade-flows.md                  trade, lifecycle
```

### Output (JSON)

```json
{
  "elapsed_ms": 8.2,
  "rebuilt": false,
  "results": [
    {"rank": 1, "score": 42.0, "priority": "SKILL", "path": "skills/ETI_TRADE/SKILL.md", "matched": ["trade", "booking"], "description": "..."}
  ]
}
```

## Performance

| Operation | Target |
|-----------|--------|
| Cold build (first run) | <100ms |
| Warm query (cached) | <15ms |
| Index size | ~334 documents |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Stale results after adding files | Run with `--rebuild` to force reindex |
| No results | Check query spelling; try shorter/broader terms |
| Slow cold start | Normal on first run; subsequent runs use cache |

## Links

- `skills/INDEX.md` — skill registry
- `memory/INDEX.md` — memory file index (search target)
