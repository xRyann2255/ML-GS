# `tests/repos/` — the genericity fixtures

Four tiny repos (plan §11.1, decision 23), 3–11 files each. They are **inputs**, not tests.
The harness that runs them lives elsewhere; plan §11.3 is the loop:

```bash
cd hackathon
for R in tests/repos/hazards tests/repos/flat_script \
         tests/repos/nested_root tests/repos/no_entry; do
  PYTHONPATH=src py -3.11 -m trailhead build "$R" -o "out/$(basename $R).html" \
      --provider stub --run-commands none --gate || echo "FAIL $R"
done
```

Each repo exists to force **one** path that `restored/` — the demo repo — cannot force.
`restored/` is LF-only, BOM-free, syntax-error-free, has no long lines and no git history.
It is the *unrepresentative* repo on this machine (§11.1). Nothing here duplicates it.

## What each repo proves

| Repo | Files | Forces | Plan | §9 rows |
|---|---|---|---|---|
| `flat_script/` | 4 | Root-cascade **terminal fallback** — no `__init__.py`, no pyproject, bare-stem module names. **Zero internal edges** → `C=1` in the layout. One directory → `cp-a` has no ≥4-directories to stand on. | §3.2 rule 5, §4.1 rule 4, §4.2 step 5, §4.4 | 1, 2, 4, 8 |
| `nested_root/` | 10 | `restored/` in miniature: pyproject at `src/`, so **anchor root ≠ import root**, and `tests/` outside the declared package. The **only** fixture with ≥3 map nodes, so the only one that exercises the packing and placement code at all. Carries both corrected **relative-import** forms and one dangling target. | §3.2 rule 1, §3.4, §3.7 rank 1+3, §3.8 row 3, §4.1, §4.2 | 2 |
| `no_entry/` | 9 | **No entry point of any kind** and no test candidate, on a repo that is otherwise healthy — four directories, four map nodes, a straight-line import chain. | §3.2 rule 4, §3.7, §4.1 rule 4 | 1, 2, 8 |
| `hazards/` | 11 | **The whole of `read_source`'s error surface**, one hazard per file, plus the render-armour strings and a stdlib name shadowed by a repo module. | §3.1, §3.3, §3.4, §3.5, §7 | 1, 2, 4, 8, 9, 10 |

`hazards/` is the highest-value asset here. Everything else in this directory duplicates a
layout that exists somewhere on this machine; the encoding paths exist nowhere else and will
not be exercised before demo day by anything but this repo.

## `hazards/` — the file-by-file table

| File | Hazard | What breaks without the guard |
|---|---|---|
| `pkg/__init__.py` | 0 bytes | `lines == []`, `loc == 0`. Also what makes cascade rule 4 fire. |
| `pkg/crlf.py` | every line ends `\r\n` | CRLF is the **majority case on this machine** — 93/93, 140/161, 28/28, 6/7 `.py` across four local repos. Unnormalised, `'import os\r'` is not findable by a model's verbatim quote and hashes differently: a **100% claim-drop rate** (§3.1). |
| `bom.py` | UTF-8 BOM | Decoded as plain `utf-8` the file starts `﻿` and `ast.parse` raises on line 1. `utf-8-sig` strips it. |
| `latin1.py` | latin-1 bytes behind a PEP 263 cookie | `utf-8-sig` raises on `0xe9`; `tokenize.detect_encoding` must find the cookie before the latin-1 fallback fires. Verified: `read_source` returns `encoding=iso-8859-1`, `degraded=False`. |
| `formfeed.py` | `\x0c` inside a docstring | `str.splitlines()` splits on it and `str.split("\n")` does not. Measured on this file: 8 fragments vs 7 real lines — every `ast.lineno` below the docstring then points at the wrong source text. This is why §3.1 forbids `splitlines()`. |
| `longline.py` | one line of **exactly 5,000 chars** | Excerpt windows, the resolver's quote match, and the rendered `<pre>`. |
| `broken.py` | `def broken(:` — a real `SyntaxError` | §3.5 must record `{path,line,offset,msg}`, set `parsed=false`, **keep** `loc` and the file entry, and **continue**. Never raise. Measured: line 3, offset 12, `invalid syntax`. |
| `image.py` | a real 68-byte PNG named `.py` | The NUL check in `read_source` step 1 is the only thing that stops this reaching `ast`. A NUL through `ast.parse` is a **`ValueError`, not a `SyntaxError`** — which is exactly why §3.5 catches both. |
| `evil.py` | `<script src="…">`, `</script>`, `@font-face`, `@import`, `/*`, and the literal splice marker `RENDER — knows only` | Decision 9's four armour rules and `check-bundle.js`. A splice that searches for the marker anywhere but the template will cut the bundle inside this file's payload. Also carries a second dangling target. |
| `secrets.py` | bare stem shadows a stdlib module | `known` is built **per import root** (§3.4), so `pkg/crlf.py`'s `import secrets` must resolve to this file and must not shadow stdlib `secrets` anywhere else. `stdlib_shadowed` should be exactly `["secrets"]`. |

## `expect.json`

One per repo, so *"it degraded correctly"* is checked and not merely *"it did not crash"*.

| Key | Contract | Meaning |
|---|---|---|
| `degradations` | **yes**, §11.1 | Exact set, order-insensitive, of the §9 codes expected to fire. |
| `map_nodes` | **yes**, §11.1 | `len(map.nodes)`. Omitted on `hazards/` — see below. |
| `degradations_if_no_churn` | no | Merge into the expected set **when `survey.churn.available` is false**. See the git caveat. |
| `degradation_rows` | no | The §9 **row numbers**. This is the normative statement of intent — see the naming caveat. |
| `repo`, `proves`, `plan`, `notes` | no | Documentation. A harness should ignore unknown keys. |

`hazards/expect.json` omits `map_nodes` on purpose: that repo is here to prove survey degrades
honestly, and pinning a node count to it would make an unrelated `collapse()` tweak look like
an encoding regression. Its `notes` list the assertions worth making instead — one parse
failure naming `broken.py`, one `walk.skipped` entry naming `image.py`, `stdlib_shadowed ==
["secrets"]`, one dangling target.

### Caveat 1 — the degradation code strings are a best guess

The plan gives exactly two verbatim codes, `no_churn` and `no_test_command` (§2, §11.1). The
other nine rows of §9 are described by trigger, not by code string, and the module that emits
them is owned by another agent. The strings in `degradations` follow the two known ones'
convention; **`degradation_rows` is the authoritative claim.** If the generator emits different
strings, reconcile against the row numbers and update the strings here — the rows are what these
repos were built to fire.

Two rows are ambiguous in the plan and may legitimately not append to `degradations` at all:
rows 9 and 10 carry `—` in the Mode column and say only "count in the audit ledger", while
§9's preamble says *every* fired row appends. They appear in `hazards/expect.json` because that
is the reading the preamble supports; drop them there if the implementation says otherwise.

### Caveat 2 — `no_churn` depends on whether these files are committed

All four repos sit **inside the ML-GS working tree**, so `git rev-parse --is-inside-work-tree`
returns true for every one of them. Whether §9 row 6 fires therefore depends on commit state,
not on repo content:

- **uncommitted** → `log -1 --format=%H -- .` is empty → `GIT_UNTRACKED` → `no_churn` fires;
- **committed** → `GIT_OK`, churn available, `no_churn` does not fire.

`degradations` is written for the **committed** case, which is the state §11.1 assumes
("checked in"). A harness should union `degradations_if_no_churn` whenever
`survey.churn.available` is false rather than branch on commit state itself.

### Caveat 3 — the node counts are derived, not measured

`map_nodes` is derived from §4.1's collapse rules by hand; `mapper.py` did not exist when these
were written. The derivations are in each `notes` array. `nested_root` = 4 assumes adaptive
depth settles at 2 (`widget`, `widget/core`, `widget/io`, `tests`) and that rule 3 merges
nothing, which is why `tests/` deliberately holds two files rather than one. If `collapse()`
legitimately settles elsewhere, **fix the number, not the repo.**

## `.gitattributes`

`core.autocrlf` is `true` on this machine and there was no `.gitattributes` anywhere in the tree
(§3.1). Left alone, git would rewrite `hazards/pkg/crlf.py` to LF on commit and rewrite every
other `.py` here to CRLF on checkout — silently destroying the one asset that ever exercises
`read_source`'s normalisation, and doing it in a way no test would notice.

`* -text` freezes every byte. `*.md text eol=lf` puts the prose back in the text lane so these
docs still diff. `expect.json` stays frozen with everything else; it is already LF.

## House rules for editing these

- **Tiny.** These are fixtures, not projects. If a file needs a second idea, it needs a second
  file, and if a repo needs a fifth path proved, it needs a fifth repo — and §11.1's answer to
  that was *no*, ten more repos is 40–80 files of authoring for paths the demo never walks.
- **One repo, one path.** Every file above earns its place by forcing something. Adding an
  entry point to `no_entry/` or an internal edge to `flat_script/` does not make them more
  realistic; it makes them prove nothing.
- **Byte-exactness is the point in `hazards/`.** Do not open those files in an editor that
  normalises line endings, strips a BOM, or re-encodes. Verify with `read_source`, not by eye.
- Nothing here is discovered by `unittest discover -s tests`: `tests/repos/` has no
  `__init__.py`, and `unittest` does not descend into a directory that is not a package.
  `nested_root/src/tests/test_*.py` is therefore inert. Confirmed — discovery still reports
  101 tests.
