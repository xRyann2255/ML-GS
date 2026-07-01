---
description: "Search the Slang script database for function usages, definitions, call sites, Link statements, or patterns"
model: Claude Opus 4.6
---

Search the Slang script database using the SLANG_GLIMPSE skill for: ${input}

**Python path:** Resolve using the PYTHON_PATH skill (`skills/PYTHON_PATH/SKILL.md`). Use the resolved path as `PYTHON` below.

Run the glimpse tool:

```powershell
PYTHON skills/SLANG_GLIMPSE/src/glimpse.py --index slangprod --query "${input}"
```

## Options to consider based on the query

- To find **callers/references**: add `--field references`
- To find **definitions**: add `--field defines`
- To search **comments/authors**: add `--field comments`
- To find **scripts by name**: add `--field name --files-only`
- To find **Link statements**: add `--field links --files-only`
- To **list script names only**: add `--files-only`
- To **skip comment lines**: add `--no-comments`
- To **limit results**: add `--max-results 20`

## Index selection

- `slangprod` — Production scripts (default)
- `slangdev` — Development scripts
- `slanguser` — User home directory scripts
- `slangarch` — Archived scripts

Analyze the query intent and choose the appropriate flags. Show the results clearly, grouping by script name when relevant.
