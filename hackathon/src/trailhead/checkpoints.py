"""Checkpoint answer keys — derived from `survey.json`, never from a model.

Non-negotiable #6. There is no model inside the generated page, so every
checkpoint it grades has to carry a key that ordinary deterministic code
derived from the repository, plus a `provenance` string that says on screen
which survey field the key came from. This module is that code. It is imported
by stage 1 (survey-only keys) and again by stage 2, which re-runs it with
`map.json` in hand and rewrites `survey.json` with the map-derived key merged
in **before** narrate reads it.

Two kinds, matching the renderer at `demo/trailhead-demo.html:2734-2745`:

    single   `answer` is a 0-based index into `options[]`
    order    `answer[i]` is the 1-based RANK of `options[i]` in the true order

The `order` key is the *inverse* of the naive "list the option indices in the
right order", and getting it backwards is invisible to everything mechanical:
`verify-contract.js:171-176` checks only that the answer is a permutation of
`1..n`, so a reversed key passes both gates and then marks the correct answer
wrong in front of an audience. That happened once already (decision #15), which
is why `order_key` exists exactly once, why the options are built as positions
rather than looked up by text, and why `grade_order` reproduces the renderer's
comparison verbatim so a test can drive the derivation in the grading
direction rather than only in the authoring direction.

**Nothing here fabricates an option.** §9 row 8: a checkpoint whose real option
pool is too small is DROPPED, never padded. An invented distractor inside an
artifact whose entire pitch is that it contains no fabrication is the worst bug
available. Every builder returns `None` instead and `compose.build_course`
drops the stop.

`prompt`, `provenance` and `explanation` are plain text — the renderer runs
them through `esc()`. `options[]` is the one raw-interpolation surface here
(decision #20b), so it is the one that goes through `textio.cell`.
"""
import random

from .textio import cell, esc_html

#: §9 row 8. Below this many *real* options a checkpoint is dropped, not padded.
MIN_OPTIONS = 4

#: §3.6. A package `__init__.py` this small is a re-export shelf, not a
#: dependency: `volforecast/__init__.py` has the highest fan-in in the proving
#: -ground repo (92) at 8 lines. Ranking it as "the most imported module" is
#: true and useless, so it is excluded unless it carries real code.
INIT_LOC_FLOOR = 20

#: Column separation tolerance for `_columns`. Nodes are centred inside their
#: column band, so two nodes in one column agree on their midpoint to within
#: the integer rounding of §4.2 step 5 (±1 px), while two adjacent columns are
#: separated by strictly more than `COL_GAP = 26` px — that follows from the
#: step-2 capacity bound. Any threshold in (2, 26) works; this is the middle.
COLUMN_EPS = 12.0


def build_checkpoints(survey, mp=None, *, hops=None):
    """Every answer key this repo can honestly support, keyed by checkpoint id.

    Returns a dict shaped exactly like `survey.checkpoints` — the caller merges
    it, it does not merge itself:

        survey.setdefault("checkpoints", {}).update(build_checkpoints(sv, mp))

    Called twice by design. Stage 1 has no map, calls `build_checkpoints(sv)`
    and gets the survey-only keys. Stage 2 has `map.json`, calls
    `build_checkpoints(sv, mp)` and gets those same keys plus `cp-c1`, then
    rewrites `survey.json`. The survey-only keys are re-derived identically on
    the second pass because every shuffle is seeded from `repo.commit` and the
    checkpoint id — not from a shared generator whose state depends on call
    order — so the merge is idempotent and the answer indices do not move.

    `hops` is the trace hop list (`fixtures/trace.restored.json`, the same file
    `compose.build_trace` loads) and is optional: without it `cp-c2` is not
    derivable and is omitted rather than guessed. A hop only needs a file, flat
    (`hop.file`, as the fixture specifies it) or anchored (`hop.anchor.file`,
    as stage 4 emits it). The dict wrapper the fixture ships — `{"contract":
    …, "hops": [...]}` — is unwrapped here, so the caller can pass whatever
    `json.load` returned.

    A checkpoint that cannot be derived is absent from the result. Absence is
    the signal for §9 row 8 — the stop drops, no placeholder quiz is rendered.
    """
    out = {}

    a1 = _cp_a1(survey, _rng(survey, "cp-a1"))
    if a1 is not None:
        out["cp-a1"] = a1

    a2 = _cp_a2(survey, _rng(survey, "cp-a2"))
    if a2 is not None:
        out["cp-a2"] = a2

    if mp:
        c1 = _cp_c1(mp, _rng(survey, "cp-c1"))
        if c1 is not None:
            out["cp-c1"] = c1

    steps = _hop_list(hops)
    if steps:
        c2 = _cp_c2(steps, _rng(survey, "cp-c2"))
        if c2 is not None:
            out["cp-c2"] = c2

    return out


def order_key(options, true_sequence):
    """`answer[i]` = the 1-based POSITION of `options[i]` in the true sequence.

    The inverse of the naive "list the option indices in order", and the exact
    thing `grade_order` compares against. Published here because it is the one
    piece of arithmetic in the project that is wrong in a way no gate can see.

    Both arguments are lists of the *same* display strings. `.index()` returns
    the first match, so two identical option strings would produce a duplicated
    rank and a key that is not a permutation — the builders therefore construct
    order checkpoints by position (`_order_block`) and keep display text unique,
    and this function stays a straight readable statement of the rule.
    """
    return [true_sequence.index(o) + 1 for o in options]


def grade_single(block, pick):
    """True iff `pick` grades CORRECT — `demo/trailhead-demo.html:2911` verbatim.

    The renderer does `ok = i === b.answer` where `i` is the 0-based index of
    the option the reader clicked. Reproduced here so a test can assert the
    grading direction instead of only the authoring direction (§15 risk 13).
    """
    return pick == block["answer"]


def grade_order(block, picks):
    """True iff `picks` grades CORRECT — `demo/trailhead-demo.html:2917` verbatim.

    `ok = pick.every((v, k) => v === b.answer[k])`, where `picks[k]` is the
    1-based rank the reader chose in the select sitting next to `options[k]`.
    """
    answer = block["answer"]
    return len(picks) == len(answer) and all(
        v == a for v, a in zip(picks, answer)
    )


# --- cp-a1: the most-imported module ---------------------------------------


def _cp_a1(survey, rng):
    """"Which module is imported by the most others?" — key from fan-in.

    Dropped rather than guessed in two cases. Fewer than four rankable files is
    §9 row 8. A **tie at the top** is the more interesting one: two modules with
    equal fan-in make two options correct, and the page would mark one of them
    wrong — decision #15's failure with a different cause.
    """
    ranked, source, note = _fan_in_ranking(survey)
    if len(ranked) < MIN_OPTIONS:
        return None
    if ranked[0]["fan_in"] == ranked[1]["fan_in"]:
        return None

    pool = ranked[:MIN_OPTIONS]
    winner, runner = pool[0], pool[1]
    return _single_block(
        rng,
        prompt="Which module does the rest of this repo import the most?",
        items=pool,
        display=lambda f: cell(f["display"], code=True),
        provenance=(
            f"survey.json → {source}: {winner['display']} is imported by "
            f"{winner['fan_in']} modules, the most in the repo; {note}; "
            "options shuffled deterministically by the commit seed, so a "
            "regenerated page asks the same question the same way."
        ),
        explanation=(
            f"{winner['display']} is imported by {winner['fan_in']} modules. "
            f"The next highest is {runner['display']} at {runner['fan_in']}. "
            "Whatever the rest of the repo points at is where its assumptions "
            "live: it is the thing you cannot change quietly."
        ),
    )


def _fan_in_ranking(survey):
    """Ranked "most imported" candidates, best first, with their provenance.

    `-> (entries, source phrase, exclusion note)`. Two sources, in order of
    precision:

    1. **Per file.** `files[].fan_in` when survey emits it, else the
       `modules[].top[]` rollup, which the frozen schema defines as
       `{path, fan_in}`.
    2. **Per module, from `edges[]`.** The rollup carries `commits` instead of
       `fan_in` on any repo where git history is available (decision #18 runs
       that substitution the other way round), so a file-level ranking is
       simply absent on every healthy repo. `edges[]` is frozen, always
       present, and counting distinct importers of each module is the literal
       reading of the question being asked.

    Ties break by loc descending then name, so the ranking is stable across
    machines and runs.
    """
    files = _file_fan_in_ranking(survey)
    if len(files) >= MIN_OPTIONS:
        return (
            files,
            "per-file fan-in over the import graph",
            f"package __init__.py files under {INIT_LOC_FLOOR} loc excluded",
        )
    return (
        _module_fan_in_ranking(survey),
        "edges[]: distinct importing modules per module",
        "the declared package roots themselves are excluded",
    )


def _module_fan_in_ranking(survey):
    """Modules ranked by how many distinct modules import them.

    Declared package roots are excluded for the reason `__init__.py` files are
    excluded from the file ranking: `import volforecast` lands on the root
    package, which then wins a question about where the code lives while
    telling the reader nothing about it.
    """
    roots = set((survey.get("roots") or {}).get("declared_packages") or [])
    modules = survey.get("modules") or {}

    importers = {}
    for edge in survey.get("edges") or []:
        a, b = (edge or {}).get("a"), (edge or {}).get("b")
        if not isinstance(a, str) or not isinstance(b, str) or a == b:
            continue
        importers.setdefault(b, set()).add(a)

    ranked = [
        {
            "display": mod,
            "fan_in": len(sources),
            "loc": (modules.get(mod) or {}).get("loc") or 0,
            "path": (modules.get(mod) or {}).get("path"),
        }
        for mod, sources in importers.items()
        if mod not in roots
    ]
    ranked.sort(key=lambda m: (-m["fan_in"], -m["loc"], m["display"]))
    return ranked


def _file_fan_in_ranking(survey):
    """Every in-scope file that has a fan-in, best first, `__init__` filtered."""
    by_path = {
        f["path"]: f
        for f in survey.get("files") or []
        if isinstance(f, dict) and isinstance(f.get("path"), str)
    }

    scores = {
        p: f["fan_in"] for p, f in by_path.items() if isinstance(f.get("fan_in"), int)
    }
    if not scores:
        for mod in (survey.get("modules") or {}).values():
            for entry in (mod or {}).get("top") or []:
                if not isinstance(entry, dict):
                    continue
                path, n = entry.get("path"), entry.get("fan_in")
                if isinstance(path, str) and isinstance(n, int):
                    scores[path] = max(scores.get(path, 0), n)

    ranked = []
    for path, n in scores.items():
        rec = by_path.get(path) or {}
        loc = rec.get("loc") or 0
        if path.rsplit("/", 1)[-1] == "__init__.py" and loc < INIT_LOC_FLOOR:
            continue
        ranked.append(
            {
                "path": path,
                "loc": loc,
                "fan_in": n,
                "display": rec.get("module") or path,
            }
        )

    ranked.sort(key=lambda f: (-f["fan_in"], -f["loc"], f["path"]))
    return ranked


# --- cp-a2: where the declared entry point starts ---------------------------


def _cp_a2(survey, rng):
    """"Which file does the entry point start in?" — key from `entry_points`.

    The console script wins when there is one, because that is the file a new
    joiner actually lands in; `python -m <pkg>` is the fallback. The prompt
    names the entry point, so a repo declaring several scripts still asks an
    unambiguous question.

    **The option pool is deduped by file and the answer's own file is removed
    from it first.** On the proving-ground repo the highest-ranked
    `ArgumentParser` site *is* the answer's own file, and without the dedupe
    the checkpoint offers the right answer twice — which `verify-contract.js`
    happily passes, since it only range-checks the index.
    """
    ep, answer_file = _entry_point(survey)
    if ep is None:
        return None

    seen = {answer_file}
    distractors = []
    for candidate in _distractor_files(survey):
        if candidate in seen:
            continue
        seen.add(candidate)
        distractors.append(candidate)
        if len(distractors) == MIN_OPTIONS - 1:
            break

    if len(distractors) < MIN_OPTIONS - 1:
        return None

    where = f"{ep['file']}:{ep['line']}" if ep.get("line") else ep.get("file", "")
    name = ep.get("name") or ep.get("target") or "the entry point"
    return _single_block(
        rng,
        prompt=(
            f"{name} is this repo's declared entry point. "
            "Which file does it start in?"
        ),
        items=[answer_file] + distractors,
        display=lambda p: cell(p, code=True),
        provenance=(
            f"survey.json → entry_points[{ep.get('kind')}]: {name} → "
            f"{ep.get('target') or answer_file}, declared at {where}; "
            "the distractors are other real files from this repo; "
            "options shuffled deterministically by the commit seed, so a "
            "regenerated page asks the same question the same way."
        ),
        explanation=(
            f"{where} declares it and it starts in {answer_file}. "
            "The other three are real files from this repo, not invented "
            "distractors: they are the files a reader lands in first if they "
            "follow the wrong entry point."
        ),
    )


def _entry_point(survey):
    """The entry point to ask about, and the file it starts in.

    `-> (entry_point_dict, repo-relative file) | (None, None)`. A console
    script's declared `file` is the pyproject that declares it, not the file it
    runs, so the target module is resolved against `files[].module`; the
    `module_main` entry point is both the fallback question and the fallback
    resolution.
    """
    eps = [e for e in survey.get("entry_points") or [] if isinstance(e, dict)]
    by_module = {
        f.get("module"): f.get("path")
        for f in survey.get("files") or []
        if isinstance(f, dict) and f.get("module")
    }

    for ep in eps:
        if ep.get("kind") != "console_script":
            continue
        target = (ep.get("target") or "").split(":")[0].strip()
        path = by_module.get(target)
        if path:
            return ep, path

    for ep in eps:
        if ep.get("kind") == "module_main" and ep.get("file"):
            return ep, ep["file"]

    return None, None


def _distractor_files(survey):
    """Real files a reader could plausibly land in first, best first.

    Declared entry-point sites come first — they are the honest distractors,
    and survey has already ranked them by fan-in. The `modules[].top[]` rollup
    follows (whichever metric it ranked by), then the plain file list, so a
    repo with a single declared entry point still asks a four-option question.
    Every one is a real file in this repo; nothing here is invented (§9).
    """
    out = [
        e["file"]
        for e in survey.get("entry_points") or []
        if isinstance(e, dict) and isinstance(e.get("file"), str)
        and e["file"].endswith(".py")
    ]
    for mod in (survey.get("modules") or {}).values():
        out += [
            t["path"]
            for t in (mod or {}).get("top") or []
            if isinstance(t, dict) and isinstance(t.get("path"), str)
        ]
    out += [
        f["path"]
        for f in survey.get("files") or []
        if isinstance(f, dict) and isinstance(f.get("path"), str)
    ]
    return [p for p in out if p.endswith(".py")]


# --- cp-c1: the dependency order the map already drew -----------------------


def _cp_c1(mp, rng):
    """"Order these packages from most-importing to most-depended-on."

    The key is the map's own column index, which §4.2 step 3 sorted by
    `fan_in - fan_out`: leftmost imports the most, rightmost is imported the
    most. Asking about the picture the reader just looked at is the point.

    One node per column, the largest, so the question is about layers rather
    than about siblings. Fewer than four columns is §9 row 8's "cp-c needs ≥4
    ordered items" — dropped, not padded.
    """
    columns = _columns(mp)
    if len(columns) < MIN_OPTIONS:
        return None

    picks = [
        sorted(col, key=lambda n: (-(n.get("loc") or 0), str(n.get("id"))))[0]
        for col in columns[:MIN_OPTIONS]
    ]
    first, last = picks[0], picks[-1]
    return _order_block(
        rng,
        prompt=(
            "Order these packages from the one that imports the most to the "
            "one the rest of the repo depends on the most."
        ),
        items=picks,
        display=_node_display,
        provenance=(
            "map.json → node column index: columns are ordered by "
            "(fan-in − fan-out) over the import DAG, one option per column, "
            "largest node in each; options shuffled deterministically by the "
            "commit seed, so a regenerated page asks the same question the "
            "same way."
        ),
        explanation=(
            f"{first.get('label')} sits in the leftmost column: it imports "
            f"more than it is imported by. {last.get('label')} sits in the "
            "rightmost: everything points at it and it points at nothing. "
            "That left-to-right order is the dependency order, which is why "
            "the map is laid out that way rather than alphabetically."
        ),
    )


def _node_display(node):
    """A map node as an option string — label in `<code>`, stats after it.

    Both halves are escaped by `textio` and the two tags are added here, from
    the decision #20b whitelist. The stats tail is not decoration: two import
    roots can produce two nodes with the same label, and order options must be
    distinguishable on screen as well as unique in the data.
    """
    loc = node.get("loc") or 0
    files = node.get("files") or 0
    return (
        cell(str(node.get("label", "")), code=True)
        + " · "
        + esc_html(f"{loc:,} loc, {files} files")
    )


def _columns(mp):
    """The map's nodes grouped into columns, left to right.

    Uses an explicit `col` key when the mapper emits one. Otherwise the columns
    are recovered from geometry: `map@1` is frozen and carries only the nine
    render fields, and each node is centred inside its column band, so node
    midpoints cluster per column with `COLUMN_EPS` of slack.
    """
    nodes = [n for n in (mp.get("nodes") or []) if isinstance(n, dict)]
    if not nodes:
        return []

    if all(isinstance(n.get("col"), int) for n in nodes):
        groups = {}
        for n in nodes:
            groups.setdefault(n["col"], []).append(n)
        return [groups[c] for c in sorted(groups)]

    ordered = sorted(nodes, key=lambda n: (_mid(n), str(n.get("id"))))
    columns, current = [], [ordered[0]]
    for previous, node in zip(ordered, ordered[1:]):
        if _mid(node) - _mid(previous) > COLUMN_EPS:
            columns.append(current)
            current = []
        current.append(node)
    columns.append(current)
    return columns


def _mid(node):
    return float(node.get("x") or 0) + float(node.get("w") or 0) / 2.0


# --- cp-c2: where the traced chain ends -------------------------------------


def _cp_c2(steps, rng):
    """"Which file does the traced chain end in?" — key from the hop list.

    The answer is the last hop's `anchor.file` and the prompt asks exactly
    that, so the key is correct by construction on any hop list rather than
    only on the one the demo ships. The distractors are the other files in the
    same trace, nearest the end first: every one is a real hop the reader is
    about to walk, and picking one is the mistake of stopping a hop early.
    """
    files = []
    for hop in steps:
        path = _hop_file(hop)
        if isinstance(path, str) and path not in files:
            files.append(path)

    if len(files) < MIN_OPTIONS:
        return None

    answer = files[-1]
    distractors = list(reversed(files[:-1]))[: MIN_OPTIONS - 1]
    return _single_block(
        rng,
        prompt=(
            f"The trace starts in {files[0]} and crosses {len(files)} files. "
            "Which one does the chain end in?"
        ),
        items=[answer] + distractors,
        display=lambda p: cell(p, code=True),
        provenance=(
            f"trace hops → hop {len(steps)} of {len(steps)}, its file = "
            f"{answer}; every hop is anchored to a line range and sha256-"
            "verified in the ledger; options shuffled deterministically by "
            "the commit seed, so a regenerated page asks the same question "
            "the same way."
        ),
        explanation=(
            f"The chain ends in {answer}. The other three options are real "
            "hops in the same trace, earlier in the chain: each is where the "
            "chain would appear to end if you stopped following it one call "
            "too soon."
        ),
    )


# --- block construction -----------------------------------------------------


def _single_block(rng, *, prompt, items, display, provenance, explanation):
    """A `kind="single"` block. `items[0]` is the answer; the rest are wrong.

    The shuffle is applied to positions, and the answer index is read back off
    the permutation, so the key can never disagree with the option order.
    """
    perm = _permutation(rng, len(items))
    return {
        "kind": "single",
        "prompt": prompt,
        "options": [display(items[j]) for j in perm],
        "answer": perm.index(0),
        "provenance": provenance,
        "explanation": explanation,
    }


def _order_block(rng, *, prompt, items, display, provenance, explanation):
    """A `kind="order"` block. `items` is already in the TRUE order.

    `answer[i]` is the 1-based rank of `options[i]` — built from the
    permutation rather than by looking the option text back up, so two options
    that render identically still produce a real permutation instead of a
    duplicated rank and a crashed build (Appendix A.5).
    """
    perm = _permutation(rng, len(items))
    return {
        "kind": "order",
        "prompt": prompt,
        "options": [display(items[j]) for j in perm],
        "answer": [j + 1 for j in perm],
        "provenance": provenance,
        "explanation": explanation,
    }


def _permutation(rng, n):
    perm = list(range(n))
    rng.shuffle(perm)
    return perm


def _rng(survey, cp_id):
    """The one seed (§3.6), split per checkpoint.

    `random.Random(repo.commit)` is a function of the tree, so two runs of the
    same tree give identical option orders and identical answer indices, and
    the localStorage contract survives a regeneration. Mixing the checkpoint id
    into the seed instead of threading one generator through every builder is
    what makes stage 2's re-run reproduce stage 1's keys exactly: order of
    construction stops mattering.
    """
    commit = (survey.get("repo") or {}).get("commit") or ""
    return random.Random(f"{commit}\x00{cp_id}")


def _hop_list(hops):
    """The hop list out of whatever the caller loaded off disk."""
    if isinstance(hops, dict):
        hops = hops.get("hops") or hops.get("steps") or []
    return [h for h in hops or [] if isinstance(h, dict)]


def _hop_file(hop):
    """The repo-relative file a hop points at, either side of stage 4.

    `fixtures/trace.restored.json` specifies a hop flat — `file`, `start`,
    `end`, `focus_lines` — because it is written before any anchor exists;
    `verify.py` later emits the same hop as a trace step with an `anchor`
    object carrying the sha256. Both shapes reach this module depending on who
    calls it, and reading only one of them drops `cp-c2` in silence.
    """
    hop = hop or {}
    return hop.get("file") or (hop.get("anchor") or {}).get("file")
