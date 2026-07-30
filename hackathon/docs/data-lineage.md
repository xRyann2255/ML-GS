# Data Sources and Lineage

Where Trailhead's data comes from, how it enters this repository, what transforms it,
and what it ultimately decides. Written against the working tree on 2026-07-30.

**Evidence statuses.** `VERIFIED` — directly supported by code, config, tests, or
runtime output captured while writing this. `DERIVED` — computed from the call graph,
the frozen contract, or cross-file analysis. `INFERRED` — likely from naming or
surrounding context, not provable from what is here.

**Line-number caveat.** `demo/trailhead-demo.html` has uncommitted changes in flight
(git status `AM`; the file was rewritten by the GS restyle at 17:58:38 during this
analysis). Its line numbers below are pinned to that state — 1677 lines, 69 553 bytes.
All other cited files are clean.

---

## 0. The one thing to understand first

**Four of the five pipeline stages do not exist yet.** `README.md:110` states it and the
code confirms it: `src/trailhead/` contains exactly two modules, and neither reads a
file, shells out, or calls a model.

```
grep -rn "open(|Path(|os\.|subprocess|json\.|walk" src/ --include="*.py"
→ src/trailhead/survey.py:19:    for node in ast.walk(ast.parse(source))
```
`VERIFIED` (runtime output, this session). The only match is an AST walk over a string
already in memory.

Consequently the payload that drives everything downstream is **hand-written**, and the
repository it describes — `payments-core`, with `src/api/app.py`, `src/pricing/engine.py`
and so on — **does not exist in this repository or anywhere on this machine**.

```
ls ../src/api/app.py → No such file or directory
```
`VERIFIED` (runtime output). Those paths are *string data inside a fixture*, not source
files. Every path quoted inside `fixtures/verified.sample.json` should be read as a
value, never as a location. `demo/trailhead-demo.html:441` labels the page
`SAMPLE · SYNTHETIC REPO` on screen for the same reason.

So this document describes two different things and keeps them apart:

- **Live lineage** — data that actually moves through code that exists today.
- **Contracted lineage** — the shape a stage will consume, frozen in
  `docs/verified-contract.md` and already enforced by the gates, but with no producer.

---

## The transport spine

Everything in §2–§5 shares one ingestion path, so it is described once here.

```
fixtures/verified.sample.json          (source of truth, 924 lines)
  → inline-fixture.js:22  JSON.parse
  → inline-fixture.js:31-45  brace-matched splice of the `const D = {…}` block
  → inline-fixture.js:49-50  JSON.stringify(D, null, 1) written into the HTML
  → demo/trailhead-demo.html:483-1406  `const D`
  → demo/trailhead-demo.html:1411+  renderer
```

| Step | Evidence |
|---|---|
| The fixture is the single source of truth; the HTML data block is generated, never hand-edited | `VERIFIED` — `tools/inline-fixture.js:1-12`, `docs/verified-contract.md:195-198` |
| Only the `const D` block is rewritten; the shell is byte-identical | `VERIFIED` — `tools/inline-fixture.js:49` splices `src.slice(0,a)` + payload + `src.slice(end+1)` |
| Brace matching is string-aware, so payload text cannot fake the terminator | `VERIFIED` — `tools/inline-fixture.js:32-44` tracks `inStr`/`esc`/`quote` |
| Both gates report identical figures against the HTML and against the JSON, which is what proves the splice preserved the payload | `VERIFIED` — runtime, both runs print `tracks 5 \| stops 11 \| bundled files 7`, `anchors sha256-verified 13` |

**If missing or unreadable:** `inline-fixture.js:19-20` and `verify-contract.js:23-24`
both `process.exit(2)` with `not found:`. `VERIFIED` (runtime — the exit-2 path fired
during this analysis when a scratch file was absent).

---

## 1. Repository Python source → import edges

**Business meaning.** Which module depends on which. This is what the architecture map
is drawn from, and — per non-negotiable #6 — what checkpoint answer keys must be derived
from, so the page can grade a learner without a model in it.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | `.py` files in the target repo, as text, plus the dotted module name of the file | `VERIFIED` — `src/trailhead/survey.py:9` signature `parse_imports(source, module)` |
| **INGESTION** | `survey.parse_imports` — `src/trailhead/survey.py:9-31`. Takes source **already in memory**; nothing in the package opens a file | `VERIFIED` — code + the grep in §0 |
| **VALIDATION** | `ast.parse` — `src/trailhead/survey.py:19`. A syntactically invalid file raises `SyntaxError`, uncaught | `VERIFIED` — code. No try/except exists in the module |
| **TRANSFORMATION 1** | AST walk collects `ast.Import` → `alias.name`; `ast.ImportFrom` → `base + "." + alias.name` — `src/trailhead/survey.py:19-30`. Relative imports resolved by climbing one package per dot: `module.split(".")[:-node.level]` — `:26-28` | `VERIFIED` — `tests/test_survey.py:34-48` covers single- and multi-dot |
| **TRANSFORMATION 2** | `survey.resolve_import` — `src/trailhead/survey.py:34-46`. Walks prefixes longest-first against a `known` set; returns the module or `None` | `VERIFIED` — `tests/test_survey.py:51-73` |
| **CONSUMER** | **None in this repository.** No caller exists — no file walker, no `known` set builder, no `survey.json` writer, no git-churn reader | `VERIFIED` — grep in §0; `README.md:110` lists Survey as not started |
| **OUTCOME (contracted)** | `map.nodes[]` / `map.edges[]` (`fixtures/verified.sample.json:18-148`) and checkpoint `provenance` strings such as `"survey.json → imports → calendars.* is imported by 4 modules"` (`:515`, `:530`, `:780`, `:795`) | `DERIVED` — the fixture cites `survey.json` as the key's origin; no code produces it |

**Ambiguity handled on purpose.** `from pkg.sub import thing` emits `pkg.sub.thing`
whether `thing` is a submodule or a symbol, because one file cannot tell; the longest-known-prefix
walk in `resolve_import` collapses it later. `VERIFIED` — `src/trailhead/survey.py:10-16`
documents it, `tests/test_survey.py:23-32` and `:54-59` pin both halves.

**If missing/invalid:** third-party imports resolve to `None` and are deliberately not
nodes (`tests/test_survey.py:64-67`, asserting `os.path` and `fastapi` → `None`).
An unknown submodule falls back to its known parent (`tests/test_survey.py:69-73`).

**Tests:** `tests/test_survey.py` — 8 tests, both classes.
```
PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
→ Ran 8 tests in 0.001s / OK
```
`VERIFIED` (runtime, this session).

> **Visible lineage ends here.** Between `parse_imports` and the `map`/`provenance` values
> in the fixture there is no code. Stages 2–4 are absent.

---

## 2. Bundled source lines and anchor hashes — the evidence substrate

**Business meaning.** The proof behind every claim: the actual repo lines a sentence
cites, shipped inside the artifact so it verifies offline. This is the mechanic the whole
pitch rests on.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | Source lines of the target repo at the recorded commit (`repo.commit`, `fixtures/verified.sample.json:4`). Today: hand-written into the fixture | `VERIFIED` — `docs/verified-contract.md:132-134` assigns re-reading to stage 4, which does not exist |
| **INGESTION** | `files` map — `fixtures/verified.sample.json:150-226`. Shape: path → line-number-as-string → verbatim line, no trailing newline. 7 files bundled | `VERIFIED` — `docs/verified-contract.md:65-76`; gate prints `bundled files 7` |
| **VALIDATION** | `anchor()` — `tools/verify-contract.js:62-81`: anchor present (`:63`), file bundled (`:65`), range inside bundled bounds (`:66-68`), focus lines inside `[start,end]` (`:69-70`), **every** line present (`:71-73`), `sha256` present (`:75`), hash matches (`:77-79`) | `VERIFIED` — code + runtime |
| **TRANSFORMATION** | `excerptOf()` — `tools/verify-contract.js:55-59`: lines `start..end` joined with `\n`, no line numbers, no trailing newline; SHA-256 hex over UTF-8 (`:77`) | `VERIFIED` — matches the spec text at `docs/verified-contract.md:126-129` verbatim |
| **CONSUMER** | `excerpt()` — `demo/trailhead-demo.html:1421-1436`, called by `B.prose` (`:1444`), `B.excerpt` (`:1447`) and `B.trace` (`:1457`) | `VERIFIED` — code |
| **OUTCOME** | The line-numbered code table in a claim popover, focus lines highlighted (`:1426`), plus the COPY button payload (`:1429`, `:1432`) | `VERIFIED` — code |

**If a line is missing:** the renderer degrades rather than crashes — it emits a
`… elided` row and continues (`demo/trailhead-demo.html:1425`). The gate is stricter and
fails the bundle first (`tools/verify-contract.js:73`). `VERIFIED`.

**If the excerpt was tampered with:** hash mismatch, and one changed line takes down
every anchor citing it. Experiment run this session — one bundled line edited in a copy
of the fixture:
```
FAIL  c-001: sha256 mismatch on src/api/app.py:58-66
FAIL  trace hop 1: sha256 mismatch on src/api/app.py:58-66
anchors sha256-verified 11        (13 when clean)
2 FAILURE(S)   EXIT=1
```
`VERIFIED` (runtime output, this session). This is the claim at `README.md:117-120`, and
it holds.

**Tests:** `tools/verify-contract.js` (acceptance test 3, `docs/walkthrough-spec.md:307`).
13 anchors hash-verified on both the HTML and the JSON.

---

## 3. Narrated claims — the only model-authored data

**Business meaning.** The prose a new joiner reads. Every factual sentence is one claim
carrying its own evidence, or is visibly marked as unproven.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | Stage 3 NARRATE, one small model call per unit, returning claims + **verbatim quotes, never line numbers** | `DERIVED` — `README.md:96`, `CLAUDE.md` non-negotiable #7, `src/trailhead/__init__.py:7`. No client, no prompt, no interface exists in the tree |
| **INGESTION** | `prose.claims[]` — e.g. `fixtures/verified.sample.json:294-362`. Each claim: `id`, `text`, `status`, optional `anchor` | `VERIFIED` — fixture + `docs/verified-contract.md:107-113` |
| **VALIDATION** | `tools/verify-contract.js:86-94`: `status:"inferred"` **must not** carry an anchor (`:91`) — otherwise it renders as verified, which the contract calls "a lie by markup" (`docs/verified-contract.md:121-123`). Anything else must pass `anchor()` (`:92`) | `VERIFIED` — code |
| **TRANSFORMATION (contracted)** | Quote → line range resolved *in code* by searching the file for the snippet; a snippet not found verbatim is deleted, not repaired | `DERIVED` — `README.md:96`, `CLAUDE.md` build order hours 5–6. Unimplemented |
| **CONSUMER** | `B.prose` — `demo/trailhead-demo.html:1440-1445`. Two branches: `inferred` → plain span + `INFERRED` tag, no marker, no popover (`:1442`); verified → claim + `.mark` button + hidden `.pop` holding the excerpt (`:1443-1444`) | `VERIFIED` — code |
| **OUTCOME** | A sentence a reader can expand to the exact `file:line` that backs it. Marker click toggles the popover — `demo/trailhead-demo.html:1615-1616` | `VERIFIED` — code |

**Counts today:** `rendered claims 12 (inferred 5)`. `VERIFIED` (runtime).

**If the anchor does not resolve:** the claim never reaches this entity — it is routed to
§5's ledger instead. That routing is the product.

---

## 4. Command execution records

**Business meaning.** Proof the setup instructions were actually run, including the ones
that fail. Non-negotiable #4: output is real or the run is a fraud.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | A command runner executing setup/test commands on the generation machine and capturing exit code, stdout and wall-clock time | `DERIVED` — `README.md:92`, `CLAUDE.md` architecture. **No runner exists**; no `subprocess` call anywhere in `src/` |
| **INGESTION** | `command` blocks — `fixtures/verified.sample.json:549-611`. Fields: `cmd`, `cwd`, `exit`, `dur`, `out`, `env`, and for failures `broken` + `hypothesis` | `VERIFIED` — fixture + `docs/verified-contract.md:146`, `:156-161` |
| **VALIDATION** | `tools/verify-contract.js:101-106`: `exit !== 0` must carry `broken` (`:103`), `env` required (`:104`), non-empty `out` required (`:105`) | `VERIFIED` — code |
| **TRANSFORMATION** | None numeric — deliberately. `dur` is stored as a display string (`"11.4 s"`, `:552`) and `env` as a capture note (`"captured 2026-07-30, ubuntu-22.04, docker 24.0.7"`, `:554`) | `VERIFIED` — fixture + contract `:156-158` |
| **CONSUMER** | `B.command` — `demo/trailhead-demo.html:1449-1455`: exit pill coloured by `b.exit` (`:1451`), BROKEN banner (`:1452`), `<details>` output with a computed line count (`:1454`), env note (`:1455`) | `VERIFIED` — code |
| **OUTCOME** | `report.failed` (`fixtures/verified.sample.json:13`) and the red banner. The `hypothesis` — the cause guess — is always rendered tagged `INFERRED` (`demo/trailhead-demo.html:1453`), and the fixture text ends "Unverified — this tool did not test the fix" (`:572`, `:583`) | `VERIFIED` — code + fixture |

**If a command fails:** it is shown failing. Two of five do. `VERIFIED` — runtime prints
`commands 5`, and the report/page cross-check at `tools/verify-contract.js:137-139`
passes with `report.failed` = 2.

**If output is empty or `env` absent:** gate failure, exit 1 — `tools/verify-contract.js:104-105`.

---

## 5. Verification report and dropped-claim ledger

**Business meaning.** The headline numbers: how many claims the machine caught the model
inventing. Non-negotiable #3 — hiding the drop count defeats the entire point.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | Stage 4 VERIFY, counting over the whole generation run | `DERIVED` — `docs/verified-contract.md:54-63`; unimplemented |
| **INGESTION** | `report` — `fixtures/verified.sample.json:7-16`; `dropped[]` — `:873-921`. Each drop: `id`, `text`, `file`, `reason` | `VERIFIED` — fixture |
| **VALIDATION** | `tools/verify-contract.js:128-139`: a dropped id must appear nowhere in `tracks` (`:131`), `reason` required (`:132`), `report.dropped === dropped.length` (`:134`), `report.failed ===` count of failing command blocks (`:137`) | `VERIFIED` — code |
| **TRANSFORMATION** | None. The counts are carried verbatim; `docs/verified-contract.md:61-63` notes they intentionally exceed what the page renders (142 claims made, 12 rendered) — that gap is the pitch | `VERIFIED` — fixture + contract |
| **CONSUMER** | `ledgerTable()` — `demo/trailhead-demo.html:1499-1512`: six-figure summary grid (`:1501-1506`) and the deletion table with reasons (`:1508-1509`). Rendered by `B.ledger` (`:1493`) at the audit stop, and into the modal opened from the badge (`:1642`, `:1666-1667`) | `VERIFIED` — code |
| **OUTCOME** | The audit panel and the on-screen deleted count | `VERIFIED` — code |

**Drop reasons in the fixture** — `file does not exist at this commit` · `snippet not
found verbatim in file` · `lines 44-51 out of range (file ends at 38)` · `excerpt hash
mismatch — file changed after narration` (`:873-921`). Each maps to a specific check in
§2's `anchor()`. `DERIVED`.

### Finding — the static top bar is outside this lineage

`demo/trailhead-demo.html:435-453` renders the header from **hard-coded literals**, not
from `D`: `payments-core` (`:438`), `a3f9c21` (`:439`), `142 claims` (`:443`),
`8 dropped` (`:444`), `23 cmds` (`:445`), `2 failing` (`:446`). They agree with
`report` today, and nothing keeps them agreeing:

- `inline-fixture.js` rewrites only the `const D` block (`:49`), so a fixture edit cannot
  update them.
- Neither gate reads the header — `verify-contract.js` parses `D` only (`:27-38`).

Verified by experiment. A copy of the bundle with the header changed to `WRONG-REPO` and
`1 dropped`, ledger untouched:
```
node tools/verify-contract.js …/stale-badge.html → ALL ANCHOR + CONTRACT CHECKS PASS  EXIT=0
node tools/check-bundle.js     …/stale-badge.html → BUNDLE OK                          EXIT=0
```
`VERIFIED` (runtime, this session). This is the same failure class `README.md:63-64`
records the gate catching once before ("badge said 2 failing commands, page displayed 1")
— caught then inside `D`, uncovered now in the shell. Stage 5 should render the header
from `D.report`, or `verify-contract.js` should scrape and compare it.

---

## 6. Learner progress state

**Business meaning.** Where the reader is, which stops are done, and how they answered.
The only data the artifact writes rather than reads.

| Stage | Detail | Evidence |
|---|---|---|
| **SOURCE** | Browser `localStorage`, keyed `"trailhead:" + D.repo.name + ":" + D.repo.commit` — `demo/trailhead-demo.html:1413` | `VERIFIED` — code |
| **INGESTION** | `demo/trailhead-demo.html:1416-1417`: `S = {cur:0, done:{}, ans:{}}` then `Object.assign(S, JSON.parse(localStorage.getItem(KEY) \|\| "{}"))` inside try/catch | `VERIFIED` — code |
| **VALIDATION** | Corrupt JSON is swallowed by the `catch` and defaults survive (`:1417`). **No shape validation** — a well-formed but wrong-shaped object is merged in as-is | `VERIFIED` — code; the `catch(e){}` guards parsing only |
| **TRANSFORMATION** | Grading happens here, in the page: single-answer `S.ans[id]={pick:i, ok:i===b.answer}` (`:1624`); ordering `ok: pick.every((v,k)=>v===b.answer[k])` (`:1630`). `b.answer` comes from the payload, whose key traces to `survey.json` (§1) — never to a model | `VERIFIED` — code + `fixtures/verified.sample.json:514-515` |
| **CONSUMER** | `B.checkpoint` (`:1475-1491`), `verdict()` (`:1495-1498`), `rail()` progress (`:1548-1551`), `draw()` (`:1555-1572`) | `VERIFIED` — code |
| **OUTCOME** | Correct/incorrect marks, the explanation with its `ANSWER KEY` provenance line (`:1496-1497`), the progress percentage, and the URL hash (`:1569`) | `VERIFIED` — code |

**If unavailable** (private mode, quota, `file://` restrictions): both reads and writes
are wrapped — `:1417` and `:1418` — so the page runs with in-memory state and silently
loses progress on reload. `VERIFIED` — code.

**If stale:** a changed `repo.commit` yields a different key, so a regenerated artifact
starts fresh rather than replaying answers against different content — `:1413`.
`VERIFIED` (code); this is acceptance test 7, `docs/walkthrough-spec.md:311`, which has
no automated check. Manual reset: `:1653`.

---

## Where the visible lineage ends

| Boundary | Status |
|---|---|
| Target-repo files → `survey.json` | **No code.** `parse_imports` accepts a string; nothing walks a tree, reads git churn, or writes the file. `VERIFIED` |
| `survey.json` → `map.json` (stage 2) | **No code.** `map.x/y/w` in the fixture are hand-placed; the contract fixes layout at generation time (`docs/verified-contract.md:88-89`). `VERIFIED` |
| Model → `content.json` (stage 3) | **No code, no named tool.** Open decision 1, `README.md:142` |
| `content.json` → `verified.json` (stage 4) | **No code.** The quote→line resolver, the hash check and the deletion path exist only as assertions in `tools/verify-contract.js`, which the header calls "a stand-in for stage 4" (`CLAUDE.md`) |
| Command runner → `command` blocks | **No code.** No `subprocess` anywhere. `VERIFIED` |
| `verified.json` → HTML | **Exists**, as a splice (`inline-fixture.js`) rather than a generator. Stage 5 is prototyped, not written — `README.md:112-115` |

Everything downstream of `const D` is real, tested and gated. Everything upstream of it is
a contract with no producer. The fixture is not a mock of the pipeline's output — right
now it *is* the pipeline's output.

Also present and **not** a data source: `hackathon/restored/` (1 147 files) is untracked
by git and referenced by no code in `hackathon/` — a restored copy of a different
project's workspace. `VERIFIED` (`git ls-files hackathon/restored` → 0; grep for
`restored` across `.js`/`.py`/`.html`/`.json` → no hits).

---

## Reproducing the evidence

```bash
cd hackathon
node tools/check-bundle.js      # → BUNDLE OK, exit 0
node tools/verify-contract.js   # → ALL ANCHOR + CONTRACT CHECKS PASS, exit 0
node tools/verify-contract.js fixtures/verified.sample.json   # identical figures
PYTHONPATH=src py -3.11 -m unittest discover -s tests -v      # → Ran 8 tests, OK
```

Captured 2026-07-30: `tracks 5 | stops 11 | bundled files 7`,
`rendered claims 12 (inferred 5) | checkpoints 4 | commands 5 | dropped 8`,
`anchors sha256-verified 13`.
