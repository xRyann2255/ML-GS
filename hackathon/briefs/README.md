# Briefs — one per person, start now

Five owners, five briefs. Each is self-contained: paste the block at the top of
your brief into your own Claude Code session and go. Nobody waits on anybody.

| | Owner | Brief | Ships |
|---|---|---|---|
| A | | [A-survey.md](A-survey.md) | Stage 1 + 2 + checkpoint keys → `survey.json`, `map.json` |
| B | | [B-narrate.md](B-narrate.md) | Stage 3 → `content.json` |
| C | | [C-verify.md](C-verify.md) | Stage 4 + command runner → `verified.json`, `commands.json` |
| D | | [D-render.md](D-render.md) | The HTML artifact — the thing on the projector |
| E | | [E-integration.md](E-integration.md) | CLI, hygiene, demo repos, the pitch |

Write the names in that table before anyone starts.

## Why you are not blocked

Every seam is frozen and every seam has a fixture. You build against the
fixture, not against the person upstream.

```
survey.sample.json ─┐
content.sample.json ─┼─▶ VERIFY ─▶ verified.sample.json ─▶ RENDER ─▶ trailhead.html
commands.sample.json ┘
```

All four fixtures describe the same synthetic repo, `payments-core @ a3f9c21`.
Field-by-field definitions: `docs/verified-contract.md` (generator↔render) and
`docs/pipeline-contracts.md` (the three seams inside the generator).

## Rules of engagement

1. **One person per file.** The ownership tables in the briefs are not advisory.
   If you need a change in someone else's file, ask them — don't edit it.
2. **Fixtures are shared state.** Changing one breaks three people. Say so out
   loud before you do, and re-run `node tools/check-fixtures.js`.
3. **Contracts extend, never break.** Add a key; never rename, remove, or retype
   one. A real breaking change means bumping to `@2` and telling the room.
4. **Three gates, all must exit 0** before anyone says a thing works:
   ```bash
   node tools/check-bundle.js      # self-containment + spec §1
   node tools/verify-contract.js   # anchors, sha256, contract
   node tools/check-fixtures.js    # the fixture chain agrees with itself
   ```
   Quote the output. Reading the code is not evidence.
5. **Don't touch anything outside `hackathon/`.** The rest of this repo is the
   summer vol-forecasting project and is off limits this week.

## The four non-negotiables you can personally break

Each of you owns one. Breaking it turns Trailhead into a generic codebase
explainer with no pitch.

| Owner | Yours |
|---|---|
| A | **#6** — checkpoint answer keys come from static analysis, never a model |
| B | **#7** — never ask the model for line numbers, ask it to quote |
| C | **#4** — command output is real, always; and **#3** — dropped claims are counted |
| D | **#5** — one HTML file, zero external requests; and the drop count stays on screen |
| E | **#1** — only stage 3 touches a model |

## Checkpoints — 15 minutes, everyone stops

| When | What must be true |
|---|---|
| Hour 3 | A's real `survey.json` replaces the fixture · B has one successful model call · D has projector mode |
| Hour 5 | First end-to-end run on a real repo, however ugly |
| Hour 7 | Run on unfamiliar repo #1 |
| Hour 8 | Freeze. Only fixes for what unfamiliar repo #2 breaks. No new features. |

**Pivot rule:** if the core loop is still unreliable at hour 4, E hard-codes the
demo path rather than chasing generality.

**Cut list, in order:** stop 12 → stop 15 → stop 10 → checkpoint B → stop 7.

**Never cut:** claim markers, the audit panel, the dropped-claim count.
