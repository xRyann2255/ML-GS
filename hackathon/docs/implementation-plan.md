# Trailhead — Generic Generator Implementation Plan

**Status:** authoritative build plan, 2026-07-30. Supersedes the build-order rows in
`README.md` and `walkthrough-spec.md` §9. Does not supersede `docs/verified-contract.md`
or `docs/pipeline-contracts.md` — those are frozen seams and this plan codes against them.

## What exists today

Verified by running the gates, not by reading the code:

```
node tools/check-bundle.js      BUNDLE OK · 21 checks · 81.5 KB · 284/284 braces   exit 0
node tools/verify-contract.js   5 tracks | 11 stops | 13 anchors sha256-verified   exit 0
node tools/check-fixtures.js    FIXTURE CHAIN CONSISTENT · 27 checks               exit 0
```

**`check-fixtures.js` is a repo invariant, not a build gate.** `DIR` is hard-coded to
`../fixtures` and the four sample filenames are `require`d; it takes no argv. Running it after
generating a bundle re-checks the shipped synthetic fixtures and exits 0 regardless of what was
produced. Wherever this plan says "all three gates", the two that read the artifact are
`check-bundle` and `verify-contract`.

- **Stage 5 RENDER exists as a working, browser-tested HTML renderer** — `demo/trailhead-demo.html`,
  1900 lines, nine block types, claim markers, audit ledger, SVG map, two checkpoint kinds,
  predict-then-reveal, localStorage progress. Its data is `fixtures/verified.sample.json`
  spliced in by `tools/inline-fixture.js`.
- **Four fixtures describe one synthetic repo** (`payments-core @ a3f9c21`) and agree with
  each other. The whole chain is testable before a single real repo is surveyed.
- **Stage 1 SURVEY is two pure functions** — `parse_imports`, `resolve_import` — with 8 passing
  tests. Everything else in stages 1–4 is unbuilt.

> A recon lens reported `check-bundle.js` failing on `@font-face` inside a CSS comment.
> **That is stale.** It exits 0 as of the run above. Do not start by "fixing" it.

## What this plan builds

Point `trailhead` at any Python repo; get one self-contained HTML walkthrough that shows its
own evidence. `hackathon/restored` is the proving ground — a 455-file, 12-package, zero-git-history,
partially-broken snapshot that fires three of the five degradation paths on its own.

## The strategy, in one sentence

Ship a **walking skeleton in the first hour** — render `fixtures/verified.sample.json` through
a Python `render.py` into a gate-green HTML file — then replace exactly one fixture per stage,
keeping both artifact gates green the entire way, so at no point is there a valley where nothing
runs.

## Reading this as a team

The five briefs in `briefs/` split this plan by owner. The mapping is exact:

| Owner | Sections | Files |
|---|---|---|
| A | §3, §4, and the checkpoint half of §5 | `survey.py` `mapper.py` `checkpoints.py` |
| B | §5 | `compose.py` `prompts.py` `provider.py` `narrate.py` |
| C | §6, §8 | `resolve.py` `verify.py` `runner.py` |
| D | §7 | `template.html` (was `demo/trailhead-demo.html`) |
| E | §0, §7 splice, §10, §11, §13, §14 | `render.py` `cli.py` `textio.py` `tools/` `fixtures/` |

A single engineer follows §13's **spine** column and cuts everything else.

---

# 0. Decisions made here

Every open decision is closed. No section below leaves one dangling.

| # | Decision | Call | Why (one line) |
|---|---|---|---|
| 1 | **LLM interface** | `provider.py` — one method, `Provider.complete(system, user, schema) -> dict`. Two impls: `StubProvider` (default) and `ClaudeProvider`. | A one-method protocol makes "only stage 3 touches a model" structural, not a promise. |
| 2 | **Default provider** | `StubProvider`, reading the **same** `.trailhead/narration/<sha256>.json` store the live path writes. Live is opt-in via `--provider claude`. | The gates, the tests and the offline demo all exercise the real assembly path; a live call is the exception. One store and one key, or record/replay never hits. |
| 3 | **Named model** | `claude-opus-5`, `max_tokens=16000`, structured output via `output_config.format`. GS gateway is `base_url` from `TRAILHEAD_BASE_URL`, credential from `ANTHROPIC_API_KEY` — two env vars, zero code above the protocol. | The brief requires naming a tool; naming the model gives real, checkable limits, and the internal endpoint stays a config detail. |
| 3b | **The one dependency** | `anthropic>=0.40`, installed by `py -3.11 -m pip install anthropic` as stage 0 item 7 and smoke-tested at hour 0, not hour 6. Nothing else leaves stdlib. | Structured output plus a `base_url` override in one supported client. Hand-rolling the HTTP is more code and no less of a dependency on the wire format. |
| 4 | **Narration cache** | On-disk, keyed `sha256(rendered_prompt_text)`, in `.trailhead/narration/`. Committed after the first good run; a miss under `--offline` is a hard error. | A rehearsal at 9pm and the run on stage produce byte-identical narration, and re-runs cost nothing. |
| 5 | **Fixture narration** | Record/replay, never hand-authored. Run live once, commit the cache directory. | ~40 byte-exact multi-line quotes transcribed by hand is an hour of work that produces a ledger full of your own typos. |
| 6 | **Language scope** | Python only, stdlib `ast`. Anchors additionally permitted into any UTF-8 text file that survey listed (`pyproject.toml`, CI YAML, `Makefile`). Stated on screen in the cover stop and the ledger. | `pyproject.toml:52` is the single most anchorable fact in the proving-ground repo, and line-based anchoring is language-agnostic. Disclose the limit, don't imply more. |
| 7 | **Render approach** | **Template-splice.** `demo/trailhead-demo.html` becomes `src/trailhead/template.html`; `render.py` reads it, armours the JSON, splices between two literal markers. | The 44 KB shell earns all 21 check-bundle passes for free and is browser-tested for nine block types. Emitting HTML from Python means re-earning every one by hand, for zero pitch value. |
| 8 | **Shell templating** | One 14-line `shell()` function in the template reading `D.repo` and `D.report`. Not seven sentinel replacements. | One splice point instead of eight; `textContent` escapes a repo name for free; and the §6 amber badge becomes two lines instead of impossible. |
| 9 | **Payload armour** | Four `\uXXXX` escape rules on the serialized JSON text. **Verified by experiment** (§7). | The recon's `\/*` rule is a no-op — `\/*` still contains `/*`. So does `\/`. Only `\u002f` removes the character. |
| 10 | **Demo repo (develop)** | `hackathon/restored/`, source root `restored/src`. | Real size, real nesting, unread as a codebase, and it fires three degradation paths honestly. |
| 11 | **Demo repo (stage)** | Generate against **both** `restored/` and one CRLF repo with real git history. Recommended second: `C:/Users/ryanv/Documents/Projects/ryanatron-v2` (93/93 CRLF, real history) — confirm it is unread before hour 4. | `restored/` has zero churn and no green test, so it is an excellent degradation showcase and a weak happy-path one. |
| 12 | **Pipeline order** | survey → map → **runner** → narrate → verify → render. The runner moves *before* narrate. | Narrate can then see which commands really failed, write the `hypothesis` for a real traceback, and make every degradation decision in one deterministic place. |
| 13 | **Who owns the stop list** | `compose.py`, inside stage 3, deterministic. The model fills claims only; it never invents a stop. | `content@1` carries `tracks`, so the skeleton must be produced by stage 3 — but nothing says a *model* produces it. |
| 14 | **Contract version tag** | Emit `trailhead/verified@2`. Patch `verified-contract.md`'s version line to match. | `fixtures/verified.sample.json` already says `@2`; the doc says `@1`. The gate ignores the string. Fix the doc, not three working artifacts. |
| 15 | **`cp-c1` answer key** | Fix to `[4,3,1,5,2]` in **both** `survey.sample.json` and `verified.sample.json`. Stage 0. | Confirmed by simulation: the shipped `[3,5,2,1,4]` demands `serialize_price` first and grades the correct order wrong. Both gates pass it. A checkpoint that marks the right answer wrong is a live on-stage failure. |
| 16 | **Map density cap** | 14 nodes, not spec §4.4's 40. Amend the spec line. | 900×400 with node widths ~142 holds 5 columns × 6 rows. 40 nodes is 71% fill and the renderer has no zoom, no pan and no density collapse despite §4.4 promising all three. |
| 17 | **Dynamic viewBox** | **Cut.** Canvas stays hard-coded 900×400. | `.mapbox svg{width:100%}` means a wider viewBox zooms *out*, not gains space; and the proposed tick formula draws a tick past the right edge, regressing the shipped demo. |
| 18 | **Churn substitute** | When git has no history: rank by **fan-in**, exclude `__init__.py` under 20 loc, and say `fan-in (no git history)` in the column header and inside every `top[]` string. Amend spec §3 stop 3 and §4.4 to make churn optional with a declared substitute. | `restored/` has 0 commits and 0 tracked files. Never label fan-in as churn; the drawer heading `MOST-EDITED FILES` is hard-coded, so the substitution must be visible in the data. |
| 19 | **Per-node map narration** | **Cut before hour 0.** `node.why` is a deterministic template. | It is 10 of 17 model calls, and it routes unanchored model prose into a surface with no claim marker, no anchor and no gate coverage. |
| 20 | **`where` table purpose cells** | Purpose comes from the package `__init__.py` docstring's first sentence, or an em-dash. Model prose about layout goes in a `prose` block *above* the table. | Table cells have no claim machinery and `verify-contract.js` never walks them — a model sentence in a cell is an unverified factual claim on the stop a joiner reads second. |
| 20b | **Escaping the raw-interpolation surfaces** | `textio.cell(text, code=False)` — `esc_html(text)`, then optionally wrap in `<code>`. **Values are escaped; markup is added by the generator from a two-tag whitelist (`<code>`, `<b>`), never carried in the data.** Applies to `table.columns[]`, `table.rows[][]`, `checkpoint.options[]`, `excerpt.caption`, `callout.title`/`text`, and (SVG-sanitised) `map.nodes[].label`. | The renderer interpolates all of these without `esc()`. Blanket-escaping the whole cell would render the shipped fixture's `<code>src/pricing/</code>` as visible `&lt;code&gt;`; escaping the value and re-wrapping keeps both properties. |
| 20c | **Survey-derived prose on unanchored surfaces** | Permitted, and permitted *only* there: `node.why`, `top[]`, table cells, `stop.lede`, stop/track titles, callout titles and text. Every one is a deterministic template over `survey.json`/`map.json` — no model string ever reaches them. | NN2 governs model-authored sentences. A survey-derived string is verified by construction and re-derivable from the artifacts on disk; the rule that keeps it honest is that **no model output may reach a surface with no claim marker**. |
| 21 | **Command timeout** | 60 s per command, 120 s total budget. Diverges from C's brief (300 s). | Every measured candidate finishes under 3 s. A 300 s hang on stage is a dead demo. |
| 22 | **Command posture** | Deny-by-default allowlist of four argv shapes. No `ask` policy, no import-reachability engine. | "Execute from an allowlist, never because it was discovered" makes a denylist and a reachability walk dead code. |
| 23 | **Test-repo fixtures** | Four tiny repos, not fourteen. Genericity is proven against three real repos already on this machine. | Ten hand-written repos is 40–80 files of authoring to exercise paths the demo never walks. |
| 24 | **`map.w` / `map.h` keys** | Not added. `map@1` stays as frozen. | See #17. No contract change needed. |
| 25 | **Chain extraction (`chain.py`)** | **Cut at hour 0, not hour 5.** Trace hops for `restored/` are hand-specified in `fixtures/trace.restored.json` from recon's verified `file:line` list; `cp-c` becomes a layer-order checkpoint from the map column index. | Cutting it at hour 5 schedules it inside the window where only in-place fixes are permitted. |
| 26 | **Who writes `command.hypothesis`** | **`runner.classify_failure` only** — a rule table. The `hyp:<cmd-id>` narrate unit is **deleted**, taking `restored` from 7 units to 4. | Two producers and no precedence is a coin flip in the ledger. A rule table costs no call, no cache entry and no parse-failure path; asking a `hyp` unit would be legal under NN1 (it is inside stage 3) but buys nothing. `verify.py` tags whatever arrives `inferred` regardless of source. |
| 27 | **`repo.generated_at`, `report.tool_version`, `report.duration_s`** | Produced by `verify.assemble`, not survey. `TOOL_VERSION = "0.4.0"` in `__init__.py`; `duration_s` is a wall clock spanning stages 1–5; `generated_at` is `datetime.now(timezone.utc).isoformat()` at assemble time. | `shell()` reads all three. A missing `generated_at` throws inside `shell()` before a stop renders — a blank page that **both gates still pass**, because neither executes the renderer. |

---

# 1. Architecture as built

Five stages plus a runner. **Only stage 3 calls a model.**

```
repo ─▶ 1 SURVEY ─▶ survey.json ─▶ 2 MAP ─▶ map.json
             │                                  │
             ├──▶ RUNNER ─▶ commands.json ──────┤
             │                                  │
             └──────────▶ 3 NARRATE (LLM) ─▶ content.json
                                                  │
                              4 VERIFY ◀──────────┘
                                  │
              verified.json + verification-report.json
                                  │
                             5 RENDER ─▶ trailhead.html
```

## On-disk artifacts

All under `<out-parent>/.trailhead/`. Every stage reads its input from disk and writes its
output to disk; that is what makes any stage re-runnable alone.

| File | Contract | Produced by |
|---|---|---|
| `survey.json` | `trailhead/survey@1` | stage 1 |
| `map.json` | `trailhead/map@1` | stage 2 |
| `commands.json` | `trailhead/commands@1` | runner |
| `content.json` | `trailhead/content@1` | stage 3 |
| `verified.json` | `trailhead/verified@2` | stage 4 |
| `verification-report.json` | — (audit log, not shipped) | stage 4 |
| `narration/<sha256>.json` | — (prompt cache, committed) | stage 3 |

**One narration store, one key.** `.trailhead/narration/<sha256(prompt)>.json`, where the prompt
is `system + "\x00" + user`. `StubProvider` reads that same directory — there is no separate
`fixtures/narration/`. A stub miss returns `{"claims": []}` and the unit falls back to its
template blocks; under `--offline` a miss is a hard error instead.

## File tree this plan creates

```
hackathon/src/trailhead/
  __init__.py          exists                                            —
  __main__.py          `python -m trailhead …` entry point               5
  textio.py            THE file reader, THE path key, sha256, escape,    60
                       armour. Every other module imports these.
  survey.py            stage 1 — extends the existing 46 lines          300
  mapper.py            stage 2 — collapse + layout in 900×400           140
  checkpoints.py       answer keys from survey.json, no model            90
  runner.py            real subprocess execution + capture              150
  compose.py           the STOP_TABLE + block builders + degradation    220
  prompts.py           prompt construction, line-numbered windows        90
  provider.py          Provider protocol + StubProvider + Claude         90
  narrate.py           stage 3 orchestration, cache, response parsing   110
  resolve.py           quote → line range. The critical function.       110
  verify.py            stage 4 merge, ledger, files bundle, report      200
  render.py            stage 5 splice                                    90
  cli.py               argparse surface + stage driver                  110
  template.html        de-fixtured copy of the demo (delta only)         25

hackathon/tests/
  test_survey.py       exists (8) + roots, walk, classifier, churn     +120
  test_map.py          collapse + geometry invariants                    90
  test_checkpoints.py  answer-key derivation                             60
  test_resolve.py      the resolver. Most of the project's risk.        160
  test_verify.py       merge, ledger, report cross-checks                90
  test_runner.py       capture, timeout, encoding, truncation            90
  test_render.py       armour, splice, self-police                       70
  test_narrate.py      parser rejection rules                            70
  repos/               four tiny fixture repos (§11)                     60

hackathon/fixtures/
  *.sample.json        exist, frozen                                     —
  trace.restored.json  the hand-specified hops of Appendix A.3,          —
                       loaded by compose.build_trace
hackathon/out/         generated bundles. Gitignored, and excluded
                       from the walk via --out (§3.3)
```

**Out of scope for this plan**, and untouched by it: `hackathon/openclaw/`,
`docs/data-lineage.md`, `docs/gs-restyle-prompt.md`, `docs/teaching-features-prompt.md`,
`fixtures/verified.ml-gs.json`.

**≈1790 lines of implementation, ≈810 of tests.** That is a five-person figure. §13 gives the
one-person spine.

---

# 2. `survey.json` — the schema

`trailhead/survey@1`, frozen in `docs/pipeline-contracts.md`. **Extending is additive only.**
The frozen keys below are reproduced for reference; everything under *Additions* is new and
must not rename or retype anything above it.

```jsonc
{
  "contract": "trailhead/survey@1",

  "repo": { "name": "restored", "root": "C:/…/hackathon/restored",
            "commit": "nogit-4b17c2e9", "branch": null,
            "surveyed_at": "2026-07-30T18:40:11Z" },

  "stats": { "files": 1125, "py_files": 455, "loc": 96000, "modules": 364,
             "external_deps": ["numpy", "pandas", "torch", "…"] },

  // Every in-scope .py file. `module` is the dotted name, null if not importable.
  // `commits`/`last_commit`/`authors` are null-filled when churn is unavailable.
  "files": [ { "path": "src/volforecast/registry.py", "module": "volforecast.registry",
               "loc": 123, "commits": null, "last_commit": null, "authors": [] } ],

  // Module-level rollup. Key is the dotted name, `path` is the directory.
  "modules": { "volforecast.data": { "path": "src/volforecast/data", "files": 21,
                                     "loc": 9195, "commits": null,
                                     "top": [ { "path": "…/ohlcv.py", "fan_in": 12 } ] } },

  // Import edges, module → module. External imports are NOT edges.
  // Dangling imports are NOT edges either — see `dangling`.
  "edges": [ { "a": "volforecast.cli", "b": "volforecast.data", "n": 31 } ],

  // kind: console_script | module_main | main_guard | http_route | dockerfile_cmd
  "entry_points": [ { "kind": "console_script", "name": "volforecast",
                      "file": "src/pyproject.toml", "line": 53,
                      "target": "volforecast.__main__:main" } ],

  // Candidates only. Nothing has been run. `cmd` is the canonical string.
  // kind: setup | test | lint | run
  "command_candidates": [ { "cmd": "python -c \"import volforecast\"", "kind": "run",
                            "cwd": "src", "source": "src/pyproject.toml:50",
                            "confidence": "high" } ],

  // Answer keys. Static analysis only — non-negotiable #6 lives here.
  // Written in TWO passes: stage 1 writes the survey-only keys (cp-a1, cp-a2);
  // stage 2 calls build_checkpoints(survey, map) and REWRITES survey.json with the
  // map-derived ones (cp-c1) merged in, before narrate reads it. The map is
  // deterministic code, so #6 still holds — no model is involved either way.
  "checkpoints": { "cp-a1": { "kind": "single", "prompt": "…", "options": ["…"],
                              "answer": 1, "provenance": "…", "explanation": "…" } },
```

### Additions (new keys, all additive)

```jsonc
  // Root discovery. repo_root is the ANCHOR namespace; import_roots are sys.path entries.
  // On the proving-ground repo they differ, and conflating them is a silent empty graph.
  "roots": { "repo_root": "C:/…/restored", "import_roots": ["src"],
             "test_roots": ["src/tests"], "pyproject": "src/pyproject.toml",
             "declared_packages": ["volforecast"],
             "rule": "pyproject [tool.hatch.build.targets.wheel] packages" },

  "walk": { "scanned": 1125, "py_in_scope": 364, "excluded_dirs": 15,
            "skipped": [ { "path": "…", "reason": "not text" } ],
            "by_ext": { "py": 455, "md": 364, "yaml": 95 },
            "doc_only_dirs": ["memory", "workspace/docs", ".github"] },

  // Imports naming a module with no file on disk. Never a node, never an edge.
  // 14 targets / 706 statements on restored — the single most striking true fact about it.
  "dangling": [ { "target": "volforecast.config", "n": 120,
                  "sites": [ { "file": "src/volforecast/data/micro.py", "line": 14 } ] } ],

  "parse_failures": [ { "path": "…", "line": 12, "offset": 4, "msg": "invalid syntax" } ],

  // Three states, not two. GIT_OK | GIT_UNTRACKED | NO_GIT | GIT_ERROR
  "churn": { "state": "GIT_UNTRACKED", "available": false,
             "reason": "target path has no tracked history in the enclosing repository",
             "substitute": "fan_in", "by_file": {}, "committers": {},
             "discarded_paths": 0 },

  // Top-level names that are both repo modules and stdlib. Genuinely useful orientation.
  "stdlib_shadowed": ["inspect"],

  // Non-.py files anchors are permitted into. Predicate, exactly:
  //   read_source decoded it without degradation, size < 256 KB, AND
  //   (suffix in {.toml .cfg .ini .yml .yaml .json .md .txt .sh .cmd .ps1}
  //    OR name in {Makefile, justfile, Dockerfile}
  //    OR no suffix and the first line starts "#!")
  // The last clause is what admits `restored/vol`, a 22 KB extensionless bash script.
  "text_files": ["src/pyproject.toml", ".pre-commit-config.yaml", "vol"],

  // Which §6 rows fired. The input to every placeholder callout and the amber badge.
  "degradations": [ { "code": "no_churn", "reason": "…", "substitute": "fan-in" } ]
}
```

### Rules the gates enforce

- Every `edges[].a` / `.b` is a key in `modules`.
- Every `files[].path` is repo-relative, forward slashes, on every OS.
- Every `checkpoints` value satisfies `verified@1`'s checkpoint block exactly; `provenance`
  and `explanation` both required, and `provenance` names the survey field it came from.
- `command_candidates[].cwd` is repo-relative.

**Two frozen field semantics change, deliberately, and this is not additive.** `files[].module`
and the `modules` keys become **import-root-derived** (`volforecast.registry`, `volforecast.data`)
where the frozen fixture is path-derived (`src.api.app`, `src.api`); `map.nodes[].label` becomes
the group path relative to the import root (`data`) where the fixture has `src/api`. Neither
breaks a gate. Both are required: a path-derived dotted name is not an importable module name,
and `src/api` is 40% wider on the canvas than `api`.

### `map.json` — `trailhead/map@1`

`pipeline-contracts.md` says the map fixture is "inline in survey fixture". **It is not** —
`"map" in survey.sample.json` is false. Stage 2 writes `map.json` as its own file. Shape is
identical to `verified@1`'s `map` key plus a `contract` tag, plus one addition:

```jsonc
{ "contract": "trailhead/map@1",
  "nodes": [ … ], "edges": [ … ],
  "diagnostics": { "modules_in": 364, "groups": 12, "hidden_modules": 352,
                   "cycles_broken": 9, "edges_dropped_backward": 4, "edge_cap_hits": 3 } }
```

---

# 3. Stage 1 SURVEY

Deterministic, pure, test-driven. Timing is a non-issue: read + `ast.parse` over all 455 files
of `restored` is **917 ms**, ~2 ms/file. No caching, no parallelism, no incremental mode.
Re-run it every generation and treat `survey.json` as disposable.

## 3.1 `textio.py` — the one reader and the one path key

Exactly one function may read a source file. A second read path is a guaranteed sha256
mismatch between stage 4 and the gate.

```python
@dataclass(frozen=True)
class Source:
    lines: list[str]
    encoding: str
    degraded: bool          # decoded via latin-1 fallback
    note: str | None        # "not text" | "syntax error" | None

def read_source(path: Path) -> Source: ...
def rel_key(p: Path, root: Path) -> str | None: ...
def sha256_range(lines: Sequence[str], start: int, end: int) -> str: ...
def esc_html(s: str) -> str: ...
def cell(text: str, code: bool = False) -> str: ...   # esc_html, then optionally wrap in <code>
def armour_json(text: str) -> str: ...
```

`cell()` is the only way a string reaches a surface the renderer interpolates raw (decision #20b).
Escaping the whole cell instead would render the shipped fixture's `<code>src/pricing/</code>` as
visible `&lt;code&gt;`; markup is added here from a two-tag whitelist and never carried in data.

**`read_source`, in this exact order:**

1. `b = path.read_bytes()`. If `b"\x00" in b[:8192]` → return `Source([], "", False, "not text")`.
   A PNG named `.py` must never reach `ast`.
2. Decode `utf-8-sig` (strips a BOM; byte-identical to utf-8 otherwise).
   On `UnicodeDecodeError` try `tokenize.detect_encoding` for a PEP 263 cookie.
   On failure, `latin-1` with `degraded=True` recorded.
3. `text = text.replace("\r\n", "\n").replace("\r", "\n")` — in that order, explicitly.
4. `lines = text.split("\n")`; if `lines and lines[-1] == ""`: `lines.pop()`.
5. Feed `ast.parse("\n".join(lines))` — the **same normalised str that gets hashed**.

**Never `str.splitlines()`.** It also splits on `\x0b \x0c \x1c \x1d \x1e \x85 \u2028 \u2029`,
desynchronising your index from `ast.lineno`, from git, and from the reader's editor.
Measured: `'a\x0cb\nc\x85d\ne f'.splitlines()` → 6 fragments; `.split('\n')` → 3 real lines.

**Never `open()` or `read_text()` without `encoding=`.** Verified on this box:
`locale.getpreferredencoding(False)` → `cp1252`. Applies to reading source, writing the
HTML output, and decoding subprocess output.

**Why this matters more than it looks:** CRLF is the majority case on this machine
(`core.autocrlf=true`, no `.gitattributes`; 140/161, 93/93, 28/28, 6/7 `.py` files CRLF across
four local repos). Under a naive read, `'import os\r'` is not findable by a model's verbatim
quote and hashes differently — a **100% claim-drop rate**. `restored/` is LF-only and will
never surface it. That is what `tests/repos/hazards/` is for.

**`rel_key(p, root)`** = `p.resolve().relative_to(root.resolve()).as_posix()`, wrapped in
`try/except ValueError` (junction/symlink escape → `None`, file skipped and recorded). Its
output is the **only** permitted value for `files` keys, `anchor.file`, `dropped[].file`,
and `map.nodes[].label`. Never `str(Path)`, `os.path.relpath`, or `os.path.join` —
`verify-contract.js:64` does an exact-string dict lookup and a single backslash reports
`file not bundled` for every anchor in that file.

## 3.2 Root discovery

`repo_root` (what the user pointed at, the anchor namespace) is **separate** from
`import_roots` (sys.path entries, the module-naming namespace). On the proving-ground repo
they differ: repo_root is `restored/`, import_root is `restored/src`.

```python
@dataclass(frozen=True)
class Roots:
    repo_root: Path; import_roots: list[Path]; test_roots: list[Path]
    pyproject: Path | None; declared_packages: list[str]; rule: str

def discover_roots(repo_root: Path) -> Roots: ...
```

Ranked cascade, terminal fallback always succeeds:

1. **Declared.** Find `**/pyproject.toml` *via the pruned walk* (never `rglob` first —
   IMC-Prosperity-4 has 45,698 entries under `.venv`). Take the **shallowest**. `tomllib.load`
   it. Read in order: `tool.setuptools.packages.find.where` → `tool.setuptools.package-dir[""]`
   → `tool.hatch.build.targets.wheel.packages` → `tool.poetry.packages[].from`. Each yields a
   directory relative to the pyproject's parent; a bare `packages = ["volforecast"]` has no
   directory component, so `import_root = pyproject.parent`.
2. `base/src` exists and contains **no** `__init__.py` → `import_roots = [base/"src"]`.
3. `base/src` exists and **does** contain `__init__.py` (src *is* a package) → `[base]`.
4. Any immediate child dir of `base` contains `__init__.py` → `[base]`.
5. Terminal: no `__init__.py` anywhere → every directory containing a `.py` is its own import
   root, module names are bare stems. **When a directory and its parent both qualify, the
   shallowest wins** — otherwise `module_name()` is ambiguous.

**`import_roots` must always include the parent of each `test_root`.** For standard src-layout,
`tests/` sits outside the import root and the entire test tree silently vanishes: measured on
IMC-Prosperity-4, 68 of 161 files (42%) including all 36 tests; on prediction-markets, 49 of 81
and all 43 test files. `restored/` only works by luck — its tests happen to live at `src/tests`.

`test_roots`: `tool.pytest.ini_options.testpaths` resolved against the pyproject's parent, else
any dir named `tests/` or `test/` directly under an import root. Verified: `restored/src/pyproject.toml:79`
declares `testpaths = ["tests"]`.

**Mandatory self-check.** After `build_edges`, if `len(py_in_scope) > 50 and internal == 0`,
raise `SourceRootError` naming every candidate tried and the edge count each produced.

> Measured **under the uncorrected longest-prefix resolver**, which is the cheapest way to
> compare roots: `root=restored/` → **1 edge of 782**. `root=restored/src/volforecast` →
> **0 of 354**. `root=restored/src` → **782**. A wrong root produces a silently empty graph, not
> an error. The corrected classifier of §3.4 reports different absolute numbers on the same root
> — **1854 internal statements / 588 distinct file-level edges** — and those are the numbers to
> check against, never 782.

## 3.3 The walk

`os.walk` with **in-place `dirnames[:]` filtering** — prune at directory level, never
rglob-then-filter. Sort `dirnames` and `filenames` before descending so walk order (and
therefore every id, tie-break and shuffle seed) is stable across machines.

Exclusion set, matched against the directory **name**:

```
.git  .venv  venv  env  .env  node_modules  __pycache__  site-packages
.mypy_cache  .pytest_cache  .ruff_cache  .tox  .nox  build  dist  .eggs
.ipynb_checkpoints  htmlcov  .idea  .vscode  target  vendor  third_party
```

plus `name.endswith(".egg-info")`. Also exclude the resolved output path (`--out`), so a
second run does not survey its own 76 KB HTML.

Two scopes recorded: `files_all` (every text file, for the ext census and the doc-only-dir
list) and `py_in_scope` (`.py` under an import root — the only files parsed, named, mapped
or anchored). Surface `walk.excluded_dirs` in the audit ledger so the exclusion is visible.

`.gitignore` honouring is **cut** — the static list covers every repo measured on this machine.

## 3.4 Module mapping and the import classifier

This is the correctness centre of stage 1.

```python
@dataclass(frozen=True)
class ImportRef:
    base: str; name: str | None; level: int; line: int
    @property
    def dotted(self) -> str:            # base is ALREADY absolute — see below
        return f"{self.base}.{self.name}" if self.name else self.base

def extract_imports(source: str, module: str, is_init: bool = False) -> list[ImportRef]: ...
def classify_import(ref, module, is_init, known) -> tuple[str, str | None]:
    """-> ('internal'|'dangling'|'external', target_module_or_root)"""
def build_module_index(files, roots) -> tuple[dict[str,str], dict[str,set[str]]]:
    """-> (dotted -> relpath, str(root) -> known-set).  known is PER ROOT."""
```

`parse_imports` and `resolve_import` **keep their signatures and their 8 tests**.
`parse_imports` becomes `[r.dotted for r in extract_imports(...)]` so there is one ast walk.
This is a change to the **caller**, not to those functions — their longest-prefix fallback is
correct for its stated contract and its 4 tests assert it deliberately.

**Relative resolution, corrected for `__init__.py`.** This runs **inside `extract_imports`**, so
every `ImportRef.base` that leaves it is already absolute and `.dotted` needs no `roots`:

```python
parts = module.split(".")
if not is_init:
    parts = parts[:-1]
if level > 1:
    parts = parts[: len(parts) - (level - 1)]
base = ".".join(parts + ([base] if base else []))
```

For a package's `__init__.py`, `level=1` means the package itself, not its parent. `restored/`
has **zero** relative imports (2560 `ImportFrom`, all `level==0`), so generation will never
exercise this — the unit tests are the only guard.

**Classification:**

| Shape | Rule |
|---|---|
| `import a.b.c` | internal iff `a.b.c in known`; else dangling iff `a in known`; else external |
| `from a.b import c` | if `a.b in known`: target is `a.b.c` when that is also known (a real submodule), else `a.b` (a symbol) |
| `from a.b import c`, `a.b` not known | dangling iff `a in known`, else external |

**The `known` set is built PER import root**, so `restored/skills/SECDB_INSPECT/src/inspect.py`
is the module `inspect` only for files under its own root and never shadows stdlib `inspect`
elsewhere. If a top-level name is in both `sys.stdlib_module_names` and `known`, record it in
`stdlib_shadowed`.

**`__init__.py` maps to its PACKAGE's dotted name**, never `pkg.__init__`.

**Node ids and file keys derive from the repo-relative POSIX path, never from the dotted name.**
Dotted names collide — measured `inspect` twice in `restored` — and a collision silently merges
two unrelated modules into one node, while `verify-contract.js` only checks duplicate *stop* ids.

> **Why this is not optional.** Measured on `restored/src` with the corrected classifier:
> **internal 1854 / dangling 706 / external 1922**, 588 distinct file-level edges. The existing
> longest-prefix resolver alone reports 2557 internal of which **700 (27.4%) are phantom** — it
> re-points `volforecast.cli.ingest_iv.register` at `volforecast.cli` even though
> `volforecast/cli/ingest_iv.py` does not exist on disk. Confirmed: that file is absent.

Dangling targets get a first-class survey field with occurrence counts and sites. Never a node,
never an edge.

## 3.5 Per-file `ast` extraction — one walk, everything at once

```python
def extract_module(path, rel_path, module, is_init) -> dict: ...
```

One `ast.parse`, catching `SyntaxError` **and** `ValueError`. Record
`{path, line, offset, msg}` in `parse_failures`, set `parsed=False`, keep `loc` and the file
entry, **continue**. Never raise. `restored` is 455/455 clean, so this path is exercised only
by `tests/repos/hazards/`.

Collected in the same walk:

- Module docstring, first line, truncated to 200 chars.
- Top-level and one-level-nested `FunctionDef` / `AsyncFunctionDef` / `ClassDef`:
  name, kind, `start = min(node.lineno, *[d.lineno for d in decorator_list])`,
  `end = node.end_lineno`, first docstring line, `public = not name.startswith("_")`,
  arg names, owning class. **Cap at 400 defs per file** (`economic_value.py` is 1439 lines).
- `__all__` if present at module level.
- Entry-point signals: the lineno of a module-level `ast.If` comparing `Name("__name__")` to
  `Constant("__main__")`; linenos of `Call` nodes resolving to `argparse.ArgumentParser`;
  the literal first string argument of every `add_parser(` call.
- `loc = len(lines)`, and a sha1 of the normalised text for the no-git content hash.

**Not collected, deliberately:** a general call graph, type annotations, complexity metrics.

## 3.6 Git churn — three states, literal argv

Every call is `subprocess.run(argv, shell=False, stdout=PIPE, stderr=PIPE, timeout=10)`,
bytes, decoded utf-8/replace. **Check `returncode` on every one.**

```python
@dataclass(frozen=True)
class GitState:
    state: str          # GIT_OK | GIT_UNTRACKED | NO_GIT | GIT_ERROR
    toplevel: Path | None; prefix: str; head: str | None; reason: str
```

State probe, in order:

```python
["git", "-C", root, "rev-parse", "--is-inside-work-tree"]   # rc!=0 or FileNotFoundError -> NO_GIT
["git", "-C", root, "rev-parse", "--show-toplevel"]
["git", "-C", root, "rev-parse", "--show-prefix"]           # -> "hackathon/restored/" (verified)
["git", "-C", root, "log", "-1", "--format=%H", "--", "."]  # empty stdout -> GIT_UNTRACKED
["git", "-C", root, "ls-files", "-z", "--", "."]            # confirm: 0 files (verified)
```

The churn command, `GIT_OK` only:

```python
["git", "-c", "core.quotepath=false", "-C", root, "log",
 f"--since={days}.days", "--pretty=format:%x01%h%x02%an", "--name-only", "--", "."]
```

Three things about that argv, each verified by running it:

1. **`"--"` and `"."` are two separate argv elements.** Passing `"-- ."` as one element gives
   `rc=128, fatal: unrecognized argument: -- .`, which under a returncode-blind implementation
   reads as "no history" — so every `GIT_OK` repo silently reports `churn unavailable` and
   falls back to fan-in. Verified on `restored`: one-arg → 128; two-arg → 0.
2. **The pathspec is mandatory.** Without it, running inside `restored/` returns the enclosing
   ML-GS repo's history at exit 0, naming files that do not exist under the target. Verified:
   no-pathspec → `fb3c3ce feat(deliverables): trailhead demo page …`. That is the worst possible
   failure for a tool whose pitch is that the machine checks the facts.
3. **`-c core.quotepath=false` is mandatory.** `core.quotepath` defaults to true and is unset on
   this machine, so any path with a non-ASCII byte comes back C-quoted (`"caf\303\251.py"`), fails
   the existence check, and is silently dropped from the ranking. Count discards in
   `churn.discarded_paths` and surface the number.

Every returned path is repo-root-relative. Re-anchor: discard unless
`p.startswith(prefix)`; `rel = p[len(prefix):]`; discard unless `(root/rel).exists()` — that
drops deletes and rename ghosts.

**`GIT_UNTRACKED` is the default path for `restored`, not an edge case.** Verified: `rev-parse`
returns `true`, `log -1 --format=%H -- .` is empty, `ls-files -- .` is empty. Emit
`churn.available=false` with the literal reason, `by_file={}`, `substitute="fan_in"`.

**`repo.commit` when churn is unavailable:** `"nogit-" + sha1(sorted (relpath, size, sha1-of-text)
tuples of every in-scope file)[:8]`. It must genuinely change when the tree changes — localStorage
is keyed `trailhead:<name>:<commit>` and progress must reset on a real regeneration.

**The one seed.** Every shuffle in the generator — checkpoint options, distractor sampling —
uses `random.Random(repo.commit)`, constructed once and passed down. `--seed` is cut (§10), so
this is the only source of randomness, and it is a function of the tree. Two runs of the same
tree produce byte-identical option orders, and therefore identical answer indices and an
unchanged localStorage contract. Name it in the checkpoint `provenance` string.

**mtime is not a churn substitute.** Measured: 307 of 455 `.py` in `restored` share one mtime day
across only 10 distinct days. Tertiary tie-break at most, never under the label "churn".

**Fan-in substitute ranking:** score = fan-in from `edges`, excluding package `__init__.py`
files **unless `loc >= 20`**. Measured: `volforecast/__init__.py` has fan-in 92 at 8 loc;
`pipeline/__init__.py` 32 at 5; `data/__init__.py` 19 at 1. An unfiltered ranking shows five
near-empty files. Ties broken by loc desc, then path.

## 3.7 Entry points — ranked by confidence, each citable

```python
def entry_points(roots, files, fan_in) -> list[dict]: ...
def toml_line(lines, table, key=None) -> int | None: ...
```

| Rank | `kind` | Signal | Provenance string |
|---|---|---|---|
| 1 | `console_script` | pyproject `[project.scripts]` / `[project.gui-scripts]` / `[tool.poetry.scripts]` | `src/pyproject.toml [project.scripts]` |
| 2 | `console_script` | `setup.py` `entry_points` console_scripts (regex; skipped when absent) | `setup.py:<n>` |
| 3 | `module_main` | `<pkg>/__main__.py` for each declared package | `<relpath> exists — python -m <pkg> runs it` |
| 4 | `http_route` | module-level assignment to a `Call` of FastAPI / Flask / Typer / `click.Group` | `<relpath>:<n>` |
| 5 | `main_guard` | module-level `if __name__ == "__main__"` **inside an import root**, ranked by fan-in, capped at 5 reported | `<relpath>:<n>` |

Verified on `restored`: rule 1 gives `volforecast = "volforecast.__main__:main"` at
`src/pyproject.toml:53`. Rule 3 gives `src/volforecast/__main__.py`. Rule 4 gives **zero**
(0 click, 0 typer, 0 fastapi, 0 flask) — it exists so a second repo works and it is item 2 on
the cut list.

**Scoping matters enormously.** Unscoped, `if __name__` reports **91 candidates** on `restored`
(36 in `skills/`, 48 in `workspace/`, 40 of which use `sys.path.insert` and are statically
unresolvable). Scoped to import roots it reports the correct **6**.

Do **not** implement the repo-specific `def register(subparsers)` convention. The generic
equivalent is the literal string argument of `add_parser(`, which yields 22 real subcommand
names here and works on any argparse repo.

`toml_line`: `tomllib` returns no line numbers. After parsing, scan the normalised lines for the
first stripped line equal to `[<table>]`, then the first following line matching `^<key>\s*=`.
Fall back to the table header line. If neither is found, the derived claim is emitted as
`inferred` with **no anchor** rather than guessed.

## 3.8 Command discovery — candidates with provenance

**Survey does not execute anything.** It emits candidates with a canonical `cmd` string.

```python
def command_candidates(roots, files, text_files, interp: str) -> list[dict]: ...
```

The `cmd` string is **canonical and load-bearing**: `commands.json` records runs by `cmd`, and
`verify.py` merges command blocks by `(cmd, cwd)`. One string, three producers. Derive `argv`
from `cmd`, never the reverse; store `argv` as an additive sibling key.

| # | `kind` | `cmd` | `cwd` | Source |
|---|---|---|---|---|
| 1 | `run` | `python -c "import <pkg>"` | import root | pyproject packages declaration |
| 2 | `run` | `python -m <pkg> --help` | import root | pyproject `[project.scripts]` |
| 3 | `test` | `python -m pytest --collect-only -q <testpaths>` | pyproject parent | `[tool.pytest.ini_options] testpaths` |
| 4 | `lint` | the `entry:` of a `.pre-commit-config.yaml` local hook | repo root | `.pre-commit-config.yaml:<n> hook <id> entry` |

`.pre-commit-config.yaml` and `.github/workflows/*.yml` are scraped with a **line regex, not a
YAML parse** — PyYAML is a dependency and it destroys the line numbers that are exactly what the
provenance string and the anchor need. Regex: `^\s*entry:\s*(.+)$` with the nearest preceding
`^\s*-?\s*id:\s*(.+)$`; and `^\s*(- )?run:\s*(.+)$` with the nearest preceding `working-directory:`.

**Interpreter resolution.** Never bare `python` — verified on this box it is the Microsoft Store
shim and fails outright. Resolve **once per repo**, in order: `<repo>/.venv/Scripts/python.exe`
→ `<repo>/.venv/bin/python` → `shutil.which("python3")` → `shutil.which("python")` → `sys.executable`.
Store the absolute path on the candidate; the display `cmd` says `python`.

**Probe before admitting a pytest candidate.** Verified: `py -3.11 -c "import pytest"` →
`ModuleNotFoundError`; `py -3.12` has pytest but no torch. If `import pytest` fails under the
resolved interpreter, emit the candidate with `allowed=false, deny_reason="pytest not importable
under the resolved interpreter"` so §9 can list it as considered.

Cut, deliberately: Makefile/justfile targets, the platform CLI wrapper, the bare `pytest`
fallback, the CI workflow scraper. They are cut-list items 3–6.

## 3.9 Signatures

`files` throughout is `list[dict]` — the per-file results of `extract_module`, which is the only
structure carrying linenos, sizes and hashes. **Nothing downstream takes `modules`** (the
directory-level rollup) where it needs per-file signals; that was the original bug in this list.

```python
def discover_roots(repo_root: Path) -> Roots
def walk_files(roots: Roots, out_path: Path | None) -> dict
def module_name(rel_path: str, roots: Roots) -> tuple[str | None, Path | None, bool]
    """-> (dotted | None, import_root | None, is_init)"""
def build_module_index(files, roots) -> tuple[dict[str, str], dict[str, set[str]]]
def extract_imports(source: str, module: str, is_init: bool = False) -> list[ImportRef]
def classify_import(ref, module, is_init, known) -> tuple[str, str | None]
def extract_module(path: Path, rel_path: str, module: str, is_init: bool) -> dict
def build_edges(files, index, known_by_root) -> dict
    """-> {"edges": [...], "internal": int, "dangling": [...], "external": int}
       `internal` is what the §3.2 self-check reads."""
def git_state(repo_root: Path) -> GitState
def git_churn(repo_root: Path, st: GitState, since_days: int) -> dict
def repo_id(st: GitState, files: list[dict]) -> dict
def entry_points(roots, files, fan_in) -> list[dict]
def command_candidates(roots, files, text_files, interp: str) -> list[dict]
def survey(repo_root: Path, *, since_days: int = 365, out_path: Path | None = None) -> dict

class SourceRootError(Exception): ...
```

---

# 4. Stage 2 MAP

Every number here is final — there is **no layout engine in the page** and the viewBox is
hard-coded `0 0 900 400` with a decorative ruler at y = 381–392.

```python
MAP_CAP = 14
W, H     = 900.0, 400.0
X_PAD    = 8.0
Y_TOP, Y_BOT = 10.0, 368.0
BAND     = Y_BOT - Y_TOP        # 358.0
COL_GAP  = 26.0
ROW_GAP  = 13.0
EDGE_CAP = 48
W_MAX    = 300.0                # node width clamp — see §4.2 step 1
H_BASE, H_DIV = 44.0, 6.0       # THE renderer's rect height. Read from here, never inlined.
```

`H_BASE` and `H_DIV` mirror `demo/trailhead-demo.html:1731`, `const h=n=>44+Math.sqrt(n.loc)/6;`
**verbatim**. Every height in this section — the packing, the invariant, the tests — calls
`node_h`, which is the only place those two constants appear. An inlined literal here is how the
layout reserves less than the browser draws and the invariant passes while the map clips.

## 4.1 Collapse

1. **Test roots collapse to one node, always, before anything else.** Measured: depth-2 on
   `restored/src` gives 26 groups of which 13 are loose `tests/*.py`; forcing tests to depth 1
   gives 14 groups — 13 `volforecast` + 1 `tests`, which is the right architecture picture.
2. **Adaptive depth** for everything else: start at `d=1`, increase while the group count still
   grows and stays `<= cap*2`. A fixed depth is wrong at both ends — depth 1 on `restored/src`
   gives 2 useless nodes, depth 3 gives 331.
3. **Merge-smallest, unconditionally**, while any group has `file_count == 1` and a mergeable
   parent, *and* while `count > cap`. Take the group with the smallest `(files, loc, key)`,
   pop it, re-file its members under `key[:-1]`. Running it only above the cap is a measured
   no-op on `restored` (14 groups < cap 24 under the old design) and leaves 2 of 14 slots spent
   on single files — one of them an 8-line `__init__.py`.
4. **Scope is the declared distribution packages plus the test root.** Adding `restored/skills/`
   gives 42 nodes with 3 edges and 38 isolated islands.
   **When `roots.declared_packages` is empty**, scope instead to every directory under an import
   root holding at least one in-scope `.py`, at the adaptive depth, plus the test root. Without
   this fallback the scope is empty on `flat_script`, `no_entry`, `qrt` and `ryanatron-v2` — two
   of four fixture repos and two of three real acceptance repos — so `map.nodes` is `[]`, §9 row 4
   fires everywhere, and the map is never exercised on a repo with real git history.
   Expected under the fallback: `qrt` → 1 node (`<3`, row 4 correctly fires); `ryanatron-v2` →
   3 nodes (`.`, `cogs`, `utils`) and a real graph. §11.2 checks those two numbers.

**Node identity:** `id = slug("n-" + repo-relative POSIX path)`, deduped with a numeric suffix.

**Label = the group's path relative to its IMPORT ROOT** — `data`, `models`, `cli`, `tests`,
not `volforecast/data`. This is not cosmetic: label length sets `w`, and `w` sets the column
count. `volforecast/visualization` (25 ch) needs `w≈195` → 4 columns; `visualization` (13 ch)
needs `w≈142` → 5 columns. Label choice **is** the layout algorithm. Sanitise to
`[A-Za-z0-9_./+-]` — the renderer interpolates `n.label` into SVG `<text>` unescaped, and
malformed SVG breaks the whole map rather than one cell.

**Edges:** sum file-level multiplicities between distinct groups; drop self-edges;
`n = min(raw, EDGE_CAP)`. Stroke width is `0.7 + n/16` with **no clamp in the renderer** — a raw
214 draws a 14 px band across a 400-unit canvas. State the cap in the map stop caption.

## 4.2 Layout — step by step

```python
def node_w(label, loc, files) -> int:
    stats = f"{loc:,} loc · {files} files"
    return math.ceil(min(W_MAX, 22 + max(6.9 * len(label), 6.0 * len(stats))))

def node_h(loc) -> float:
    return H_BASE + math.sqrt(loc) / H_DIV    # == the renderer's h(). We RESERVE exactly this.
```

1. **Widths** via `node_w`. The renderer draws the label at `600 11.5px mono` and the stats at
   `10px mono`, both starting at `x+11`, and clips neither. The shipped fixture's `risk` node
   already overflows by ~5 px under this formula. **The `W_MAX` clamp is not decoration:**
   without it a single long label makes `max_w > 442`, no `C` satisfies step 2, `Cmax` falls to 0
   and both the `colw` walk and the `x + w <= 900` invariant break. When the clamp bites,
   middle-ellipsise the label to fit and keep the full name in `node.why` and the drawer `<h4>`.
2. **Column capacity:** `Cmax = max(1, max C such that (C+1)*max_w + C*COL_GAP <= 884)`.
   The `max(1, …)` is the floor that makes step 4 total.
3. **Order.** Sort nodes ascending by `(fan_in - fan_out, -loc, id)`. A pure importer
   (high fan_out, zero fan_in) is most negative and sits leftmost; a pure library is most
   positive and sits rightmost. This is mandatory: edges are drawn from `a.x + a.w` to `b.x`
   and **`a` imports `b`**, so a right-to-left edge backtracks into a horizontal S.
4. **Columns.** Heights include the gaps they will need, or the packing under-reserves:

   ```python
   C_min = max(1, math.ceil((sum(h) + (N - 1) * ROW_GAP) / BAND))
   ```

   Then **walk `C` from `C_min` up to `Cmax` and take the first whose gutter (step 5) is
   `<= 3 * COL_GAP`; if none qualifies, take `Cmax`.** Without the widening walk, `restored`'s
   12 nodes give `C_min = 3` and a 223 px gutter between 142 px nodes — technically valid, and it
   looks like a bug. With it, `C = 4` and the gutter is 103 px.
   For each candidate `C`: walk the ordered list, opening a new column when
   `acc > 0 and acc + h > target*1.02 and c < C-1`, where `target = sum(h) / C`.
   Greedy height-balanced line-break.
5. **Place.** `colw[c] = max width in column c`.
   **`gap = 0.0 if C < 2 else (W - 2*X_PAD - sum(colw)) / (C - 1)`.** The `C-1` guard is not
   optional: any repo whose module graph has **no internal edges** gives `C=1` and a bare
   division raises `ZeroDivisionError`. Reproduced on `qrt` (7 loose `.py`, 0 internal
   references) — which is a named acceptance repo — and on `IMC-Prosperity-4/src/round0`.
   Centre each node within its column's width. Vertically per column, **with the same guard,
   for the same reason** — the greedy line-break routinely leaves the last column holding one
   node:

   ```python
   rg = (ROW_GAP if sum(h) + (n - 1) * ROW_GAP <= BAND
         else max(2.0, (BAND - sum(h)) / max(1, n - 1)))
   ```

   Centre the block over `[Y_TOP, Y_BOT]`. Round `x`, `y` to int.
6. **Overflow.** If no `C <= Cmax` fits (`sum(h) + (n-1)*2 > BAND` in some column at every `C`),
   merge the smallest groups (§4.1 rule 3) and re-pack until it does; record the count in
   `diagnostics.density_merges`. This is the only path by which `build_map` may reduce the node
   count below what collapse produced, and it must never raise — `MAP_CAP = 14` makes it
   unreachable on every repo measured, but an unfamiliar repo at hour 8 is not the place to
   discover an assertion.
7. **Emit only edges with `col[b] >= col[a]`.** Count the rest in
   `diagnostics.edges_dropped_backward` and state the number in the map stop caption. Measured
   on `restored`: 9 back edges among 14 nodes with column deltas `[-2,-2,-1,-1,-1,-1,0,0,0]`;
   a `-2` edge runs 626 px right-to-left across a 900 px canvas, crossing a column and both
   gutters, and reads as a horizontal band.

**SCC condensation is rejected** — measured, it swallows 8 of the 13 `volforecast` subpackages
into one blob labelled `cli +7` and destroys the map.

## 4.3 Hard invariants — assert in code and in tests

```
0 <= x  and  x + w <= 900
0 <= y  and  y + node_h(loc) <= 372               # clears the ruler at 381–392
no two rects overlap                              # using node_h, never a literal
every edge endpoint names an emitted node
every node has all 9 fields: id label loc files x y w why top
len(node["top"]) >= 1
```

**Both height invariants call `node_h`.** Asserting an inlined formula that under-reserves is
worse than not asserting: it passes in Python while the browser clips, which is exactly the
failure mode §15 risk 4 claims to have mitigated.

`why` and `top` are **deterministic templates**, not model prose (decision #19):

```python
why  = (f"{files} files, {loc:,} loc. Imports {out_n} of these; imported by {in_n}. "
        f"Busiest file: {basename} ({rank_label} {k}).")
top  = [f"{basename} — {rank_label} {n}" for … ][:3]
```

`rank_label` is `"commits"` when `churn.available`, else `"fan-in (no git history)"`. The
drawer's heading is hard-coded `MOST-EDITED FILES` in the renderer, so **the substitution must
be visible inside the strings** or the page states a falsehood on every one of the 10 node
drawers.

**`top` is never empty.** Rank unfiltered, drop sub-20-loc `__init__.py` files, and **if the
result is empty fall back to the unfiltered ranking**. The group keyed `volforecast` on
`restored` contains exactly one module — an 8-line `__init__.py` with the highest fan-in in the
repo (92). Under a bare exclusion its `top` is `[]`, and that node sits at the far right of the
map (most depended on), so it is the first one a judge clicks — rendering an empty
`MOST-EDITED FILES` heading.

## 4.4 Fewer than 3 nodes

`build_map` sets `render="table"`. The generator then emits a `table` + `callout level="info"`
**instead of** a `graph` block. `map.json` still carries `{"nodes": [], "edges": []}` because
`verify-contract.js:167` does `D.map.nodes.map(...)` unconditionally. The renderer will happily
draw a one-node map and has no degradation logic of its own.

Note this substitutes a different artifact from the one spec §6 row 4 names: the spec's "text
fallback list" is the `<details class="fallback">` *inside* `graph()`, so omitting the graph block
omits the fallback too. A real table with path/files/loc/imports beats a `<details>` nobody opens.
Amend spec §6 row 4 to say so (stage 0 item 4).

## 4.5 Signatures

```python
def collapse(sv: dict, cap: int = MAP_CAP) -> tuple[dict, dict, dict]
def node_w(label: str, loc: int, files: int) -> int
def node_h(loc: int) -> float          # H_BASE + sqrt(loc)/H_DIV. The ONLY height definition.
def order_nodes(ids, fan_in, fan_out, loc) -> list[str]
def pack_columns(order, heights, widths, C: int) -> dict[str, int]
    """Balance into exactly C columns. Called once per candidate C by the step-4 walk."""
def place(col, order, widths, heights) -> dict[str, dict]
def build_map(sv: dict, cap: int = MAP_CAP) -> dict
```

---

# 5. Stage 3 NARRATE

The **only** stage that touches a model. Everything in `compose.py` is deterministic; the model
is reached only through `provider.py`.

## 5.1 The rule that makes the project work

> **Never ask the model for a line number. Ask it to quote.**

Feed files with line numbers pre-pended, require the verbatim snippet, resolve the range in
Python. Models count badly and copy well. This is the difference between a 40% drop rate and ~3%.

Enforced three ways, in descending order of strength:

1. **The JSON schema has no line-number field**, and `additionalProperties: false`.
2. The parser **rejects** any response with a key in `cite` that is not one of `file`, `quote`,
   `focus` — rejects, never repairs. A parser that patches model output is a model verifying
   itself with extra steps. Scope the check to **key names**, as `check-fixtures.js:80` already
   does; a digit scan over the quote text rejects most true responses, since `argv[1]`,
   `timeout=60` and `version = "0.3.1"` are all legitimate content.
3. `check-fixtures.js` already asserts `content carries NO line numbers (non-negotiable #7)`.

## 5.2 `provider.py` — the interface

```python
class Provider(Protocol):
    def complete(self, system: str, user: str, schema: dict) -> dict: ...

class StubProvider:      # DEFAULT
    def __init__(self, directory: Path): ...   # .trailhead/narration/<key>.json; miss -> {"claims": []}

class ClaudeProvider:
    def __init__(self, *, model: str = "claude-opus-5",
                 base_url: str | None = None, max_tokens: int = 16000): ...
```

`ClaudeProvider` notes, each load-bearing:

- `output_config={"format": {"type": "json_schema", "schema": SCHEMA}}`.
- **`max_tokens=16000`, not 8000.** On `claude-opus-5` thinking is adaptive and **on by default**,
  and it shares the `max_tokens` budget with the response. A truncated response is invalid JSON,
  so the unit drops — and the worst case is the `trace` unit, which returns 6 hops each with a
  sentence plus a multi-line quote from a different file.
- **Check `response.stop_reason` before `json.loads`.** `max_tokens` and `refusal` both return
  HTTP 200 with content that will not satisfy the schema. Treat each as a parse failure with its
  own ledger reason, not as an exception.
- **No `temperature` / `top_p` / `top_k`** — rejected with a 400 on Opus 5. Determinism comes
  from the disk cache, not from sampling parameters. Say that plainly on the slide.
- `base_url` from `TRAILHEAD_BASE_URL` is the GS gateway swap point. Filling in the approved
  internal endpoint is one env var and zero code above the protocol.

## 5.3 The unit of work

One call per **stop-unit**, not per module and not per claim.

| Unit | Claims | Notes |
|---|---|---|
| `five` | 5 | Claims 1–4 must verify; claim 5 ("what it is not") is expected `inferred` and that is correct |
| `trace` | 8 | **One call carrying all hops** so the model sees the chain. One claim per hop of §5.7's hop list — the two counts are the same number or a hop renders `esc(undefined)` |
| `conv` | 4 | Every claim **forced** to `inferred` in code (spec §3 stop 13) |
| `green` | 2 | Only if a passing command exists — precondition, see §9 |

**4 units for `restored`.** There is no `hyp:` unit — `command.hypothesis` comes from
`runner.classify_failure`'s rule table (§8.5, decision #26). Hard cap `--max-units 12`; overflow
drops in reverse priority **`conv` → `green` → `five` → `trace`**, matching §14's stop-cut order,
and the affected stop falls back to its template blocks. `trace` is last because it carries beat 4
of the pitch.

Cut before hour 0 (decisions #19, #20, #26): the 10 `map:<node>` units, the `where` unit and the
three `hyp:` units. `node.why`, the table's purpose column and every `hypothesis` are
deterministic.

Serial, not concurrent. `ThreadPoolExecutor` buys ~90 seconds once, on a run the disk cache
makes free for every rehearsal, in exchange for partial-failure handling, result ordering and
Ctrl-C behaviour.

## 5.4 Context packing — `prompts.py`

```python
@dataclass(frozen=True)
class Window:  file: str; start: int; end: int

def pack(unit, survey, root) -> tuple[str, str, tuple[Window, ...]]: ...
    """-> (system, user, QUOTABLE windows).  Quotable ⊂ shown: rule 5 excludes
       lines 1–12 of every file, which are still SHOWN for orientation."""
def number(lines, start, end) -> str: ...
```

The two window sets are different and both matter: the resolver arbitrates against **quotable**
windows, while §6.1's cross-file check reads the **shown** snapshot. `pack` returns the quotable
set; the shown set is the snapshot `narrate` already holds to build the text.

1. A deterministic **facts block** from `survey.json` — repo name, file counts, package list,
   entry points, dangling-import count, churn availability, per-module fan-in and loc. Plain text
   the model may rely on but must **not** quote; it is already verified by construction.
2. **Source windows.** Per selected file: a **hot window** of ≥30 contiguous lines centred on the
   highest-fan-in public function's `lineno`, plus skeleton fragments of **≥5 lines each**
   (signature + docstring + first 3 body lines) for other top-level defs. Merge overlapping ranges.
   Accumulate to `max_lines=900` (~12k tokens).
3. Render with a fixed-width gutter, `f"{n:5d}| {line}"`, preceded by `--- <repo-relative path> ---`,
   ranges separated by a bare `   ...` line. Leading indentation after `| ` is byte-preserved —
   indentation is the main disambiguator and must survive the round trip.
4. **Record every emitted `(file, start, end)`.** This is handed to the resolver and is the
   strongest anti-hallucination check available: a quote that resolves outside what we showed
   was not copied.
5. **Exclude lines 1–12 of every file from the quotable window set** (still show them as
   orientation). Measured: `from __future__ import annotations` / blank / `import logging` is
   3 lines and 44 non-space chars — it clears every quality floor and appears verbatim at lines
   1–3 of **20 files** under `restored/src/volforecast/cli/`. 17 distinct 3-line head spans
   across the 139 files of `volforecast` clear the floor and appear in more than one file.

**Never feed whole files.** `models/xgboost.py` is 1477 lines, `economic_value.py` 1439.

## 5.5 The output schema

```json
{ "type": "object", "additionalProperties": false, "required": ["claims"],
  "properties": { "claims": { "type": "array", "items": {
    "type": "object", "additionalProperties": false,
    "required": ["text", "status", "cite"],
    "properties": {
      "text":   { "type": "string" },
      "status": { "type": "string", "enum": ["verified", "inferred"] },
      "cite":   { "type": "object", "additionalProperties": false,
                  "properties": { "file":  { "type": "string" },
                                  "quote": { "type": "string" },
                                  "focus": { "type": "array", "items": { "type": "string" } } } }
  } } } } }
```

`cite.focus` is an **array of substrings of `quote`**, never line numbers — non-contiguous focus
is normal (line 63 and 65 matter, 64 doesn't).

**Hand validation after parsing**, because a schema guarantees shape and never truth:

- Reject the response if `claims` is absent or not a list.
- Truncate to `unit.max_claims` — never error.
- Reject a claim whose `text` is empty, >280 chars, or contains `` ` ``, `\n`, `<`, or `](`.
- `status == "inferred"` → **force `cite` absent**, discarding whatever came back.
- `status == "verified"` with no `cite`, or with an empty `quote` → **drop the claim entirely**,
  one ledger row, no claim in `tracks`. Never both — a claim id appearing in `tracks` *and*
  `dropped` is the one cross-check (`verify-contract.js:131`) the contract doc calls the failure
  that would discredit the entire pitch.
- Any `focus` string that is not a substring of `quote` → drop the focus, keep the claim.
- `unit.kind == "conventions"` → override **every** returned status to `inferred`. Enforced in
  code, not in the prompt, so the quarantine holds even if the prompt drifts.
- Quote longer than **24 lines** → reject with `quote longer than the anchor cap`.

One retry per unit on a parse failure. Second failure: zero claims, one ledger row
`model returned unparseable output` (with a real `id`, `text` and `file` — the ledger table reads
all four and the gate checks only `reason`), and the stop renders from its template blocks.

## 5.6 Which stops are model-written, template, or survey-derived

| Stop | Prose | Numbers / structure | Answer key |
|---|---|---|---|
| `cover` | template | survey | — |
| `five` | **model**, 5 claims | — | — |
| `map` | template (`node.why`) | survey + map geometry | — |
| `where` | template (`__init__` docstring) | survey | — |
| `cp-a` | — | — | **survey only** |
| `setup` | template + `runner.classify_failure`'s `hypothesis`, always `inferred` | runner: real exit, out, timings | — |
| `green` | **model**, 2 claims | runner | — |
| `trace` | **model**, one call, 8 hops | hand-specified hops + anchors | — |
| `cp-c` | — | — | **survey (map-derived, merged in stage 2)** |
| `conv` | **model**, all forced `inferred` | — | — |
| `audit` | template | report + ledger | — |

Anything a checkpoint grades against, anything numeric, anything that becomes an anchor's line
range, and anything that becomes a permutation key is **survey-derived**. A model cannot verify
itself and a model-supplied answer key makes the quiz meaningless.

**Ledes, titles and callout text are deterministic templates too** (decision #20c). They are
factual sentences on a surface with no claim marker, so no model string may reach them.

**Trace hops need a fallback.** The renderer draws a trace `claim` inside a `.claim` span with
no marker and no `INFERRED` tag — visually verified, with no way to mark one inferred. So if a
hop's model claim fails verification, the hop **keeps its survey-derived anchor** and its `claim`
is replaced by a deterministic template sentence; the failed model claim goes to the ledger. A
trace hop is therefore never blank and never carries an unverifiable sentence dressed as verified.

## 5.7 `compose.py` — the STOP_TABLE

Deterministic. Genericity is a data question here, not a control-flow question.

```python
@dataclass(frozen=True)
class Ctx:
    survey: dict            # survey.json, post stage-2 checkpoint merge
    map: dict               # map.json
    commands: dict          # commands.json — CommandResult / SkippedCommand records
    narration: dict         # unit id -> parsed claims (may be {} on a stub miss)
    hops: list[dict]        # fixtures/trace.restored.json, or [] for an unknown repo
    rng: random.Random      # seeded on repo.commit (§3.6)

@dataclass(frozen=True)
class StopSpec:
    id: str; title: str; track: str; minutes: int; kind: str
    precondition: Callable[[Ctx], str | None]   # -> reason if unmet
    build: Callable[[Ctx], list[dict]]
    on_fail: str                                # PLACEHOLDER | ALTERNATE | DROP
```

**`STOP_TABLE`, with the exact block sequence each builder emits.** Verified against
`fixtures/verified.sample.json` — these are the shapes the renderer and both gates already accept,
so matching them is free and deviating from them is not.

| Stop | Track | min | kind | Blocks, in order | Builder |
|---|---|---|---|---|---|
| `cover` | ORIENT | 2 | stop | `callout` · `table` (FIELD/VALUE) | `build_cover` |
| `five` | ORIENT | 4 | stop | `prose` (5 claims) · `callout` | `build_five` |
| `map` | ORIENT | 5 | stop | `graph` · `prose` | `build_map` |
| `where` | ORIENT | 4 | stop | `table` (PATH/PURPOSE/FILES/LOC/rank/committers) | `build_where` |
| `cp-a` | ORIENT | 3 | cp | `checkpoint` (cp-a1) · `checkpoint` (cp-a2) | `build_cp` |
| `setup` | RUN | 8 | stop | `command` × n · `callout` | `build_setup` |
| `green` | RUN | 4 | stop | `command` · `prose` · `callout` | `build_green` |
| `trace` | READ | 12 | stop | `trace` · `callout` | `build_trace` |
| `cp-c` | READ | 4 | cp | `checkpoint` (cp-c1) · `checkpoint` (cp-c2) | `build_cp` |
| `conv` | CONV | 8 | stop | `callout` · `prose` | `build_conv` |
| `audit` | AUDIT | 6 | stop | `callout` · `ledger` | `build_audit` |

```python
def build_<stop>(ctx: Ctx) -> list[dict]: ...      # one per row above
def build_course(ctx: Ctx) -> list[dict]: ...      # -> tracks[], applies preconditions
```

`track.minutes` is a **constant on the track spec**, not the sum of its stops — the shipped
fixture has ORIENT at 15 against a stop sum of 18. It is a rounded reading estimate and the rail
shows it verbatim.

**`excerpt` blocks are not emitted by any builder.** The renderer supports the type and
`verify-contract.js:99` checks its anchor, so the payload walk in §6.5 must still cover it; but
nothing in this plan produces one, and `excerpt.caption` therefore has no producer by design.

Every stop emits `kind` (`"stop"` or `"cp"`) and `minutes`; every track emits `minutes`.
**Neither gate checks any of them**, and the rail shows `undefinedm` and checkpoints tick
themselves off without them. `stop.kind == "cp"` is load-bearing: a stop not marked `cp` is
auto-marked complete the instant it is drawn.

**`lede` is required on every stop with `kind == "stop"`, and omitted on `cp` stops.** That is
what the frozen fixture does (`cp-a` and `cp-c` carry no `lede`) and the renderer treats it as
optional (`${s.lede?…:""}`). A self-police rule demanding one everywhere rejects the reference
payload.

**Trace-block field rules**, all deterministic, all in `build_trace`:

- `steps[i].next` — emitted on every hop but the last, as `f"{next_symbol} in {next_file}"` from
  the next hop's survey data. Matches the fixture's `"build_instrument in src/instruments/factory.py"`.
  The renderer prints `next → <b>${s.next}</b>` and falls back to "response leaves the process".
- `steps[i].predict` — emitted **only** when `i < len-1`, `steps[i+1].anchor.file != steps[i].anchor.file`,
  **and** no earlier hop already carries a predict for this file. The first two conditions are
  `verify-contract.js:110`; the third is the renderer, which keys prediction state as
  `pid = "pt:" + s.anchor.file`, so two predicts in one file collide on one localStorage slot.
  On Appendix A.3's hop list that admits hops 1, 3, 6 and 7.

**The `green` stop when there is no test command.** On `restored` both the `green` narrate unit
and §9 row 2 fire: `python -c "import volforecast"` passes, and no `kind=test` candidate is
admitted because pytest is not importable. The rule, in `build_green`:

1. An admitted `kind=test` command that passed → narrate it. This is the happy path.
2. Else any command that passed → render it under a caption that says plainly it is an **import
   smoke check, not a test suite**, and emit row 2's callout **above** it naming the denied
   pytest candidate and its deny reason.
3. Else → row 2's callout alone, and the `green` unit is not built.

That is the honest reading of spec stop 6 and the better demo beat: the page shows a green
command and states in the same breath that it is not the thing you wanted.

**Never emit a stop with an empty `blocks` array** — the renderer and the gate both TypeError
rather than degrade.

**The `audit` stop is not skippable and not filterable.** Hard-guard it in `build_course`.
Verified: stripping every `ledger` block from the fixture leaves `verify-contract.js` exiting 0
with `ALL CHECKS PASS`, so nothing mechanical stops a ledger-less page. That is the never-cut
list made real.

## 5.8 Caching and determinism

Cache key = `sha256((system + "\x00" + user).encode("utf-8"))` — both halves of what `pack`
returns, so a system-prompt edit invalidates too. The prompt already contains the evidence and any
prompt edit changes its bytes, so version-bumping is automatic — no `PROMPT_VERSION`, no
separate evidence fingerprint. Stored as `.trailhead/narration/<key>.json`. A hit makes zero
calls. **`StubProvider` reads the same directory under the same key** — record and replay must
agree or replay never hits. A stub miss returns `{"claims": []}`; `--offline` turns a miss into a
hard error.

---

# 6. Stage 4 VERIFY

Deterministic, no model. Strictly test-driven — write the failing test first.

## 6.1 `resolve.py` — the quote → line resolver

The highest-risk function in the project. It is deliberately brittle: **every fuzzy fallback is
rejected as a drop**, because a fallback that can land in the wrong place is the exact failure
the pitch claims to have eliminated.

```python
def resolve(quote: str, lines: list[str], *,
            windows: Sequence[tuple[int, int]] | None = None,
            min_lines: int = 2, max_lines: int = 24,
            min_payload: int = 40) -> tuple[tuple[int, int] | None, str | None]:
    """-> ((start, end), None) 1-based inclusive, or (None, reason).
    Never raises. Never guesses."""
```

**Normalisation, in this exact order.** Every rule is one that *cannot* change which occurrence
matches.

1. `quote.replace("\r\n","\n").replace("\r","\n").split("\n")` → `q`.
2. **Gutter strip:** if **every** non-blank line of `q` matches `^\s*\d+\s*\|\s?`, remove that
   prefix from every line. If only *some* match, leave all alone — a partially mangled quote
   must not be silently repaired.
3. Pop leading and trailing wholly-blank lines from `q`; keep interior blanks.
4. `rstrip()` every line of `q`.
5. `rstrip()` every line of the haystack. **Left-side whitespace is never touched on either side.**

**Guards.** `len(q) < min_lines` → `quote shorter than two lines`.
`len(q) > max_lines` → `quote longer than the anchor cap`.
`len(re.sub(r"\s","", "".join(q))) < min_payload` → `quote too thin to be unique`.

**Exact scan.** `k = len(q); hits = [i for i in range(len(H)-k+1) if H[i:i+k] == q]`.
That is the only matching operation in the function.

**Window arbitration — narrows, never relocates.**

| Condition | Result |
|---|---|
| exactly one hit inside a shown window | resolve to it |
| more than one hit inside shown windows | `snippet ambiguous`, detail = count |
| zero inside, but hits exist elsewhere | `snippet resolved outside the excerpt shown to the model` |
| no windows given, zero hits | `snippet not found verbatim in file` |
| no windows given, >1 hit | `snippet ambiguous`, detail = count |

**Cross-file check.** `resolve()` takes one file. The wrapper that loops over the unit's snapshot
is the one that produces the wrong-file reason, and it needs its own signature and an **explicit
precedence** — two orderings give two different ledger strings for the same failure, and the
ledger is the pitch:

```python
Snapshot = Mapping[str, tuple[list[str], tuple[tuple[int, int], ...]]]   # file -> (lines, quotable windows)

def arbitrate(cite: dict, snap: Snapshot) -> tuple[Anchor | None, str | None]: ...

def verify_claim(claim: dict, snap: Snapshot,
                 sources: Mapping[str, Source]) -> tuple[dict | None, dict | None]:
    """-> (kept_claim_with_anchor, None) or (None, ledger_row).  Never both, never neither."""
```

`arbitrate` calls `resolve()` once per file in `snap` and then applies, **in this order**:

| # | Condition | Result |
|---|---|---|
| 1 | resolves in >1 shown file | `snippet ambiguous across files shown to the model` |
| 2 | resolves in exactly one file, and it is **not** the cited file | `snippet belongs to a different file than the one cited` |
| 3 | otherwise | fall through to the single-file window-arbitration table above |

Row 2 is the single best-reading ledger row the tool can produce, and without this check a
wrong-file anchor renders as **verified** with a matching sha256 and passes both gates.
`test_resolve.py` asserts the precedence, not just the strings.

**Return `(code, detail)` internally**, format `f"{code} — {detail}"` at the ledger boundary, so
the frozen `DROP_REASONS` vocabulary stays a set of literals while the on-screen reason still
names the match count.

**Explicitly rejected**, each because it can resolve to the *wrong* place:
`difflib`/`SequenceMatcher` fuzzy matching · whitespace-insensitive matching that lstrips each
line · first-hit-wins on ambiguity · AST- or token-normalised matching · dedenting a uniformly
indented quote · accepting single-line quotes.

> **Calibrated on `restored/src/volforecast`.** Quotes ambiguous within their own file:
> 1-line **23.63%**, 2-line **12.80%**, 3-line **7.12%**, 4-line **3.79%**. With the 40-char
> payload floor *and* window scoping to 120 lines: 2-line **3.26%**, 3-line **2.12%**. The prompt
> asks for ≥3 lines; the code floor stays at 2 so a good 2-line quote is not punished.

**Focus.** Each `focus` string is a substring of `quote`. Resolve it to the line containing its
**first character**, at its **first occurrence** in the quote — a quote can repeat a token, and
`backfill_rk.py` alone repeats `parser.add_argument(` 96 times. **If the focus string spans a
newline, emit every line it touches**; the model will naturally return a whole two-line signature.
Then apply the 4-line cap — a 20-line focus inside a 24-line anchor highlights nothing. A focus
string not found **drops the focus, not the claim**. `verify-contract.js:73-74` checks only that
each focus line falls inside the anchor, so "first line" and "last line" both pass while
highlighting different code; pick one and test it.

## 6.2 `expand_anchor`

```python
def expand_anchor(lines, ms: int, me: int, *, cap: int = 24, python: bool = True
                  ) -> tuple[int, int]:
```

1. If `python`, walk `ast.parse` for the smallest `FunctionDef`/`AsyncFunctionDef`/`ClassDef`
   whose `[min(lineno, *decorator linenos), end_lineno]` contains the focus **and spans ≤ cap**.
2. Otherwise pad: **`pad = max(0, (cap - (me - ms + 1)) // 2)`**, clamped to `[1, len(lines)]`.
3. **Then force `start = min(start, ms)` and `end = max(end, me)`**, so focus containment is true
   by construction.
4. `assert start <= ms and me <= end` in `verify_claim`.

> **Why steps 2–4 are not defensive padding.** Without the `max(0, …)`, a quote longer than `cap`
> yields a *negative* pad and an anchor strictly inside its own focus. Reproduced:
> `expand_anchor(lines, 32, 61)` → `(35, 58)` with focus `[32..61]`, giving
> `verify-contract.js:69` → `focus line 32 outside 35-58`, exit 1 — **after** every model call is
> already spent. And it is the common path, not the fallback: **409 of 972 functions (42.1%)** in
> `restored/src/volforecast` exceed cap 24 (median span 20, p90 84, max 572).

Pass `python=False` for any non-`.py` path — `ast.parse` on TOML falls through silently.

## 6.3 The sha256 recipe — exact

> Hex SHA-256 of source lines `start..end` **joined with `\n`**, **no trailing newline**,
> **no line numbers**, UTF-8.

```python
def sha256_range(lines, start, end) -> str:
    return hashlib.sha256("\n".join(lines[start-1:end]).encode("utf-8")).hexdigest()
```

`lines` must come from `textio.read_source`, which has already stripped `\r`. Both stage 4 and
`verify-contract.js:55-59,77` compute it this way; any deviation drops every anchor.

**On Windows this is the single most likely way to drop 100% of anchors.** A CRLF checkout that
reaches the hash with `\r` intact produces `sha256("import os\r\n…")`, which differs from the
gate's recomputation over the bundled (stripped) text. Test it against the gate on day one.

Store into `files` the **byte-identical stripped line text that was hashed**, keyed
`path -> str(int(n)) -> text`. Canonical decimal integers, no zero-padding — verified in Node:
`Object.keys({'058':1,'58':1})` → `['58','058']`, out of numeric order.

## 6.4 The merge

Walk `content.json`. Per block:

- **prose / excerpt / trace** — resolve every cite. Survivors get an `anchor` with `sha256`;
  failures go to `dropped` with a real reason and are **removed from `tracks` entirely**.
  An `inferred` claim passes through untouched and must still carry no anchor.
- **checkpoint** — substitute the full object from `survey.checkpoints[id]`. Unknown id → drop
  the block, log it. (`content.sample.json` has `cp-a9-does-not-exist` deliberately.) The
  substitution is total, so *"the shipped key equals the survey key"* is true by construction —
  self-police it anyway (§6.7), because that is the only thing standing in for acceptance test 6
  once `tools/check-payload.js` is cut.
- **command** — match `commands.json` on `(cmd, cwd)`, merge in the real `exit`/`out`/`dur`/`env`.
  `env` is the file-level string from `commands.json` unless the run carries its own override.
  No match → drop the block, log it. (The fixture has `make coverage` deliberately.) Any
  `exit != 0` **must** get a `broken` banner; `hypothesis` from `classify_failure` passes
  through, always tagged `inferred`.
- **graph / ledger** — field-free, pass through. `map` comes from `map.json`.

**Downgrade-to-inferred must DELETE the `anchor` key** — not blank it, not set it to `null`, not
keep it with a null sha256. `verify-contract.js:89` fails any inferred claim that still carries
one, and `if (c.anchor)` is true for `null`… no — but it is true for `{}`. Delete the key.

## 6.5 Bundling `files`

**Walk the ASSEMBLED payload for every `anchor` key** — prose claims, trace steps, *and* excerpt
blocks. Do not build it from the claim list.

```python
def iter_blocks(tracks) -> Iterator[dict]: ...     # every block of every stop of every track
def iter_anchors(payload) -> Iterator[dict]: ...   # prose claims, trace steps, excerpt blocks
```

`verify-contract.js:96` runs the full anchor check (bundled file, every line present in range,
non-empty sha256) on every trace step, and `:99` on every excerpt block. Trace anchors are
survey-derived, so a `files` map built from claim anchors alone fails **every trace hop** with
`file not bundled` — 6 immediate gate failures on the stop that carries the pitch.

Per anchor: `{str(n): lines[n-1] for n in range(start, end+1)}`, merged per path with `update`.
Contiguous within each range (gate requirement); sparse across disjoint ranges (allowed).
Build from the **final post-verification** anchor set, so dropped and inferred claims cost no bytes.

## 6.6 Drop reasons

The frozen vocabulary in `verified-contract.md` lists four. This plan adds **eight**, listed in
full below. **Patch the doc in the same commit** — a contract that documents a vocabulary the code
does not use is drift, in either direction.

| Reason | Source |
|---|---|
| `snippet not found verbatim in file` | frozen |
| `file does not exist at this commit` | frozen |
| `lines N-M out of range (file ends at K)` | frozen |
| `excerpt hash mismatch — file changed after narration` | frozen |
| `snippet ambiguous` | **new** — 12.4% of distinct lines in `volforecast` repeat within their own file |
| `snippet ambiguous across files shown to the model` | **new** — §6.1 cross-file check |
| `snippet belongs to a different file than the one cited` | **new** — §6.1 cross-file check |
| `snippet resolved outside the excerpt shown to the model` | **new** — window arbitration |
| `quote too thin to be unique` | **new** — quality floor |
| `quote shorter than two lines` | **new** — quality floor |
| `quote longer than the anchor cap` | **new** — quality floor |
| `model returned unparseable output` | **new** — parser |

## 6.7 Assembling `verified.json`

**Ids.** One monotonic counter across the **whole run** — kept *and* dropped claims draw from the
same sequence, so ids are globally unique and the ledger interleaves realistically. Format
`f"c-{n:03d}"`; assert `n < 1000` and abort with a clear message otherwise. The renderer's marker
label is `c.id.slice(-3)`, so `c-7` renders as `c-7` and `claim-1042` renders as `042`.

**Three shipped fields nothing else produces** (decision #27), set here:

```python
payload["repo"]["generated_at"] = datetime.now(timezone.utc).isoformat()   # NOT survey.surveyed_at
report["tool_version"] = TOOL_VERSION      # "0.4.0", a constant in __init__.py
report["duration_s"]   = round(time.monotonic() - t0)   # wall clock over stages 1–5
```

`shell()` reads all three. A missing `generated_at` throws inside `shell()` before the first stop
renders — a blank page that **both gates still pass**, because neither executes the renderer.
This is the one failure mode no check in this plan catches, which is why all three are in the
self-police list below.

**`report` is assembled LAST, by walking the emitted payload.**

```python
report["dropped"] = len(dropped)                      # gate cross-check
report["failed"]  = sum(1 for b in iter_blocks(tracks)
                        if b["type"] == "command" and b["exit"] != 0)   # RENDERED, not the run log
```

`claims` / `verified` / `inferred` / `commands` come from the run log and are **deliberately
larger** than what the page renders — that gap is the point of the pitch. Getting `failed`
backwards (23 commands run, 5 failed, 2 rendered → emitting 5) is the single easiest way to fail
the gate.

**Self-police what neither gate checks, then abort on violation:**

```
claim ids unique and matching ^c-\d{3,}$
checkpoint block ids unique and containing at least one non-digit
    (a bare "12" makes the CHECK button navigate to stop 12 instead of grading)
every checkpoint block deep-equals survey.checkpoints[id]      (acceptance test 6)
claim.status  ∈ {verified, inferred}
callout.level ∈ {info, inferred, broken}; callout.title and .text both non-empty
    (the renderer emits <b>${esc(b.title)}</b> unconditionally — a missing title
     renders the literal word "undefined" on the honest-degradation stops)
stop.kind     ∈ {stop, cp}, and == "cp" iff the stop holds a checkpoint
track.minutes and stop.minutes present; stop.lede present iff stop.kind == "stop"
repo.generated_at, report.tool_version, report.duration_s all present and non-empty
command.exit is a real int  (Number.isInteger — "0" renders FAILING, null renders PASSING)
command.env non-empty
table rows all have len(columns) cells                          (verify-contract.js:146)
every dropped id absent from EVERY block type, not just prose
    (the gate builds its `rendered` set from prose only — :153-154)
every string the renderer interpolates without esc() has been through textio.cell/esc_html:
    table.columns[] · table.rows[][] · checkpoint.options[] · excerpt.caption
    · callout.title/.text · map.nodes[].label (additionally SVG-sanitised)
no backslash in any anchor.file
every map node carries all 9 fields, len(top) >= 1
all seven top-level keys present even when empty:
    contract repo report map files tracks dropped
at least one ledger block
```

**The `>40% dropped` amber flag:** `drop_rate = report.dropped / max(report.claims, 1)` over the
**whole run**. Above 0.40, prepend a `callout level="broken"` to both `cover` and `audit`, and
set the flag `shell()` reads (§7).

---

# 7. Stage 5 RENDER

## 7.1 De-fixturing the template

Copy `demo/trailhead-demo.html` → `src/trailhead/template.html`. **Do this only after committing
the working tree.**

**From that moment `src/trailhead/template.html` is authoritative** and `demo/trailhead-demo.html`
is a generated artifact — rebuilt by `render.py --payload fixtures/verified.sample.json`, with
`tools/inline-fixture.js` retired at hour 1, not hour 8. Two hand-edited copies of a 1900-line
renderer diverging over seven hours is a worse risk than one hour without a known-green demo, and
the demo is recoverable from git in ten seconds. `render.py` locates the file as
`Path(__file__).with_name("template.html")` — no `importlib.resources`, no package data config.

**Locate every edit by its anchor string, never by line number.** The numbers below drifted
between the writing of this plan and its review; the strings did not.

| # | Anchor string | Change |
|---|---|---|
| 1 | `<title>Trailhead · payments-core</title>` | → `<title>Trailhead</title>` (non-empty; check-bundle greps the source text) |
| 2 | `<b>payments-core</b>` | → `<b></b>` |
| 3 | `<span class="meta">a3f9c21 ·` | empty the element |
| 4 | `<span class="sample">` | delete the whole element |
| 5 | `id="badge"` | empty the button's innerHTML |
| 6 | `eight block types` | → `nine`; de-fixture the surrounding data-block comment |
| 7 | `const D = {` | payload → `const D = {};` |
| 8 | CSS | add `.badge.lowconf{border-color:var(--inf)} .badge .lo{color:var(--inf);font-weight:600}` |
| 9 | before boot | insert `shell()` |
| 10 | boot | call `shell()` |

Edit 8 introduces the one genuinely new colour pair in this plan — `--inf` on the badge
background, in **both** themes. Check it against 4.5:1 when you add it (acceptance test 10). It is
also the badge state a judge looks at hardest, because it only appears when the drop rate is high.

**The SAMPLE chip is deleted, not made data-driven** — the contract is frozen and there is no
sample flag. Move the disclosure into the fixture's `cover` lede as data. One-line fixture edit,
survives into print, leaves no `payments-core` string anywhere in the renderer.

**`shell()`** — 14 lines, one splice point instead of eight, and `textContent` escapes a repo
name containing `<` for free:

```js
function shell(){
  const r=D.repo||{}, p=D.report||{};
  document.title = "Trailhead · " + r.name;
  $(".brand b").textContent = r.name;
  $(".meta").textContent = [r.commit,
      "generated " + (r.generated_at||"").replace("T"," ").replace("Z"," UTC"),
      "trailhead " + p.tool_version].join(" · ");
  const lo = p.claims > 0 && p.dropped / p.claims > 0.40;
  $("#badge").innerHTML =
      `<span><i class="n">${p.claims}</i> claims</span>`
    + `<span class="d">${p.dropped} dropped</span>`
    + `<span><i class="n">${p.commands}</i> cmds</span>`
    + `<span class="f">${p.failed} failing</span>`
    + (lo ? `<span class="lo">low confidence — ${Math.round(100*p.dropped/p.claims)}% dropped</span>` : "");
  $("#badge").classList.toggle("lowconf", lo);
}
```

All four badge values are integers, so there is no escaping risk. Spec §6's amber badge —
previously impossible, because the badge was static HTML — is the two `lo` lines. The `||{}`
guards are belt-and-braces on top of §6.7's self-police: a blank page that passes both gates is
the worst outcome in the document, and the guard costs six characters.

**Do not templatise the ledger's regeneration command.** `trailhead build . --out trailhead.html`
is genuinely copy-paste correct when run from the repo root. **Which means `render()` must not
refuse to write inside the repo** — instead, record the resolved output path and add it to the
walker's exclusion set (§3.3). Refusing writes inside the repo makes the one command printed on
screen for the audience the one command the tool rejects.

## 7.2 Splice markers

`verify-contract.js:33-37` scrapes the bundle by slicing between the literal `const D = {` and
the literal `RENDER — knows only` (**U+2014 em dash**), then strips from the first `/*` and
`eval`s the remainder. Both markers must survive, verbatim, **in that order**, or the gate exits
2 before running a single check — which reads as "gate crashed", not "generator broken".

```python
TEMPLATE_MARKER = "const D = {"
SCRAPE_MARKER   = "RENDER \u2014 knows only"

def splice(template: str, payload: dict) -> str:
    assert TEMPLATE_MARKER in template
    assert template.index(SCRAPE_MARKER) > template.index(TEMPLATE_MARKER)
    body = armour_json(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    a   = template.index(TEMPLATE_MARKER)
    end = template.index("}", a)          # placeholder is exactly `{}`
    return template[:a] + "const D = " + body + template[end+1:]
```

No brace-matching is needed in Python — the template placeholder is `{}`. `inline-fixture.js`
needs its string-aware matcher only because it re-splices an already-populated demo.

Write with `encoding="utf-8", newline="\n"`.

## 7.3 The payload armour

```python
def armour_json(t: str) -> str:
    return (t.replace("<", "\\u003c")
             .replace("@", "\\u0040")
             .replace("/", "\\u002f")
             .replace("\u2014", "\\u2014"))
```

Provably safe as a blanket text replace: in JSON, `<`, `@`, `/` and non-ASCII only ever occur
inside string literals — the structural characters are `{}[]",:` plus numbers and bare keywords.
All four are legal JSON escapes, so `JSON.parse`, `eval` and the browser see the original
characters unchanged. **Compute sha256 over the PRE-armour text**, so the gate's recomputation
from the decoded `files` map still matches.

> **The recon's four-rule set does not work, and the fix is not the obvious one.** Measured in
> Node against a payload containing `# /* not a comment */ // nor this <script src="https://a/b.js"></script> @font-face RENDER — knows only`:
>
> | Rule set | `/*` survives | `//` | `<` | `@` | em-dash | round-trips |
> |---|---|---|---|---|---|---|
> | `/*`→`\/*`, `//`→`\/\/` | **yes** | no | no | no | **yes** | yes |
> | `\u002f` blanket + `\u2014` | no | no | no | no | no | yes |
>
> `\/*` still contains the two-character sequence `/*`, which is exactly what
> `verify-contract.js:36`'s `/\/\*[\s\S]*$/` greps for — it truncates the payload and `eval`s
> the fragment. `\/` fails for the same reason. Only `\u002f` removes the character.
>
> This is not hypothetical on the proving-ground repo: `restored/src/volforecast/data/measures.py:4`
> reads `features/*.py re-export these for backward compatibility.` — lines 1–6, i.e. the most
> likely anchor for a "what does this module do" claim. Four more sites exist under
> `restored/src`; 16 `.py` files repo-wide.
>
> The **em-dash rule is also load-bearing** and is absent from the recon's set: a bundled line
> containing `RENDER — knows only` moves the gate's second scrape index *into* the payload,
> truncating the slice.
>
> Cost: +1.5% bytes on a 30 KB payload.

Teaching `check-bundle.js` to skip the data region is **rejected** — check-bundle must pass
unmodified, and armour also fixes the real browser bug (a bundled `</script>` terminates the
script element regardless of JS string context).

## 7.4 How `check-bundle.js` stays green

All 21 passes are inherited from the shell for free: doctype, `lang`, viewport, non-empty
`<title>`, `prefers-color-scheme`, `data-theme`, `prefers-reduced-motion`, `@media print`,
`overflow:auto`, `focus-visible`, `data-proj`, `localStorage`, inline `<style>`/`<script>`,
parseable inline JS, and 284/284 balanced CSS braces. The four self-containment checks
(`<link`, external `<script src>`, `@font-face|@import`, loader URLs) are plain substring greps
over the **whole file including the payload** — the armour is what keeps them green on real repo
source. Size: 81.5 KB shell against a 5 MB hard cap and a 2 MB target; at ~47 B per bundled line
that is ~40,000 lines of headroom, and `--max-units 12` bounds the anchor count independently of
repo size. **Do not build excerpt byte-capping.**

## 7.5 `tools/inline-fixture.js`

**Retired at hour 1**, once `render.py` reproduces `demo/trailhead-demo.html` from
`fixtures/verified.sample.json` and both artifact-reading gates stay green. Its string-aware brace
matcher exists only because it re-splices an already-populated demo; `render.py` splices into a
`{}` placeholder and needs none of it. Keep the file in git until hour 8 as a fallback, but stop
running it — a second splicer is a second way for the demo and the template to disagree.

Stage 0 commits the tree first, so the pre-de-fixture demo is always one `git checkout` away.

---

# 8. Command runner

Non-negotiable #4 is made **structural**, not a matter of discipline: a not-executed candidate is
a different Python type whose only renderer is a callout.

```python
@dataclass(frozen=True)
class CommandResult:
    cmd: str; argv: tuple[str, ...]; cwd: str; exit: int
    out: str; dur_ms: int; dur: str; started: str; timed_out: bool
    env: str                       # see below — verify-contract.js:120 fails a falsy one
    broken: str | None             # set by classify_failure whenever exit != 0
    hypothesis: str | None         # set by classify_failure; always rendered `inferred`

@dataclass(frozen=True)
class SkippedCommand:
    cmd: str; reason: str
```

There is no constructor path producing `exit`/`out`/`dur` without a real run.

**`env` is a real, measured string, not a label.** Built once per run into `commands.json`'s
top-level `env` and copied into every merged block (§6.4):

```python
env = (f"captured {date.today().isoformat()}, {platform.system()} {platform.release()}, "
       f"python {sys.version.split()[0]}")
```

A run whose resolved interpreter differs from the generating one carries its own override with
that interpreter's `--version` output. Omitting `env` entirely is a hard gate failure on **every**
command block on the first real run — `verify-contract.js:120`, `no environment note`.

## 8.1 Execution

```python
p = subprocess.run(argv, shell=False, cwd=str(cwd.resolve()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                   timeout=timeout, env=child_env)
out = p.stdout.decode("utf-8", errors="replace")
```

**`capture_output=True` cannot be combined with `stderr=subprocess.STDOUT`.** Verified on this
box: `ValueError: stdout and stderr arguments may not be used with capture_output.` A runner
specified that way raises before spawning a single child, so every command block degrades to
"Not executed" on every run and non-negotiable #4 is never exercised.

`stderr=STDOUT` rather than two pipes, because capturing two streams and concatenating them
**fabricates the interleaving** — real output has them interwoven.

Never `text=True` — it applies the locale codec, which is `cp1252` here.

Child env overlay: `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`,
`NO_COLOR=1`, `TERM=dumb`, `CI=1`, `COLUMNS=100`, `GIT_TERMINAL_PROMPT=0`. The first two are not
cosmetic: an em-dash in real lint output arrived as a replacement character without them, in a
bundle whose whole point is that its output is real.

**`argv[0]` must be an absolute resolved path** for repo-local wrappers and a `shutil.which()`
result for PATH programs, resolved at discovery time. Verified: `['vol.cmd','help']` with
`shell=False` → `FileNotFoundError [WinError 2]`, while the absolute path → exit 0. Under a naive
handler that becomes `exit 127, "vol.cmd not found on PATH"` — a false sentence about a file that
exists in the repo root. If resolution fails, emit a `SkippedCommand`, never a fabricated 127.

## 8.2 Failure paths

| Situation | `exit` | Notes |
|---|---|---|
| Normal | `p.returncode` | real |
| `TimeoutExpired` | `124` | `timed_out=True`, partial output kept, `broken="timed out after {T} s and was killed"` |
| `FileNotFoundError` | `127` | `broken="{argv[0]} not found on PATH"` |
| `PermissionError` | `126` | |

**Never `exit: None`** (the renderer tests truthiness, so it renders **green** while
`verify-contract.js:103` demands a `broken` banner — a self-contradictory page that still passes
one gate) and **never `exit: "0"`** (renders as failing).

## 8.3 Truncation and the one blessed placeholder

```python
def truncate(out: str) -> tuple[str, bool]:
    """400-line cap (contract), THEN an 8192-byte cap. Both markers explicit."""
```

Line cap first per `commands@1`; then re-check bytes and trim head/tail again with a second
`… N lines elided` marker. A line cap alone is not enough — `uvx ruff check .` emits 219 KB and
`lint_all.py` 25.8 KB, and 60+40 surviving lines of the former still blow 8 KB.

Empty output records the literal `(no output)`. This is the **only** synthesised string in a
command block; it describes an absence rather than inventing content, and `exit` and `dur` stay
real. `verify-contract.js:121` fails an empty `out`, so the alternative is not "show nothing" but
"fail the gate". Acceptance test 5 says *non-placeholder output* and this is, literally, a
placeholder — say so out loud rather than pretending the test passes unqualified.

`dur` is a **display string** (`"11.4 s"`); `dur_ms` is the number. Emit both — `check-fixtures.js`
asserts `every run has both dur and dur_ms`.

## 8.4 Safety posture

Deny-by-default. **Execute from an allowlist, never because a command was discovered.** The four
admitted argv shapes are exactly §3.8's four candidates. Anything else becomes a `SkippedCommand`
rendering as `callout level="info"` titled "Not executed", naming the candidate, its source and
the reason.

`--run-commands {safe,none}`; `none` is the stage panic switch. No `ask` policy — an interactive
prompt in a build you may re-run on stage is the last thing you want. No argv denylist and no
import-reachability engine: once execution requires the allowlist, both are dead code.

Per-command timeout 60 s; total budget 120 s, after which remaining candidates skip with
`generation command budget exhausted`.

Known-hostile, and covered by never being on the allowlist: `uv sync` (pinned to the unreachable
GS Nexus mirror in `src/uv.toml`), `uvx ruff` (11.4 MiB first-run download, 219 KB output),
anything reaching `pytickclient` / `goldmansachs.pyslang` / `gs_quant` / `marquee` (13 files under
`volforecast/`).

## 8.5 Failure rendering

```python
def classify_failure(argv, exit_code, out) -> tuple[str, str | None]:
    """-> (broken, hypothesis|None). A RULE TABLE, never a model call."""
```

`broken` = the last output line matching `/(Error|Exception|error:|FAILED|assert)/`, else the last
non-empty line, verbatim. `hypothesis` emitted only for `ModuleNotFoundError`, and always rendered
tagged `inferred`. The remaining branches restate the exit code the page already shows.

**This is the only producer of `hypothesis`** (decision #26). A `hyp:<cmd-id>` narrate unit would
*not* break non-negotiable #1 — it runs inside stage 3 — but it costs one call, one cache entry
and one parse-failure path per failing command, to restate a traceback the page already prints
verbatim. On `restored` the single `ModuleNotFoundError` case is the whole demo anyway.

---

# 9. Degraded generation

Spec §6's five rows, extended with every case the recon found. **All of it is a generator
obligation** — the renderer has zero conditional-degradation logic.

Every fired row appends to `survey.degradations` / `content.degradations`, which is the input to
the placeholder callouts, the amber-badge decision, and the per-repo golden files in §11.

Every row that emits a `callout` gets its `title` and `text` **here, verbatim**. The renderer
emits `<b>${esc(b.title)}</b>` unconditionally, so an unspecified title renders the literal word
`undefined` on exactly the stops that carry the honest-degradation story. `{}` are template slots.

| # | Trigger | Mode | Callout `title` / `text` | Also emitted | Where |
|---|---|---|---|---|---|
| 1 | no entry point, or trace < 2 hops | ALTERNATE | **broken** · *No traceable entry point found* / "Nothing in this repo declares a console script, a `__main__.py`, or a resolvable `if __name__` guard inside an import root. Candidates considered: {list}." | `cp-c` DROPped | `compose.build_trace` |
| 2 | no admitted `kind=test` command | PLACEHOLDER | **info** · *No test command detected* / "Candidates considered: {cmd} — {deny_reason}." | §5.7's `green` rule 2/3 | `compose.build_green` |
| 3 | every `kind=setup` command failed | PLACEHOLDER | **broken** · *This repo did not build during generation.* / "All {n} setup commands failed. Every one is shown below with its real exit code and output — nothing is hidden." | **every failure in full as real command blocks** | `compose.build_setup` |
| 4 | `len(map.nodes) < 3` | ALTERNATE | **info** · *Too few modules to draw a graph* / "{n} module group(s) found. The table below carries the same information." | no `graph` block at all; a `table` (path, files, loc, imports) | `compose.build_map` |
| 5 | `dropped / claims > 0.40` | — | **broken** · *Low confidence — {pct}% of claims dropped* / "{dropped} of {claims} generated claims failed verification and were deleted. Every one is listed in the audit ledger." | amber badge | `verify.assemble` + `shell()` |
| 6 | `churn.available == false` | ALTERNATE | **info** · *No git history for this path* / "{reason} Files are ranked by fan-in instead; the column header and every entry say so." | table header becomes `fan-in (no git history)`, `top[]` strings carry the label, `repo.commit` = `nogit-<hash>` | `survey.git_churn`, `mapper`, `compose.build_where` |
| 7 | narrate budget exceeded | PLACEHOLDER | **info** · *Narration budget reached* / "{n} of {m} units narrated. The rest render from templates and carry no claims." | unnarrated rows keep `purpose = "—"` | `narrate.build_units` |
| 8 | checkpoint precondition unmet — `cp-a` needs ≥4 distinct directories, `cp-c` needs ≥4 ordered items | DROP | **info** · *Stops not generated* / "{id} — {reason}" per row | stop removed from `tracks` | `compose.build_course` |
| 9 | parse failures > 0 | — | — | count in the audit ledger | `verify.assemble` |
| 10 | files skipped as not-text or outside root | — | — | count in the audit ledger | `verify.assemble` |
| 11 | `stop_reason` was `max_tokens` or `refusal` | DROP | — | ledger row with its own reason | `narrate.parse` |

**A DROPped stop goes in the audit callout, never in `dropped[]`.** `report.dropped ===
dropped.length` is a hard gate cross-check, and stuffing stop-skips there inflates the headline
dropped-claim number — the one number the pitch turns on.

**Never render a placeholder quiz.** "Checkpoint A unavailable" is worse than no checkpoint, and
padding options with invented distractors puts a model-free fabrication into an artifact whose
entire claim is that it has none.

**Never emit a blank stop.** A labelled gap reads as a tool that knows what it does not know;
a blank stop reads as a bug.

---

# 10. CLI

```
python -m trailhead build [repo] [options]

  -o, --out PATH          default trailhead.html
      --work DIR          default <out-parent>/.trailhead
      --payload PATH      default <work>/verified.json — only with --from-stage render
      --provider {stub,claude}     default stub
      --offline           a narration-cache miss is an error
      --run-commands {safe,none}   default safe
      --from-stage {survey,map,commands,narrate,verify,render}
      --max-units N       default 12
      --max-nodes N       default 14
      --gate              run the two artifact-reading gates after writing; fail on non-zero
  -v, --verbose
```

`<repo>` is required **except** with `--from-stage render`, which needs only `--payload`.

**What each `--from-stage` value reads from `<work>`:**

| Value | Reads | Then runs |
|---|---|---|
| `survey` | nothing | everything |
| `map` | `survey.json` | map, commands, narrate, verify, render |
| `commands` | `survey.json`, `map.json` | commands, narrate, verify, render |
| `narrate` | `survey.json`, `map.json`, `commands.json` | narrate, verify, render |
| `verify` | the three above + `content.json` | verify, render |
| `render` | `--payload` (default `<work>/verified.json`) | render |

Exit codes: `0` ok · `1` generation failed · `2` usage · `3` gates failed.

**`--gate` runs two gates against the output, not three.** `check-bundle.js` and
`verify-contract.js` both take a path and read the artifact. `check-fixtures.js` hard-codes
`../fixtures` and takes no argv — it is a repo invariant, run in CI-of-the-mind alongside the
unit tests, and it says nothing about generated output. Anywhere this plan says "all three gates
green", the two that read the artifact are the ones that mean anything.

Everything else is cut (cut-list item 7): `--stops`, `--skip`, `--dry-run`, `--cache-dir`,
`--seed`, `--source-root`, `--stage`, `--cmd-timeout`, `--cmd-budget`, `--allow-cmd`, `--quiet`.
Each flag is argparse plumbing plus a code path plus a way to be wrong on stage. Cutting `--seed`
is why §3.6 pins the one seed to `repo.commit`.

**`--from-stage` is the one that earns its place.** Narrate is the only slow or networked stage,
so `--from-stage verify` re-renders in under a second when you spot a typo mid-rehearsal, and if
the endpoint dies during the pitch you run it off the last `content.json` and nobody notices.

**Artifacts** are written atomically (`tmp` + `os.replace`) as UTF-8 with `newline="\n"` and an
explicit `encoding=`. `run_gates` shells out to both artifact gates; if `node` is missing it
**warns and returns 0** — the bundle is already written, a missing gate runner is an environment
problem, and it prints the commands to run by hand.

Stage 4 is gateable before any HTML exists — `verify-contract.js` already accepts a bare JSON path:

```bash
node tools/verify-contract.js .trailhead/verified.json
```

---

# 11. Genericity harness

## 11.1 Four tiny fixture repos

`hackathon/tests/repos/`, 3–8 files each, checked in. Not fourteen — the other ten duplicate
layouts that already exist on this machine, at a cost of 40–80 hand-written files.

| Repo | Proves |
|---|---|
| `hazards/` | **The single highest-value asset.** A CRLF file, a BOM file, `\x0c` in a docstring, latin-1 with a PEP 263 cookie, a 5,000-char line, a syntax-error file, a PNG named `.py`, a 0-byte `__init__.py`, and `evil.py` containing `<script src="https://x/y.js">`, `@font-face`, `@import`, `/*`, `</script>` and `RENDER — knows only`. |
| `flat_script/` | No `__init__.py`, no pyproject, **zero internal edges** → the root cascade's terminal fallback, `C=1` in the layout, `<3 modules` → table not graph, `cp-a` dropped |
| `nested_root/` | pyproject at `src/`, `restored`'s layout in miniature: anchor root ≠ import root, and `tests/` outside the declared package |
| `no_entry/` | No `__main__`, no scripts, no `if __name__` → §6 row 1, and no test command → row 2 |

**`restored/` cannot be the genericity test.** It is LF-only, BOM-free, syntax-error-free, has no
long lines and no git history — it is the *unrepresentative* repo on this machine. `hazards/` is
the only thing that will ever exercise the encoding paths before demo day.

Each carries an `expect.json`, so *"it degraded correctly"* is tested and not just *"it did not
crash"*:

```jsonc
{ "degradations": ["no_churn", "no_test_command"],   // exact set, order-insensitive
  "map_nodes": 1 }                                    // len(map.nodes); omit to skip
```

## 11.2 Real repos on this machine

Cheaper and more honest than synthesising more layouts. All paths under
`C:/Users/ryanv/Documents/Projects/`:

| Repo | Axis it exercises that `restored` does not | Expected `len(map.nodes)` |
|---|---|---|
| `ryanatron-v2` | **93/93 `.py` CRLF**, real git history, flat app (`main.py` + `cogs/` + `utils/`), no pyproject | 3 — a real graph, via §4.1's no-declared-packages fallback |
| `IMC-Prosperity-4` | 161 project `.py` inside **19,494** — directory pruning; src-layout with 5 sibling packages and `tests/` outside the import root | 6 |
| `qrt` | 7 loose `.py`, zero `__init__.py`, **zero internal edges** — the `C=1` layout guard | 1 — §9 row 4 fires, correctly |

Both node counts are the check that §4.1's fallback works. Without it every repo here reports 0
and the map is never drawn on a repo with real git history.

## 11.3 The acceptance loop

No new framework. Fifteen lines:

```bash
for R in tests/repos/hazards tests/repos/flat_script tests/repos/nested_root \
         tests/repos/no_entry restored ../../ryanatron-v2 ../../qrt; do
  PYTHONPATH=src py -3.11 -m trailhead build "$R" -o "out/$(basename $R).html" \
      --provider stub --run-commands none --gate || echo "FAIL $R"
done
```

Both artifact gates exit 0, zero unhandled exceptions, and `verification-report.json.degradations`
matches `expect.json` where one exists.

## 11.4 End-to-end against `restored`

```bash
cd hackathon
PYTHONPATH=src py -3.11 -m trailhead build restored -o out/restored.html \
    --provider claude --run-commands safe --gate
```

Expected: `churn.available=false` fires row 6, `repo.commit` starts `nogit-`, `python -m
volforecast --help` renders **failing** with a real `ModuleNotFoundError`, and the dangling-import
count is 14 targets / 706 statements.

---

# 12. Tests

`unittest`, in the established style of `tests/test_survey.py`: a stage-naming module docstring
stating *why* the module is tested plus the exact run command; one CamelCase class per function
under test; full-sentence test names; a blank line between arrange and assert; comments that
explain reasoning, not mechanics; class-level constants for shared fixtures.

```bash
cd hackathon && PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
```

**No pytest in `hackathon/tests`.** TDD applies to `survey.py`, `mapper.py`, `resolve.py`,
`verify.py` and `runner.py` only — iterate the renderer, the layout aesthetics and the prompts
against the browser and the gates.

### `test_resolve.py` — the project's risk lives here

| Test | |
|---|---|
| `test_two_line_exact_quote_resolves_to_its_line_range` | **must** |
| `test_line_number_gutter_is_stripped_when_every_line_carries_one` | **must** |
| `test_a_partially_gutter_prefixed_quote_is_left_alone_and_drops` | **must** |
| `test_crlf_in_the_quote_matches_an_lf_normalised_file` | **must** |
| `test_leading_indentation_must_match_exactly` | **must** |
| `test_a_single_line_quote_is_refused_rather_than_guessed` | **must** |
| `test_a_snippet_appearing_twice_is_dropped_not_resolved_to_the_first_hit` | **must** |
| `test_a_snippet_appearing_twice_resolves_when_only_one_copy_was_shown` | **must** |
| `test_a_quote_resolving_outside_every_shown_window_is_dropped` | **must** |
| `test_a_quote_matching_a_different_shown_file_reports_the_wrong_file_reason` | **must** |
| `test_a_quote_longer_than_the_anchor_cap_is_refused` | **must** |
| `test_trailing_whitespace_is_ignored_identically_on_both_sides` | if-time |
| `test_a_quote_of_only_punctuation_is_refused_as_too_thin` | if-time |
| `test_blank_lines_around_the_quote_are_trimmed_but_interior_ones_are_kept` | if-time |

### `test_verify.py`

| Test | |
|---|---|
| `test_focus_lines_always_fall_inside_the_returned_range` — incl. a 30-line quote | **must** |
| `test_a_function_longer_than_the_cap_falls_back_to_a_padded_window` | **must** |
| `test_the_hash_matches_the_frozen_recipe_on_a_shipped_fixture_anchor` | **must** |
| `test_a_surviving_carriage_return_changes_the_hash` | **must** |
| `test_an_inferred_claim_carries_no_anchor_key_at_all` | **must** |
| `test_report_failed_counts_rendered_blocks_not_the_run_log` | **must** |
| `test_report_dropped_equals_the_ledger_length` | **must** |
| `test_the_files_map_bundles_trace_step_anchors_too` | **must** |
| `test_a_dropped_claim_id_appears_nowhere_in_tracks` — every block type, not just prose | **must** |
| `test_checkpoint_blocks_are_identical_to_the_survey_answer_keys` — acceptance test 6 | **must** |
| `test_generated_at_tool_version_and_duration_are_present` — `shell()` throws without them | **must** |
| `test_claim_ids_are_unique_across_kept_and_dropped_claims` | if-time |
| `test_a_file_that_does_not_parse_falls_back_to_padding_without_raising` | if-time |

### `test_survey.py` — extends the existing 8, all of which keep passing

| Test | |
|---|---|
| `test_crlf_and_lf_files_hash_identically` | **must** |
| `test_bom_is_stripped_and_the_text_still_parses` | **must** |
| `test_an_import_of_a_module_that_does_not_exist_is_dangling_not_internal` | **must** |
| `test_a_pyproject_one_level_down_wins_over_the_repo_root` | **must** |
| `test_import_roots_include_the_parent_of_every_test_root` | **must** |
| `test_no_internal_edges_on_a_large_repo_raises_source_root_error` | **must** |
| `test_the_churn_argv_passes_dashdash_and_dot_as_two_elements` | **must** |
| `test_an_untracked_subdirectory_reports_unavailable_with_a_reason` | **must** |
| `test_form_feed_in_a_docstring_does_not_split_a_line` | if-time |
| `test_a_png_named_dot_py_is_skipped_as_not_text` | if-time |
| `test_the_known_set_is_scoped_per_import_root` | if-time |
| `test_a_relative_import_inside_a_package_init_resolves_to_the_package_itself` | if-time |
| `test_pycache_and_venv_are_pruned_at_directory_level` | if-time |
| `test_project_scripts_outranks_main_module_which_outranks_if_name_main` | if-time |

### `test_map.py`

| Test | |
|---|---|
| `test_a_graph_with_no_edges_lays_out_without_dividing_by_zero` | **must** |
| `test_a_column_holding_one_node_does_not_divide_by_zero_in_the_row_gap` | **must** |
| `test_every_rect_fits_the_canvas_from_three_to_fourteen_nodes` — `MAP_CAP` makes 40 unreachable | **must** |
| `test_no_two_nodes_overlap` — heights from `node_h`, never a literal | **must** |
| `test_a_single_very_long_label_still_fits_the_canvas` — the `W_MAX` clamp | **must** |
| `test_top_is_never_empty_even_when_every_file_is_a_tiny_init` | **must** |
| `test_every_edge_names_an_emitted_node_and_never_points_backward` | **must** |
| `test_every_input_module_belongs_to_exactly_one_node` | if-time |
| `test_width_covers_both_the_label_and_the_stats_string` | if-time |
| `test_edge_weight_is_capped` | if-time |

### `test_runner.py`

| Test | |
|---|---|
| `test_exit_code_and_duration_are_real` | **must** |
| `test_timeout_reports_124_and_never_none` | **must** |
| `test_non_ascii_output_survives_on_windows` | **must** |
| `test_silent_command_gets_the_no_output_placeholder_but_keeps_its_real_exit` | **must** |
| `test_failing_command_always_carries_broken` | **must** |
| `test_long_output_is_capped_by_lines_then_by_bytes` | if-time |
| `test_missing_executable_reports_127` | if-time |

### `test_render.py`

| Test | |
|---|---|
| `test_the_dangerous_sequences_are_escaped` — `/*`, `//`, `</script>`, `@font-face`, `://`, em-dash | **must** |
| `test_json_round_trips_through_the_armour` | **must** |
| `test_both_scrape_markers_survive_in_order` | **must** |
| `test_an_inferred_claim_with_an_anchor_is_rejected` | **must** |
| `test_a_payload_with_no_ledger_block_is_rejected` | if-time |

### `test_narrate.py` / `test_checkpoints.py`

| Test | |
|---|---|
| `test_the_order_answer_is_the_inverse_permutation` | **must** |
| `test_the_corrected_fixture_key_round_trips` — `[4,3,1,5,2]`, not `[3,5,2,1,4]` | **must** |
| `test_an_inferred_claim_is_stripped_of_any_cite_the_model_returned` | **must** |
| `test_a_conventions_unit_forces_every_claim_to_inferred` | **must** |
| `test_a_cite_carrying_a_start_or_end_key_is_rejected_not_repaired` | **must** |
| `test_a_quote_containing_digits_is_not_mistaken_for_a_line_number` — `timeout=60` | **must** |
| `test_fewer_than_four_real_options_emits_nothing` | if-time |
| `test_option_pool_is_deduped_by_file_before_sampling_distractors` | if-time |

---

# 13. The 10-hour schedule

## Reconciling with CLAUDE.md

CLAUDE.md's published order is the operative one; `walkthrough-spec.md` §9 is superseded except
for its hour 8–10 rows (it describes RENDER work that is already done). Four deliberate
departures, each stated:

| CLAUDE.md says | This plan does | Why |
|---|---|---|
| `0–1 Freeze verified.json; hand-write a fixture` | Fixture exists and is frozen. **Hour 0–1 ships `render.py` instead.** | The fixture chain is already complete and gate-green. Building RENDER first turns the whole rest of the project into "replace one fixture" and gives an end-to-end loop at minute 45 instead of hour 6. |
| `1–3 Survey … git churn` | Survey with churn as a **three-state probe whose untracked branch is the default path** | `restored/` has 0 commits and 0 tracked files. Churn is optional data, not a feature. |
| `3–4 Command runner` | Runner moves **before** narrate in the pipeline | Narrate then sees real failures and can write a real hypothesis; degradation is decided in one place. |
| `6–7 Wire render to real verified.json` | Render was wired at hour 1; hours 6–7 are the **first real end-to-end run** | Shell templating (~30 min) is budgeted at hour 1, not discovered at hour 6. |
| `8–9 Generate against two repos` vs `Chase generality after hour 4` | **All genericity is bought before hour 4** (root discovery, the classifier, churn fallback, the read recipe). After hour 4, in-place fixes only. | Resolves the contradiction the published order contains. |

## The schedule

The **spine** column is what a single engineer builds; everything else is the five-owner
expansion. At the end of each hour, the thing in *Running* actually runs.

| Hr | Spine (one engineer) | Also, if five | **Running end-to-end at the close of the hour** |
|---|---|---|---|
| **0–1** | Stage 0 fixes (below), gitignore first. `textio.py` + `render.py` + `cli.py` skeleton + template de-fixture + `shell()`. Smoke-test `anthropic`. | D starts projector polish; B starts one live round trip | `py -3.11 -m trailhead build --from-stage render --payload fixtures/verified.sample.json -o out/demo.html`, **both artifact gates exit 0**, titled and badged from `D.repo`/`D.report` |
| **1–2** | `survey.py`: roots, walk, module index, classifier, `SourceRootError`. Tests first. | B: prompts + parser vs `StubProvider` | Same, plus `survey.json` for `restored`: **1854 internal import statements, 588 distinct file-level edges, 14 dangling targets / 706 statements** |
| **2–3** | `resolve.py` + `test_resolve.py`, TDD. It takes a quote and a line list — zero dependencies on any other module, and it is what hour 4 tests. | A: churn + entry points | `resolve()` green on the full must-list |
| **3–4** | `survey.py`: churn 3-state, entry points, command candidates. `mapper.py`: collapse + layout + invariants. `runner.py` + `checkpoints.py`. | D: degradation blocks | `map.json` for `restored`: 12 nodes, every geometry invariant asserted; `commands.json` with real exits — import smoke 0, `--help` 1 with a real traceback |
| **4** | **PIVOT CHECKPOINT — see below** | | |
| **4–5** | `verify.py` merge + ledger + `files` bundle + `report` + self-police. | | `node tools/verify-contract.js .trailhead/verified.json` exits 0 on a payload built from **real survey + real commands + stub narration** |
| **5–6** | `compose.py` STOP_TABLE + block builders + degradation rows. | | **First full generated `out/restored.html`, both artifact gates green.** The narration cache is still empty, so every stub miss returns `{"claims": []}` and each stop renders from its template blocks — which is precisely the degradation path §9 promises, exercised for free. |
| **6–7** | `provider.py` + `narrate.py` + `prompts.py`. First live run. Commit the narration cache. | | `restored.html` with **real model prose and a real drop count. Open it in a browser** — check the map does not clip and the body does not scroll horizontally at 1440/1024/768/375 px with `restored`'s long paths in the tables and excerpt headers. |
| **7–8** | Unfamiliar repo #1 (`ryanatron-v2` — CRLF + real git history). Fix what breaks. Walk the whole course once by keyboard alone (acceptance test 9). | | Two repos generating, both gate-green |
| **8** | **FREEZE.** Only fixes for what repo #2 breaks. No new features. | | |
| **8–9** | Unfamiliar repo #2 + `tests/repos/hazards`. Fix in place. | | Four repos generating, `hazards/` clean |
| **9–10** | Rehearse the pitch twice, out loud, on the machine and screen you will use. Wifi off. | | The pitch |

### Stage 0 — do these in the first 20 minutes

0. **Gitignore before anything else.** Add `hackathon/restored/`, `hackathon/out/`, `.trailhead/`
   and `__pycache__/` to `.gitignore`, then check `git status --short hackathon` is a handful of
   lines, not 1065. `git add hackathon/` without this commits 14 MB of the vol project including
   455 `.py`, which makes the `docs-only` no-Python rule unenforceable (§15 risk 12).
1. **Commit the working tree.** `git ls-files hackathon` returns two files; `src/`, `tests/`,
   `tools/`, `fixtures/`, `briefs/` and both spec docs are all untracked. A mistake at hour 6 is
   currently unrecoverable. `feat(hackathon): survey, fixtures, gates, briefs`.
2. **Fix `cp-c1`** to `[4,3,1,5,2]` in **both** `fixtures/survey.sample.json` and
   `fixtures/verified.sample.json`. Re-run `inline-fixture.js` and all three gates.
3. **Patch `verified-contract.md`:** version line `@1` → `@2` (line 3 is already `@2`; the JSON
   example at line 61 is not); add `track.minutes`, `stop.kind`, `stop.lede`, `command.env`,
   `command.predict`, `trace.steps[].next` and `trace.steps[].predict` to the field tables; add
   **all eight** new drop reasons (§6.6); strike §4.2's elision-count requirement
   (`verify-contract.js:71-76` forbids gapped ranges, so the path is unreachable).
4. **Amend `walkthrough-spec.md`:** §4.4's 40-node cap → 14; §3 stop 3's *churn rank, recent
   committers* and §4.4's *top 5 files by churn* become optional with a declared substitute;
   §6 row 4's *text fallback list* → *a table replacing the graph block* (§4.4); and **strike the
   three features the renderer does not have and nobody will build** — §4.4's zoom, pan and
   per-node expand, and §7's `0` resets graph zoom. Replace them with what exists:
   hover-to-isolate, click-to-drawer, Esc-to-close, and the `<details>` text equivalent inside
   `graph()`. Two minutes, and it stops acceptance test 9 being scored against a promise.
5. **Fix `pipeline-contracts.md`:** the map fixture is not inline in the survey fixture.
6. **Fix `README.md`:** Survey is not "not started"; and the renderer *shell* does reference the
   sample repo even though the render *functions* do not.
7. **`py -3.11 -m pip install anthropic`**, then a five-line `python -c` round trip against the
   configured `base_url`. At hour 0 a missing SDK or a bad credential costs two minutes; at hour 6
   it costs the live run.

### The hour-4 pivot checkpoint

**The concrete test.** Run this and read the number:

```bash
cd hackathon
PYTHONPATH=src py -3.11 -m trailhead build restored -o out/restored.html \
    --provider stub --run-commands safe --gate
node tools/verify-contract.js .trailhead/verified.json
```

The core loop is **reliable** if all four hold:

1. `check-bundle.js` and `verify-contract.js` both exit 0 on the generated bundle.
2. `survey.json` reports ≥ 500 distinct file-level edges and ≥ 10 dangling targets for `restored`
   (a wrong source root gives 1 or 0).
3. Every map geometry invariant asserts clean at 3, 8 and 14 nodes. Not 40 — `MAP_CAP` makes 40
   unreachable, and §4.2 step 6 merges rather than raising if a packing ever does not fit.
4. `resolve()` returns a range for ≥ 90% of a hand-built set of 20 real quotes taken from
   `restored/src/volforecast`, with **zero wrong-file resolutions**. `resolve.py` is scheduled at
   hours 2–3 precisely so this test has something to run against.

**If any fails at hour 4: hard-code the demo path.** Concretely — freeze the `restored/` survey
and map as checked-in JSON, load the eight trace hops from `fixtures/trace.restored.json` (every
one is a contiguous ≤24-line window with its focus lines inside it, so it satisfies the frozen
anchor shape as written; see Appendix A.3), keep the real command runner and the real verifier,
and generate the demo from those. The pitch survives intact, because the pitch is *the machine
checks the facts*, not *the machine discovers the facts generically*.

---

# 14. Cut list

CLAUDE.md's published list — **stop 12 → stop 15 → stop 10 → checkpoint B → stop 7** — is
**already fully spent**: the shipped fixture has 11 stops and omits exactly those five. It has
zero remaining slack. The replacement, over the surviving 11:

**Stop cuts, in order:** `conv` → `where` → `cp-c` → `cp-a`.
None of them is a claim marker, the audit panel, or the drop count.

**Generator cuts, in order.** Items 1–4 are cut *before hour 0* — carrying them invites starting
them.

| # | Cut | Saves | Cost |
|---|---|---|---|
| 1 | `chain.py` (ast call-chain walker) | 0.5 h | Trace hops hand-specified in `fixtures/trace.restored.json` (Appendix A.3); `cp-c` becomes a layer-order checkpoint from the map column index — arguably the better question, since it teaches the map the reader just looked at |
| 2 | Per-node `map:<node>` narration (10 of 17 units) | 0.7 h + 60% of the call budget | `node.why` is a template. Also removes an unanchored-prose surface and the `MOST-EDITED FILES` mislabelling pressure |
| 3 | The `where` unit's model-written purpose cells | 0.3 h | Purpose from the `__init__.py` docstring. Also removes the table-cell escaping surface entirely |
| 4 | Dynamic viewBox + the tick-count formula + `map.w`/`map.h` | 0.3 h | Canvas stays 900×400 — which it fits anyway |
| 5 | Framework entry-point detector (rule 4) | 0.2 h | `restored` has 0 click / typer / fastapi / flask |
| 6 | `.gitignore` honouring in the walk | 0.3 h | The 22-name static list covers every repo measured on this machine |
| 7 | 14 of the 20 CLI flags | 0.5 h | Keep `-o`, `--provider`, `--run-commands`, `--from-stage`, `--gate` |
| 8 | Makefile/justfile + CI-workflow + platform-wrapper command discovery (rules 5–8) | 0.5 h | Four candidate shapes cover `restored` completely |
| 9 | 10 of the 14 fixture repos | 1.7 h | Real local repos cover the same axes for free (§11.2) |
| 10 | The semantic repair retry | 0.4 h | Drop rate rises ~3% → ~6% — **which is a better number to say out loud**, since the drop count is the never-cut item and 1 ledger row does not carry the pitch |
| 11 | The re-read gate | 0.3 h | Its stated justification is wrong: the snapshot is minutes old, and a changed file changes the prompt hash and misses the cache anyway. **If cut, strike the two now-unreachable reason strings from the contract doc** rather than shipping a contract documenting checks the code does not perform |
| 12 | `tools/check-payload.js` as a fourth Node gate | 0.4 h | Every check it would run already lives in `verify.assemble`'s self-police list, in Python, where it fails *before* a bad page is written |
| 13 | The audit ledger's sortable/filterable UI (spec §4.6) | — | Not implemented, and not on the never-cut list. The **count** and the **table** are what must never be cut |

**Held in reserve — take these the moment hour 3 arrives with `mapper.py` unwritten**, in order.
They are not pre-committed because each costs a real beat, but deciding them now beats discovering
them at hour 6:

| # | Cut | Saves | Cost |
|---|---|---|---|
| 14 | `runner.py` down to two allowlisted shapes — `python -c "import <pkg>"` and `python -m <pkg> --help` | 0.4 h | The failing `--help` is pitch beat 4; the lint and pytest candidates are not. Also deletes the truncation and budget logic |
| 15 | `cp-c` entirely (already stop-cut #3) | 0.3 h | Also deletes `order_key`, the inverse-permutation trap, and the stage-2 checkpoint merge-back |
| 16 | The `green` and `conv` narrate units, leaving `five` + `trace` | 0.3 h | Two fewer stops with claims. `trace` is the beat; `five` is the opener |
| 17 | Entry-point rules 2 and 4 (`setup.py` regex, framework detector) | 0.3 h | `restored` gives zero from both |
| 18 | `--from-stage` down to `render` and `verify` | 0.2 h | The two that earn their place mid-rehearsal |

## Never cut, in the order they will tempt you

1. **The payload armour.** Without it the gates fail on the *actual* proving-ground repo. Not a
   polish item.
2. **`shell()`, and the three fields it reads** — `repo.generated_at`, `report.tool_version`,
   `report.duration_s`. Without `shell()` a walkthrough of ML-GS ships titled `payments-core`
   claiming 142 claims and 8 dropped. Without the fields it throws at boot and ships blank —
   and **both gates still exit 0**, because neither executes the renderer. That destroys the
   pitch on stage more surely than any missing feature.
3. **One read path and one path canonicaliser.** A second of either is a guaranteed sha256
   mismatch against the gate.
4. **The resolver's refusal to guess**, and window-scoped arbitration. This is the project.
5. **The dangling-import classifier.** 27.4% of edges are wrong without it.
6. **The `SourceRootError` self-check.** Turns a silent empty graph into a loud failure.
7. **The three-state git probe with the two-element `-- .` pathspec.** Without it the page
   confidently reports another project's history at exit 0.
8. **`report` assembled last.** The two cross-checks are the only hard gate failures the
   generator can cause.
9. **The `CommandResult` / `SkippedCommand` type split.** It is what makes non-negotiable #4
   structural rather than a matter of discipline.
10. **Claim markers, the audit panel, the dropped-claim count.**

---

# 15. Risks

Ranked by expected cost. Each has a trigger you can observe and a mitigation you can execute.

| # | Risk | Trigger you can observe | Mitigation you can execute |
|---|---|---|---|
| 1 | **Scope.** ~1790 impl + ~810 test LOC against a 10-hour budget already partly spent. The three designs this plan consolidates totalled 17.25 h in isolation. | Hour 4 arrives with no `verified.json` from real inputs | The **spine** column of §13 plus cuts 1–8, all pre-committed. If hour 4's test fails, hard-code the demo path — the pivot rule is a plan, not an admission |
| 1b | **Two spine hours are underbudgeted by ~2.5×.** Hour 3–4 carries churn + entry points + command candidates + all of `mapper.py` + `runner.py` + `checkpoints.py`, with three constant-tuning loops in the layout; hour 5–6 carries a 220-line `compose.py`. Realistically 2.5 h and 2 h. Rebalancing them properly means re-deriving the whole schedule, which is not an hour well spent before the build starts. | `mapper.py`'s invariants are not green when hour 4 starts, or `compose.py` is not emitting all eleven stops when hour 6 starts | Take reserve cuts 14–18 (§14) in order, starting the moment the trigger fires. Cuts 14 and 15 alone return ~0.7 h and delete two of the three constant-tuning loops |
| 2 | **Tool access unresolved.** CLAUDE.md open decision 1 is still open; nobody has measured the internal endpoint's rate limit. | No successful round trip by hour 2 | `StubProvider` is the **default**, so the parser, prompts, unit loop, verifier and both gates are all exercised with zero tool access. Ship the offline bundle if needed; a recorded cache makes the live path optional |
| 3 | **CRLF on a fresh clone.** 100% claim-drop rate under a naive read; `restored/` is LF-only and will never surface it. | `verify-contract.js` reports 0 anchors verified on repo #2 | `test_crlf_and_lf_files_hash_identically` on day one; `tests/repos/hazards/` before hour 8 |
| 4 | **The map spills the canvas on an unfamiliar repo.** Neither gate checks a single coordinate, and an invariant that asserts a *different* height formula from the renderer's passes while the browser clips — which is what the first draft of §4.2 did, under-reserving `restored`'s twelve nodes by 166 px | A node overlapping or clipped in the browser | `node_h` is the single definition of rect height, built from `H_BASE`/`H_DIV` copied verbatim from `demo/trailhead-demo.html:1731`, and both the packing and the invariants call it. Invariants assert **in `build_map`**, so a bad layout raises during generation. First browser check of a generated map is hour 6–7, not hour 9 |
| 5 | **The demo repo has no green test and no git history.** `restored` is a strong degradation showcase and a weak happy-path one. | The stage run shows three amber callouts and no green beat | Generate against **two** repos: `restored` for honesty, a CRLF repo with real history for the clean run. Decide repo #2 by hour 4 |
| 6 | **Drop count lands at 0 or 1.** ~7 units × ≤5 claims ≈ 30 run-wide claims; at 3% that is one ledger row, and the pitch line is *"here are the eight claims it caught"*. | `report.dropped <= 2` after the first live run | Deliberate: cut the repair retry (cut #10), keep the quality floors strict, and **say the real number** rather than the rehearsed one. A judge will ask if it is zero |
| 7 | **Six surfaces are interpolated raw by the renderer** — table cells *and column headers*, checkpoint `options[]` (both kinds), excerpt `caption`, callout `title`/`text`, and `map.nodes[].label`. `verify-contract.js:153-154` builds its `rendered` set from **prose blocks only**, so even a *dropped* claim id in a cell escapes the one check the contract calls pitch-destroying. | A `<` in a path breaks the page layout, or a ledger id appears in a cell | `textio.cell()` escapes the value and re-wraps in a two-tag whitelist (§0 #20b); §6.7 self-polices the full list; §0 #20/#20c keep model prose out of all six by construction. **Not fully fixed:** the gate still does not walk them |
| 8 | **Trace hop claims render as verified with no marker and no way to mark them inferred.** | A hop sentence that cannot be anchored | §5.6's fallback: keep the survey anchor, swap in a template sentence, ledger the model claim. **Not fully fixed:** the renderer has no inferred styling for trace steps, so an unanchorable hop sentence can never be shown as such |
| 9 | **`pipeline-contracts.md` names a `map@1` fixture that does not exist**, so stage 2 has no fixture to code against and `check-fixtures.js` never sees a node. | `check-fixtures.js` passes while the map is nonsense | Geometry invariants assert in `build_map`. **Not fully fixed:** writing a `map.sample.json` and teaching `check-fixtures.js` to read it is cut-list adjacent; do it at hour 8 if repo #2 exposes a map bug |
| 10 | **`report.claims` counts a run that never happened.** The whole-run counters are deliberately larger than the rendered ones, which makes them impossible to gate — and easy to inflate. | `report.claims` is a round number | Source it from a real per-unit log in `verification-report.json`. **Not fully fixed:** no gate can distinguish an honest 142 from an invented one. Discipline only |
| 11 | **Two owners implement one hash.** `textio.sha256_range` (E) vs `verify.py` (C). | Every anchor drops on a CRLF repo | One function, in `textio.py`, imported by both. Stated in §3.1 and enforced by the ownership table |
| 12 | **`restored/` is 14 MB of the vol project sitting untracked inside `hackathon/`.** `git add hackathon/` commits 1065 files, and 455 `.py` would make the `docs-only` no-Python rule unenforceable. | `git status` shows `?? hackathon/restored/` | Gitignore it — **stage 0 item 0**, before the commit, not after. Decide out loud. Also: generating a walkthrough *of* the vol project is an on-stage optics judgement — mitigate by running live against repo #2 and keeping the `restored/` bundle as the offline fallback |
| 13 | **No gate independently recomputes a checkpoint answer key.** §6.4 substitutes the whole object from `survey.checkpoints[id]`, so the payload matches survey by construction — but nothing recomputes the key *from the repo*. Decision #15 proves this matters: a wrong `cp-c1` key passed both gates for a day. A real independent recompute means a second implementation of the derivation, which is an hour and its own bug surface. | A checkpoint marks the correct answer wrong during a rehearsal | §6.7 self-polices payload-equals-survey; `test_checkpoints.py` asserts the derivation against hand-computed keys. **Not fully fixed:** the derivation is checked once, by a test, not on every build. Answer every checkpoint yourself during the hour 9–10 rehearsal — that is the recompute |
| 14 | **`report.claims` and the whole-run counters cannot be gated.** They are deliberately larger than the rendered ones, which is the point of the pitch and also the reason no cross-check can bound them. Same for the `(no output)` placeholder against acceptance test 5, and for table cells against the `dropped`-not-rendered check (`verify-contract.js:153-154` walks prose only). | A judge asks how `142` was arrived at | Source every counter from the per-unit log in `verification-report.json` and be able to open it on stage. **Not fully fixed** in any of the three cases — say the real numbers, and say which checks do and do not cover them |

---

# Appendix A — walkthrough of `hackathon/restored`

The demo script. Every fact below was measured, not assumed. Anything not measured is marked
**verify at build time**.

## A.1 The repo

| | |
|---|---|
| Path | `hackathon/restored` |
| Anchor root | `restored/` |
| Import root | `restored/src` — **verified**: `restored/` gives 1 edge of 782, `restored/src/volforecast` gives 0 of 354 |
| pyproject | `src/pyproject.toml` — the only one in 1125 files; `packages = ["volforecast"]` at `:50`, `[project.scripts]` at `:52-53`, `testpaths = ["tests"]` at `:79` |
| Files | 455 `.py`, 364 `.md`, 95 `.yaml`, 48 `.sh`, 44 `.cmd`; 1125 total, 12.6 MB |
| Parse health | 455/455 parse, 0 non-UTF8, 0 BOMs, 0 CRLF, 0 syntax errors, 0 lines > 500 chars |
| Imports | internal 1854 · **dangling 706** · external 1922 · 588 distinct file-level edges |
| Git | `rev-parse --is-inside-work-tree` → `true`; `log -1 -- .` → **empty**; `ls-files -- .` → **empty**. State `GIT_UNTRACKED`. `--show-prefix` → `hackathon/restored/` |
| `repo.commit` | `nogit-<8 hex>` — **verify at build time** |

## A.2 Map nodes — measured

Labels are relative to the import root. `loc` measured recursively.

| id | label | files | loc | Notes |
|---|---|---|---|---|
| `n-models` | `models` | 22 | 9,802 | largest |
| `n-data` | `data` | 21 | 9,195 | |
| `n-cli` | `cli` | 28 | 7,342 | most files |
| `n-evaluation` | `evaluation` | 14 | 7,031 | |
| `n-features` | `features` | 18 | 3,110 | |
| `n-utils` | `utils` | 7 | 1,552 | |
| `n-pipeline` | `pipeline` | 6 | 1,307 | |
| `n-graphs` | `graphs` | 9 | 826 | |
| `n-reporting` | `reporting` | 9 | 461 | has a `sections/` subdir |
| `n-visualization` | `visualization` | 2 | 102 | smallest |
| `n-root` | `volforecast` | 3 | 1,013 | `__init__.py`, `__main__.py`, `registry.py` |
| `n-tests` | `tests` | 225 | 55,156 | forced to one node |

**12 nodes.** Width is set by the **stats** string, not the label: `tests` gives
`"55,156 loc · 225 files"` (22 ch) → `w = ceil(22 + 6.0×22) = 154`, the widest node.
`Cmax = 4` — `5×154 + 4×26 = 874 ≤ 884`, `6×154 + 5×26 = 1054 > 884`.

`node_h = 44 + sqrt(loc)/6` spans **45.7** (`visualization`, 102 loc) to **83.1** (`tests`),
summing to **665.1 px** against a 358 px band. `C_min = ceil((665.1 + 11×13)/358) = 3`, whose
gutter is 223 px — over the `3 × COL_GAP` threshold, so §4.2 step 4 widens to `C = 4`, gutter
103 px. Greedy balance at `C = 4` gives columns of **2 / 3 / 3 / 4**; the tallest is 264.7 px
including row gaps, comfortably inside 358. **No density collapse needed.**

> The obvious wrong formula here is `34 + sqrt(loc)/9`, which under-reserves every node by
> 10–23 px and the whole column set by 166 px (+33%), producing two columns of six that overlap
> and spill into the ruler at y = 381–392 — while every invariant asserted against that same
> formula passes. `node_h` mirrors the renderer or it is worse than useless.

`skills/` (41 `.py`, 34 near-isolated dirs, 40 `sys.path` hacks, 3 edges) and `workflows/` are
**excluded** by the declared-packages scope. Mention `skills/` once in the orientation prose as
*"a separate, script-shaped subtree"*.

**Fan-in ranking** (churn substitute, `__init__.py` under 20 loc excluded):
`registry.py` 70 · `utils/paths.py` 34 · `models/_base.py` 24.
Unfiltered, `volforecast/__init__.py` leads at 92 with 8 loc — which is why the filter exists,
and why the `volforecast` node's `top` must fall back to it rather than render empty.

## A.3 The trace — eight hops, every line verified

The most compelling path in the repo: a CLI string → argparse registration → handler → data
layer → atomic parquet write → resolved absolute path.

Checked in as `fixtures/trace.restored.json` and loaded by `compose.build_trace`. **Every hop is
one contiguous window of ≤24 lines with all of its focus lines inside it** — an anchor is a single
`start..end` range (`verify-contract.js:74` rejects a focus outside it, `:77` requires every line
in range to be bundled), so a hop specified as three scattered linenos 617 lines apart is not
expressible and fails the gate. That is why there are eight hops and not six.

| # | File | Anchor | Focus | What |
|---|---|---|---|---|
| 1 | `vol` | 308–318 | 313, 314 | `ingest-ohlcv)` → `python -m volforecast ingest-ohlcv "$@"` |
| 2 | `src/volforecast/__main__.py` | 809–815 | 809, 810 | `def main(argv)` → `parser = _build_parser()` |
| 3 | `src/volforecast/__main__.py` | 190–196 | 193, 195 | `from volforecast.cli.ingest_ohlcv import register as _reg_ingest_ohlcv` → `_reg_ingest_ohlcv(subparsers)` |
| 4 | `src/volforecast/cli/ingest_ohlcv.py` | 108–116 | 108, 112, 113 | `def register(subparsers)` → `subparsers.add_parser("ingest-ohlcv", …)` |
| 5 | `src/volforecast/cli/ingest_ohlcv.py` | 133–143 | 133, 136, 143 | `parser.set_defaults(func=handle)` → `def handle(args)` → `return run(start, end, symbols=symbols, force=args.force)` |
| 6 | `src/volforecast/cli/ingest_ohlcv.py` | 74–85 | 77, 82 | `df = fetch_ohlcv(sym, start_date, end_date)` → `save_ohlcv_cache(sym, df)` |
| 7 | `src/volforecast/data/ohlcv.py` | 180–193 | 184, 185, 193 | `df.to_parquet(tmp)` → `os.replace(tmp, str(path))` → `return path` |
| 8 | `src/volforecast/utils/paths.py` | 84–92 | 88, 90 | `def ohlcv_cache_path(symbol)` → `data_path("raw/ohlcv", f"{symbol}.parquet")` |

Every window above was read off disk at plan time; re-verify at build time, because the anchor
sha256 will catch a shift and the ledger will say so.

**`predict` goes on hops 1, 3, 6 and 7 only** — the four whose next hop is in a different file
and which are the first predict for that file (§5.7). Hops 2, 4 and 5 are followed by a hop in the
same file, which `verify-contract.js:110` rejects as trivial; hop 8 is last. **`next` goes on hops
1–7.** The `trace` narrate unit returns **eight** claims, one per hop — a mismatch renders
`esc(undefined)` inside a `.claim` span.

**Live confirmation:** `python -c "from volforecast.utils.paths import ohlcv_cache_path"` prints
`…\hackathon\restored\data\raw\ohlcv\SPX.parquet`. The terminal path is verifiable by executing
one import.

**Built-in twist for the pitch:** `cli/ingest_ohlcv.py:19` and `data/ohlcv.py:29` both do
`from volforecast.constants import FUTURES_SYMBOLS, TICKER_TO_RIC` — and
**`volforecast/constants.py` does not exist** (verified). The trace is real *and* demonstrably broken.

## A.4 Commands that will run

Measured on this box, `PYTHONIOENCODING=utf-8`.

| # | `cmd` | `cwd` | exit | ms | Renders as |
|---|---|---|---|---|---|
| 1 | `python -c "import volforecast"` | `src` | **0** | 61 | Green. The one guaranteed pass — and it only works from `src`, which *proves the source root is right* |
| 2 | `python -m volforecast --help` | `src` | **1** | 166 | **Red, with a real traceback.** `ModuleNotFoundError: No module named 'volforecast.cli.ingest_iv'`, raised from `__main__.py:158` in `_build_parser()` via `main()` at `:810`. **Verified live.** The repo's headline declared entry point is broken |
| 3 | `python workspace/lint/lint_all.py` | `.` | **1** | 2,118 | **Red.** 19 of 21 checks pass, 2 genuinely fail with a `FileNotFoundError` for the missing `src/volforecast/config.py` — tying straight back to the 14 dangling modules. 25.8 KB stdout → truncated |
| 4 | `python -m pytest --collect-only -q tests` | `src` | **2** | 2,467 | 69 collected, 13 real collection errors. **Guarded:** `import pytest` fails under `py -3.11` (verified), so this is skipped with a real reason unless a 3.12 interpreter is resolved |

**Do not plan a passing test run.** `pytest tests/` gives 13 skipped, 74 errors, 2.5 s — every
unit test is blocked at `src/tests/unit/conftest.py:45` by a module-level
`pytest.importorskip("torch")`. `py -3.11` has torch but no pytest; `py -3.12` has pytest but no
torch. **Both verified.**

**`restored/vol:23`** hard-exits with
`ERROR: ./vol requires the GS Linux Coder workspace (nix+uv). On Windows use vol.cmd…` — a great
verbatim anchor for the platform claim. Confirmed at that line.

Denied by never being on the allowlist: `uv sync` (`src/uv.toml` pins the unreachable GS Nexus
mirror), `uvx ruff` (11.4 MiB download, 219 KB output), anything reaching `pytickclient` /
`goldmansachs.pyslang` / `gs_quant` (13 files under `volforecast/`).

## A.5 Checkpoints — survey-derived keys

Every shuffle below is `random.Random(repo.commit)` (§3.6) — the one seed in the generator, a
function of the tree, so two runs of the same tree give identical option orders and identical
answer indices.

**`cp-a1` — single.** *"Which module is imported by the most others?"*
Options: the top 4 by fan-in, `__init__.py`-excluded, shuffled on the seed.
`answer` = 0-based index of `volforecast.registry`.
`provenance`: *"survey.json → edges: fan-in counted over 588 distinct file-level import edges,
package `__init__.py` excluded; options ordered by seed `repo.commit`."*
`explanation` names the winner's count (70) and the runner-up's (34, `utils/paths.py`).

**`cp-a2` — single.** *"Which file does the installed console script start in?"*
Answer: `src/volforecast/__main__.py`. Distractors: 3 real `argparse.ArgumentParser` sites from
entry-point rule 5. **Dedupe the option pool by file and remove the answer's own file first** —
the measured `ArgumentParser` sites are `__main__.py:76`, `cli/backfill_rk.py:42`,
`cli/build_features.py:22`, `cli/ingest.py:26`, `cli/refresh_ohlcv.py:46`,
`evaluation/economic_value.py:1394`, and the top entry **is the answer's own file**. Without the
dedupe the checkpoint offers the right answer twice and `verify-contract.js:113` (index-in-range
only) passes it. Five distinct non-answer files remain, so the ≥4-option precondition still holds.
`provenance`: *"src/pyproject.toml:53 [project.scripts] volforecast = volforecast.\_\_main\_\_:main"*.

**`cp-c1` — order.** *"Order these four packages from most-importing to most-depended-on."*
Options: 4 map node labels, one per column, shuffled on the seed. `true_sequence` = their column
order.
`provenance`: *"map.json → node column index: ordered by (fan-in − fan-out) over the import DAG."*

**`cp-c2` — single.** *"Which file does `ingest-ohlcv` finally write through?"*
Answer: `src/volforecast/data/ohlcv.py`. Distractors: the three other distinct `anchor.file`
values in the trace hop list (`vol`, `__main__.py`, `cli/ingest_ohlcv.py`) — which is why there
are eight hops across five files and not six across four.
`provenance`: *"fixtures/trace.restored.json → hop 7 anchor.file; `os.replace(tmp, str(path))` at
`data/ohlcv.py:185`."*
The shipped `cp-c` stop carries **two** checkpoint blocks. Both must be specified or the second
one has no answer key and the stop drops.

**Note the map-derived key.** `cp-c1`'s answer comes from `map.json`, which stage 2 produces
*after* stage 1 writes `survey.json`. Stage 2 therefore calls
`checkpoints.build_checkpoints(survey, mp) -> dict` and rewrites `survey.json` with the merged
result before narrate reads it (§2). Non-negotiable #6 still holds: the map is deterministic code,
and no model touches either pass.

```python
def order_key(options: list[str], true_sequence: list[str]) -> list[int]:
    """answer[i] = the 1-based POSITION of options[i] in the true sequence.
    The INVERSE of the naive 'list the option indices in order'."""
    return [true_sequence.index(o) + 1 for o in options]
```

**Key by position, not by value.** `options` built from trace hops can contain two equal strings —
`backfill_rk.py` alone repeats `parser.add_argument(` 96 times, and 12.4% of distinct lines in
`volforecast` repeat within their own file. `.index()` on a duplicate returns the first match,
producing a duplicated rank that fails the permutation assert and **crashes the build** instead of
degrading. Build options as `(index, text)` pairs and dedupe display text with `file:line`.

> **The shipped fixture gets this backwards.** Verified by simulation against the renderer's
> grading (`a.pick[i] === b.answer[i]`, select adjacent to `options[i]`): `cp-c1`'s
> `[3,5,2,1,4]` demands `serialize_price → PriceRequest → ENGINE.price → build_instrument →
> roll_forward`, i.e. serialization first. The real trace order gives `[4,3,1,5,2]` — and
> `[3,5,2,1,4]` is exactly its inverse permutation. `verify-contract.js:113-117` checks only that
> the answer is a permutation of 1..n, so **both gates pass it**. Fix both fixtures in stage 0.

## A.6 The pitch beats, in order

1. Point it at a repo none of us has read. Run it live: `trailhead build restored -o out.html`.
2. Open the artifact. Click **one** claim marker — the excerpt expands, real `file:line`, real code.
3. **Open the audit panel.** Show the deletions. This is the moment; everything else is setup.
4. Scroll to `python -m volforecast --help` — **exit 1, a real `ModuleNotFoundError`, shown failing
   because it did**. Then the line that lands: *"the deterministic stage found 14 modules this repo
   imports that do not exist. That is why."*
5. Close: only one of five stages calls a model. Everything that checks is ordinary code, because
   a model cannot verify itself.
