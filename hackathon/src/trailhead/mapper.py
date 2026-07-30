"""Stage 2 — MAP. Deterministic. No model.

Reads `survey.json`, collapses every in-scope file down to at most `MAP_CAP`
node groups, lays those groups out in the renderer's coordinate space, and
emits `map.json` (`trailhead/map@1`).

Two things make this stage worth testing rather than eyeballing.

**The canvas is hard-coded.** `demo/trailhead-demo.html` draws
`viewBox="0 0 900 400"` with a decorative ruler at y = 381-392, and it has no
layout engine, no zoom and no pan (decision #17 cut the dynamic viewBox:
`.mapbox svg{width:100%}` means a wider viewBox zooms *out* rather than gaining
space). Every coordinate is final at generation time, so a node that does not
fit is a node drawn through the ruler in front of the judges.

**`node_h` mirrors the renderer.** `H_BASE`/`H_DIV` are copied verbatim from
`const h=n=>44+Math.sqrt(n.loc)/6;` in the template. The obvious wrong formula,
`34 + sqrt(loc)/9`, under-reserves the demo repo's twelve nodes by 166 px (+33%)
— and every invariant asserted against that same wrong formula still passes
while the browser clips. That is why `node_h` is the only height definition in
the project, and why the packing *and* the invariants both call it.

Nothing here calls a model: `why` and `top` are deterministic templates over
`survey.json` (decisions #19 and #20c), which is what makes them legal on a
surface that has no claim marker.
"""
import math
import re

#: The density cap (decision #16 — 14, not spec §4.4's 40). 900x400 with node
#: widths around 142 holds five columns of six; 40 nodes is 71% fill on a canvas
#: with no zoom, no pan and no density collapse in the page.
MAP_CAP = 14

W, H = 900.0, 400.0
X_PAD = 8.0
Y_TOP, Y_BOT = 10.0, 368.0
BAND = Y_BOT - Y_TOP                 # 358.0 — the vertical space a column may use
COL_GAP = 26.0
ROW_GAP = 13.0
EDGE_CAP = 48
W_MAX = 300.0                        # node width clamp — see §4.2 step 1

#: THE renderer's rect height, `demo/trailhead-demo.html`'s
#: `const h=n=>44+Math.sqrt(n.loc)/6;`. Read through `node_h`, never inlined.
H_BASE, H_DIV = 44.0, 6.0

#: Usable width once both side pads are taken: the number every column-capacity
#: sum is measured against.
CANVAS_INNER = W - 2 * X_PAD         # 884.0

#: A gutter wider than this looks like a bug rather than a layout, so §4.2 step 4
#: widens the column count until the gutter drops under it.
GUTTER_MAX = 3 * COL_GAP             # 78.0

#: The tightest row gap the packing will accept before it declares a column
#: overfull and asks for another column (or, failing that, a density merge).
MIN_ROW_GAP = 2.0

#: Bottom of the drawable area. The ruler lives at y = 381-392, so a rect may
#: reach 372 and no further.
Y_CLEAR = 372.0

#: Below this the generator emits a table and a callout instead of a graph
#: (§4.4 / §9 row 4). The nodes are still laid out and still shipped — the
#: renderer does `D.map.nodes.map(...)` unconditionally.
MIN_GRAPH_NODES = 3

#: Deepest adaptive-depth probe. Nothing measured needs more than 3.
MAX_DEPTH = 8

#: Longest label that still fits `W_MAX` under `node_w`'s label term.
LABEL_MAX = int((W_MAX - 22.0) / 6.9)     # 40

#: The renderer interpolates `n.label` into SVG `<text>` unescaped, so a stray
#: `<` or `&` breaks the whole map rather than one cell. Whitelist, not blacklist.
_LABEL_BAD = re.compile(r"[^A-Za-z0-9_./+-]")

_SLUG_BAD = re.compile(r"[^a-z0-9]+")


class LayoutError(ValueError):
    """A geometry invariant in §4.3 failed.

    Raised by `check_invariants`, which `build_map` calls before returning. A
    map that cannot be drawn correctly is a generation failure, not something to
    discover in the browser at hour 9 — see §15 risk 4.
    """


# ---------------------------------------------------------------- primitives

def node_w(label: str, loc: int, files: int) -> int:
    """Width of a node's rect, in the renderer's units.

    The renderer draws the label at `600 11.5px mono` and the stats line at
    `10px mono`, both starting at `x+11`, and clips neither — so the width has
    to cover whichever of the two strings is longer, plus the padding either
    side. The shipped fixture's `risk` node already overflows by ~5 px under
    this formula, which is the measurement that produced the constants.

    The `W_MAX` clamp is not decoration. Without it one long label makes
    `max_w > 442`, no column count satisfies the capacity rule, `Cmax` falls to
    0, and both the placement walk and the `x + w <= 900` invariant break.
    `build_map` middle-ellipsises the label when the clamp bites.
    """
    stats = f"{loc:,} loc · {files} files"
    return math.ceil(min(W_MAX, 22 + max(6.9 * len(label), 6.0 * len(stats))))


def node_h(loc: int) -> float:
    """Height of a node's rect. THE height definition — there is no other.

    Identical to the renderer's `h()`. We reserve exactly what the browser
    draws, never an approximation of it: an invariant asserted against a
    different formula passes in Python while the page clips, which is strictly
    worse than not asserting at all.
    """
    return H_BASE + math.sqrt(max(0, loc)) / H_DIV


def order_nodes(ids, fan_in, fan_out, loc) -> list:
    """Left-to-right order: importers first, libraries last.

    Ascending by `(fan_in - fan_out, -loc, id)`. A pure importer (high fan-out,
    zero fan-in) is most negative and sits leftmost; a pure library is most
    positive and sits rightmost.

    This is mandatory, not cosmetic. The renderer draws each edge from
    `a.x + a.w` to `b.x` and **`a` imports `b`**, so an edge whose target sits
    to the left backtracks into a horizontal S across the canvas. Ordering by
    net fan is what makes most edges point rightward in the first place; §4.2
    step 7 drops the ones that still do not.
    """
    return sorted(
        ids,
        key=lambda i: (fan_in.get(i, 0) - fan_out.get(i, 0), -loc.get(i, 0), i),
    )


def pack_columns(order, heights, widths, C: int) -> dict:
    """Balance `order` into exactly `C` columns. Returns id -> column index.

    Greedy height-balanced line-break: walk the ordered list and open a new
    column when the accumulated height would pass `target * 1.02`, where
    `target = sum(h) / C`. The last column takes whatever is left, which is why
    the caller checks every column against the band afterwards rather than
    trusting the average.

    Called once per candidate `C` by the §4.2 step-4 walk. `widths` is accepted
    and deliberately unused: the balance is by height only — width has already
    had its say in `Cmax`, which bounds `C`.
    """
    ids = list(order)
    if C <= 1 or not ids:
        return {i: 0 for i in ids}

    target = sum(heights[i] for i in ids) / C
    col, c, acc = {}, 0, 0.0
    for i in ids:
        h = heights[i]
        if acc > 0 and acc + h > target * 1.02 and c < C - 1:
            c += 1
            acc = 0.0
        col[i] = c
        acc += h
    return col


def place(col, order, widths, heights) -> dict:
    """Turn a column assignment into coordinates. Returns id -> {x, y, col}.

    Horizontally: each column is as wide as its widest node, the leftover space
    is split evenly between the columns, and every node is centred in its own
    column's width.

        gap = 0.0 if C < 2 else (W - 2*X_PAD - sum(colw)) / (C - 1)

    The `C - 1` guard is not optional. Any repo whose module graph has no
    internal edges lays out in a single column — reproduced on `qrt` (7 loose
    `.py`, 0 internal references), which is a named acceptance repo — and a bare
    division there raises `ZeroDivisionError` during generation.

    Vertically: the same guard for the same reason. The greedy line-break
    routinely leaves the last column holding one node, so the row gap divides by
    `max(1, n - 1)`. When the natural `ROW_GAP` does not fit, the gap shrinks to
    whatever the band allows, floored at `MIN_ROW_GAP`.

    One deliberate exception to "centre within the column": when there is only
    one column, the gap is 0 by definition, so the column is centred on the
    canvas rather than parked against `X_PAD`. Otherwise every small repo — 3
    nodes is the expected count on a named acceptance repo — renders as a strip
    hugging the left edge of a 900-unit canvas with 750 units of nothing beside
    it. The invariants are unaffected: `w <= W_MAX` keeps `x` positive.
    """
    ids = [i for i in order if i in col]
    if not ids:
        return {}

    used = sorted({col[i] for i in ids})
    members = [[i for i in ids if col[i] == c] for c in used]
    colw = [max(widths[i] for i in m) for m in members]
    n_col = len(used)
    gap = 0.0 if n_col < 2 else (CANVAS_INNER - sum(colw)) / (n_col - 1)

    out = {}
    for k, m in enumerate(members):
        if n_col == 1:
            cx = (W - colw[k]) / 2.0
        else:
            cx = X_PAD + sum(colw[:k]) + k * gap

        hs = [heights[i] for i in m]
        n = len(m)
        total = sum(hs)
        rg = (ROW_GAP if total + (n - 1) * ROW_GAP <= BAND
              else max(MIN_ROW_GAP, (BAND - total) / max(1, n - 1)))
        block = total + (n - 1) * rg
        y = Y_TOP + max(0.0, (BAND - block) / 2.0)

        for i in m:
            out[i] = {
                "x": int(round(cx + (colw[k] - widths[i]) / 2.0)),
                "y": int(round(y)),
                "col": k,
            }
            y += heights[i] + rg
    return out


# ------------------------------------------------------------------ collapse

def _norm_dir(p) -> str:
    """A repo-relative directory key: forward slashes, no leading or trailing one.

    `""` is the repo root itself and is a legal key — it is the group a flat
    repo's loose `.py` files land in.
    """
    s = str(p or "").replace("\\", "/").strip()
    while s.startswith("./"):
        s = s[2:]
    s = s.strip("/")
    return "" if s == "." else s


def _under(path: str, root: str) -> bool:
    """Is `path` `root` itself or inside it? `""` contains everything."""
    return root == "" or path == root or path.startswith(root + "/")


def _rel(path: str, root: str) -> str:
    """`path` expressed relative to `root`. Both already `_norm_dir`-ed."""
    if root == "":
        return path
    if path == root:
        return ""
    return path[len(root) + 1:]


def _parts(rel: str) -> tuple:
    return tuple(rel.split("/")) if rel else ()


def _group_path(key) -> str:
    """The repo-relative path a group key names.

    Almost always a directory. A key that has not been merged yet can still
    name a single file (`src/cli.py`), which is deliberate — that is the key
    rule 3 folds into its parent.
    """
    ir, parts = key
    tail = "/".join(parts)
    if not ir:
        return tail
    return ir + "/" + tail if tail else ir


def _node_id(path: str, used: set) -> str:
    """`slug("n-" + repo-relative POSIX path)`, deduped with a numeric suffix.

    Ids derive from the path and never from the dotted module name: dotted names
    collide (`inspect` occurs twice in the proving-ground repo) and a collision
    would silently merge two unrelated modules into one node, while
    `verify-contract.js` only checks duplicate *stop* ids.
    """
    body = _SLUG_BAD.sub("-", path.lower()).strip("-")
    base = "n-" + (body or "root")
    out, n = base, 1
    while out in used:
        n += 1
        out = f"{base}-{n}"
    used.add(out)
    return out


def _sanitise_label(label: str) -> str:
    out = _LABEL_BAD.sub("", label)
    return out or "."


def _ellipsise(label: str, cap: int = LABEL_MAX) -> str:
    """Middle-ellipsise with three dots — inside the SVG-safe whitelist."""
    if len(label) <= cap:
        return label
    keep = max(2, cap - 3)
    head = (keep + 1) // 2
    return label[:head] + "..." + label[len(label) - (keep - head):]


def _label_of(key, declared) -> str:
    """The group's path relative to its import root, minus the package prefix.

    §4.1's examples are `data`, `models`, `cli`, `tests` — **not**
    `volforecast/data` — so the declared package's own name comes off when
    something is left underneath it. This is not cosmetic. Label length sets
    `w` and `w` sets the column count: `volforecast/visualization` (25 ch)
    needs `w≈195` and gives 4 columns, `visualization` (13 ch) needs `w≈142`
    and gives 5. Label choice **is** the layout algorithm.

    The package root keeps its own name (`volforecast`), and a repo with no
    declared packages keeps the full relative path (`cogs`, `src/api`, `.`).
    """
    ir, parts = key
    if declared and len(parts) > 1 and parts[0] in declared:
        parts = parts[1:]
    return _sanitise_label("/".join(parts) or ir or ".")


def _lookup(key_parts, ir, groups):
    """The group owning `ir/key_parts` — the longest prefix that is a group.

    Group keys are component-prefixes of file paths, so a containing group is
    found by shortening the path one component at a time. Component-wise, never
    string-wise: `src/cli.py` is not inside `src/cli.pyx`.
    """
    for n in range(len(key_parts), -1, -1):
        k = (ir, tuple(key_parts[:n]))
        if k in groups:
            return k
    return None


def collapse(sv: dict, cap: int = MAP_CAP):
    """Files -> node groups. Returns `(groups, edges, diagnostics)`.

    `groups` is keyed by node id and carries the raw facts a node is built from
    (`label`, `path`, `files`, `loc`, `modules`, `paths`, `is_test`).
    `edges` is `{(a_id, b_id): n}` with self-edges dropped and `n` already
    capped at `EDGE_CAP`. `diagnostics` is the counter bag that ends up in
    `map.json`.

    **The unit being grouped is a file path, not a module rollup.** That is what
    §4.1's measurements describe: depth 2 on the proving-ground repo gives 26
    groups "of which 13 are loose `tests/*.py`", which only happens if
    `tests/test_models.py` and `tests/test_features.py` are distinct depth-2
    keys — they share a directory and differ only in their file name. Grouping
    directories instead gives 23 keys, picks the wrong depth, and produces a
    different map from the one Appendix A measured. It is also the only reading
    under which `loc` is unambiguously recursive and per-file (§3.9: "nothing
    downstream takes `modules` where it needs per-file signals").

    Four rules, in this order:

    1. **Test roots collapse to one node, always, before anything else.**
       Forcing tests to depth 1 takes that 26 down to 14 — 13 package keys plus
       one `tests`, which is the right architecture picture.
    2. **Adaptive depth for everything else.** A fixed depth is wrong at both
       ends: depth 1 gives 2 useless nodes, depth 3 gives 331.
    3. **Merge-smallest, unconditionally**, while any group holds a single file
       and has a mergeable parent — then again while the count exceeds `cap`.
       This is what turns the three depth-2 keys `volforecast`,
       `volforecast/__main__` and `volforecast/registry` into the single
       package-root node Appendix A.2 measured, and it takes 14 groups to 12.
    4. **Scope is the declared distribution packages plus the test root.** When
       nothing is declared, scope instead to everything under an import root.
       Without that fallback the scope is empty on two of four fixture repos and
       two of three real acceptance repos, `map.nodes` is `[]` everywhere, and
       the map is never exercised on a repo with real git history.
    """
    modules = sv.get("modules") or {}
    files = [f for f in (sv.get("files") or []) if isinstance(f, dict)]
    roots = sv.get("roots") or {}

    import_roots = sorted(
        {_norm_dir(r) for r in (roots.get("import_roots") or [""])},
        key=lambda r: (-len(r), r),
    )
    test_roots = sorted(
        {_norm_dir(r) for r in (roots.get("test_roots") or []) if _norm_dir(r)},
        key=lambda r: (-len(r), r),
    )
    declared = {str(p) for p in (roots.get("declared_packages") or []) if str(p)}

    diag = {
        "modules_in": len(modules),
        "groups": 0,
        "hidden_modules": 0,
        "cycles_broken": 0,
        "edges_dropped_backward": 0,
        "edge_cap_hits": 0,
        "density_merges": 0,
        "depth": 1,
        "scope": "declared_packages" if declared else "under_import_root",
        "collapse_merges": 0,
        "groups_dropped": 0,
        "files_out_of_scope": 0,
        "edges_out_of_scope": 0,
        "labels_clamped": 0,
    }

    # --- 1/4: scope every file, and pin the test root to one key ------------
    units = []
    for f in files:
        rel = _norm_dir(f.get("path") or "")
        if not rel:
            continue
        ir = next((r for r in import_roots if _under(rel, r)), None)
        if ir is None:
            diag["files_out_of_scope"] += 1
            continue

        troot = next((t for t in test_roots if _under(rel, t)), None)
        if troot is not None:
            tir = next((r for r in import_roots if _under(troot, r)), ir)
            units.append({"ir": tir, "parts": _parts(_rel(rel, tir)),
                          "fixed": (tir, _parts(_rel(troot, tir))),
                          "n": 1, "loc": int(f.get("loc") or 0), "file": f})
            continue

        parts = _parts(_rel(rel, ir))
        if declared and (not parts or parts[0] not in declared):
            diag["files_out_of_scope"] += 1
            continue
        units.append({"ir": ir, "parts": parts, "fixed": None,
                      "n": 1, "loc": int(f.get("loc") or 0), "file": f})

    if not units and modules:
        # A survey with rollups but no file rows — only ever a hand-written
        # fixture, since stage 1 lists every in-scope `.py`. Group the rollups
        # instead of reporting an empty map.
        for dotted in sorted(modules):
            info = modules.get(dotted) or {}
            rel = _norm_dir(info.get("path") or "")
            ir = next((r for r in import_roots if _under(rel, r)), None)
            if ir is None:
                continue
            troot = next((t for t in test_roots if _under(rel, t)), None)
            parts = _parts(_rel(rel, ir))
            if troot is None and declared and (not parts or parts[0] not in declared):
                continue
            fixed = None
            if troot is not None:
                tir = next((r for r in import_roots if _under(troot, r)), ir)
                fixed = (tir, _parts(_rel(troot, tir)))
            units.append({"ir": ir, "parts": parts, "fixed": fixed,
                          "n": int(info.get("files") or 1),
                          "loc": int(info.get("loc") or 0), "file": None})

    # --- 2/4: adaptive depth -------------------------------------------------
    def keys_at(d):
        out = {}
        for i, u in enumerate(units):
            out.setdefault(u["fixed"] or (u["ir"], u["parts"][:d]), []).append(i)
        return out

    groups = keys_at(1)
    depth = 1
    for d in range(2, MAX_DEPTH + 1):
        nxt = keys_at(d)
        if len(nxt) > len(groups) and len(nxt) <= cap * 2:
            groups, depth = nxt, d
        else:
            break
    diag["depth"] = depth

    test_keys = {u["fixed"] for u in units if u["fixed"] is not None}
    rollup_at = {}
    for dotted, info in modules.items():
        rollup_at.setdefault(_norm_dir((info or {}).get("path") or ""), []).append(dotted)

    # --- 3/4: merge smallest -------------------------------------------------
    def stats(key):
        return (sum(units[i]["n"] for i in groups[key]),
                sum(units[i]["loc"] for i in groups[key]))

    def mergeable(key):
        # The test node is a deliberate architectural node, not an accident of
        # depth, and never merges away. Everything else merges into its parent
        # path, which is created if it does not exist yet — that is how three
        # loose files at a package root become one node, and how a flat repo's
        # loose scripts become the `.` node instead of one node each.
        return key not in test_keys and bool(key[1])

    def merge(victim):
        ir, parts = victim
        parent = (ir, parts[:-1])
        groups.setdefault(parent, []).extend(groups.pop(victim))
        groups[parent].sort()

    def really_one_file(key):
        """Both the file rows and the module rollup call this a single file.

        The rollup is a veto, never a source of counts. `files` is defined as
        every in-scope `.py`, so the file rows are authoritative on a real
        survey — but a hand-written fixture carrying 10 of 68 rows would report
        six healthy modules as single files and merge four of them away. A
        rollup can only ever *stop* a merge here, so it cannot inflate a count
        however it was computed.
        """
        rolled = [modules.get(m) or {} for m in rollup_at.get(_group_path(key), [])]
        return not rolled or max(int(r.get("files") or 0) for r in rolled) <= 1

    while True:
        singles = [k for k in groups
                   if stats(k)[0] == 1 and really_one_file(k) and mergeable(k)]
        if not singles:
            break
        merge(min(singles, key=lambda k: (stats(k), k)))
        diag["collapse_merges"] += 1

    while len(groups) > cap:
        cands = [k for k in groups if mergeable(k)]
        if not cands:
            break
        merge(min(cands, key=lambda k: (stats(k), k)))
        diag["collapse_merges"] += 1

    if len(groups) > cap:
        # Nothing left to merge into — every group is already top-level. Keep
        # the largest `cap` and count the rest rather than drawing a canvas
        # nobody can read.
        keep = sorted(groups, key=lambda k: (-stats(k)[1], -stats(k)[0], k))[:cap]
        diag["groups_dropped"] = len(groups) - len(keep)
        groups = {k: groups[k] for k in keep}

    # --- 4/4: identity, labels, facts ---------------------------------------
    used_ids, out_groups, id_of_key = set(), {}, {}
    for key in sorted(groups, key=lambda k: (_group_path(k), k)):
        gpath = _group_path(key)
        nid = _node_id(gpath, used_ids)
        n_files, loc = stats(key)
        out_groups[nid] = {
            "id": nid,
            "label": _label_of(key, declared),
            "path": gpath,
            "files": n_files,
            "loc": loc,
            "modules": [],
            "paths": [_norm_dir(units[i]["file"]["path"]) for i in groups[key]
                      if units[i]["file"] is not None],
            "is_test": key in test_keys,
            "import_root": key[0],
        }
        id_of_key[key] = nid

    # Modules are attached by directory, not by name: a module's `path` is its
    # directory, so the group that owns it is the longest group key that is a
    # prefix of that directory. This is the only place `modules` is consulted
    # for structure, and it is what resolves the import edges.
    group_of_module = {}
    for dotted in sorted(modules):
        mpath = _norm_dir((modules.get(dotted) or {}).get("path") or "")
        ir = next((r for r in import_roots if _under(mpath, r)), None)
        if ir is None:
            continue
        key = _lookup(_parts(_rel(mpath, ir)), ir, groups)
        if key is None:
            continue
        group_of_module[dotted] = id_of_key[key]
        out_groups[id_of_key[key]]["modules"].append(dotted)

    # --- edges ---------------------------------------------------------------
    raw = {}
    for e in sv.get("edges") or []:
        a = group_of_module.get(e.get("a"))
        b = group_of_module.get(e.get("b"))
        if a is None or b is None:
            diag["edges_out_of_scope"] += 1
            continue
        if a == b:
            continue                                  # self-edge, never drawn
        raw[(a, b)] = raw.get((a, b), 0) + int(e.get("n") or 0)

    edges = {}
    for (a, b), n in raw.items():
        if n > EDGE_CAP:
            diag["edge_cap_hits"] += 1
        # Stroke width is `0.7 + n/16` with no clamp in the renderer, so a raw
        # 214 draws a 14 px band across a 400-unit canvas. The cap is stated in
        # the map stop caption.
        edges[(a, b)] = min(n, EDGE_CAP)

    diag["cycles_broken"] = sum(
        1 for (a, b) in edges if a < b and (b, a) in edges
    )
    diag["groups"] = len(out_groups)
    diag["hidden_modules"] = max(0, diag["modules_in"] - len(out_groups))
    return out_groups, edges, diag


# ------------------------------------------------------------ node narration

def _rank_label(sv: dict) -> str:
    """`commits` when git history exists, `fan-in (no git history)` otherwise.

    The drawer's heading is hard-coded `MOST-EDITED FILES` in the renderer, so
    the substitution has to be visible *inside the strings* or the page states a
    falsehood on every node drawer (decision #18).
    """
    return "commits" if _churn_available(sv) else "fan-in (no git history)"


def _churn_available(sv: dict) -> bool:
    churn = sv.get("churn")
    if isinstance(churn, dict) and "available" in churn:
        return bool(churn["available"])
    # No `churn` key at all (hand-written fixtures): infer from the per-file
    # signal rather than declaring history missing and mislabelling every row.
    return any(f.get("commits") is not None for f in (sv.get("files") or []))


def _rank_files(group: dict, sv: dict, files_by_path: dict, label: str):
    """Ranked `(path, value, label)` for one group's busiest files.

    Rank unfiltered, drop sub-20-loc `__init__.py` files, and **if that empties
    the list, fall back to the unfiltered ranking**. The group holding only the
    package root on the proving-ground repo is a single 8-line `__init__.py`
    with the highest fan-in in the repo (92); under a bare exclusion its `top`
    is `[]`, and that node sits at the far right of the map — the first one a
    judge clicks — rendering an empty `MOST-EDITED FILES` heading.
    """
    rows, lab = [], label
    if label == "commits":
        rows = [(p, int(files_by_path[p].get("commits") or 0))
                for p in group["paths"]
                if p in files_by_path and files_by_path[p].get("commits") is not None]

    if not rows:
        # fan-in lives on the module rollup's `top`, not on the file rows.
        seen = set()
        for m in group["modules"]:
            for t in ((sv.get("modules") or {}).get(m) or {}).get("top") or []:
                p = _norm_dir(t.get("path") or "")
                if not p or p in seen:
                    continue
                v = t.get("fan_in", t.get("commits"))
                if v is None:
                    continue
                seen.add(p)
                rows.append((p, int(v)))

    if not rows:
        rows = [(p, int(files_by_path[p].get("loc") or 0))
                for p in group["paths"] if p in files_by_path]
        lab = "loc"

    if not rows:
        # A group always holds at least one module, but a survey with no file
        # rows at all still may not name a file. `top` is never empty.
        return [(group["path"] or group["label"], group["loc"], "loc")]

    def tiny_init(p):
        if not p.endswith("__init__.py"):
            return False
        loc = (files_by_path.get(p) or {}).get("loc")
        return loc is not None and int(loc) < 20

    kept = [r for r in rows if not tiny_init(r[0])] or rows
    kept.sort(key=lambda r: (-r[1], r[0]))
    return [(p, v, lab) for p, v in kept]


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] if "/" in path else path


def _why(group: dict, out_n: int, in_n: int, ranked, label: str, full: str) -> str:
    """One deterministic sentence per node (decision #19 cut the model call).

    It reads as prose, but every number in it is re-derivable from
    `survey.json` — which is what makes it legal on a surface that has no claim
    marker and no anchor.

    `label` is what the SVG will draw and `full` is the group's real name. When
    the `W_MAX` clamp has ellipsised the label, the full name goes here: it is
    the only surface left that can carry it, since the drawer's `<h4>` renders
    `n.label` too.
    """
    path, value, metric = ranked[0]
    why = (f"{group['files']} files, {group['loc']:,} loc. "
           f"Imports {out_n} of these; imported by {in_n}. "
           f"Busiest file: {_basename(path)} ({metric} {value}).")
    if full != label:
        why += f" Full name: {full}."
    return why


# -------------------------------------------------------------------- layout

def _capacity(max_w: float) -> int:
    """`Cmax` — the most columns this widest node allows.

    `max C such that (C+1)*max_w + C*COL_GAP <= 884`, floored at 1. The floor is
    what makes the placement walk total: with `W_MAX = 300` the real answer is
    never 0, but the floor costs one `max()` and removes a whole failure mode.
    """
    best = 1
    for c in range(1, 21):
        if (c + 1) * max_w + c * COL_GAP <= CANVAS_INNER:
            best = c
        else:
            break
    return max(1, best)


def _fits(col, heights) -> bool:
    """Can every column hold its nodes inside the band at the minimum row gap?"""
    per = {}
    for i, c in col.items():
        per.setdefault(c, []).append(heights[i])
    for hs in per.values():
        if sum(hs) + (len(hs) - 1) * MIN_ROW_GAP > BAND:
            return False
    return True


def _gutter(col, widths) -> float:
    per = {}
    for i, c in col.items():
        per.setdefault(c, []).append(widths[i])
    if len(per) < 2:
        return 0.0
    return (CANVAS_INNER - sum(max(v) for v in per.values())) / (len(per) - 1)


def _lay_out(order, widths, heights, force: bool = False):
    """Choose a column count, pack, and place. `None` if nothing fits.

    Walk `C` from `C_min` up to `Cmax` and take the first whose gutter is at
    most `3 * COL_GAP`; if none qualifies, take the widest that still fits.
    Without the widening walk the proving-ground repo's twelve nodes give
    `C_min = 3` and a 223 px gutter between 142 px nodes — technically valid,
    and it looks like a bug. With it, `C = 4` and the gutter is 103 px.

    `force` spreads the nodes over `Cmax` columns without checking that they
    fit. It is only used once the graph has already been abandoned for a table,
    so that the coordinates in `map.json` are still sane numbers rather than
    a stack running off the bottom of a canvas nobody draws.
    """
    if not order:
        return {}, {}, 0

    n = len(order)
    total = sum(heights[i] for i in order)
    c_min = max(1, math.ceil((total + (n - 1) * ROW_GAP) / BAND))
    c_max = _capacity(max(widths[i] for i in order))

    if force:
        col = pack_columns(order, heights, widths, c_max)
        return col, place(col, order, widths, heights), len({*col.values()})

    chosen = None
    for c in range(c_min, c_max + 1):
        col = pack_columns(order, heights, widths, c)
        if not _fits(col, heights):
            continue
        chosen = col
        if _gutter(col, widths) <= GUTTER_MAX:
            break
    if chosen is None:
        return None
    return chosen, place(chosen, order, widths, heights), len({*chosen.values()})


# ---------------------------------------------------------------- invariants

def check_invariants(nodes, edges) -> None:
    """Every hard invariant in §4.3, asserted on the emitted payload.

    Both height checks call `node_h`, never a literal: asserting an inlined
    formula that under-reserves is worse than not asserting, because it passes
    in Python while the browser clips.
    """
    fields = ("id", "label", "loc", "files", "x", "y", "w", "why", "top")
    ids = set()
    for n in nodes:
        missing = [f for f in fields if f not in n]
        if missing:
            raise LayoutError(f"node {n.get('id')!r} missing fields {missing}")
        if n["id"] in ids:
            raise LayoutError(f"duplicate node id {n['id']!r}")
        ids.add(n["id"])
        if not n["top"]:
            raise LayoutError(f"node {n['id']!r} has an empty top[]")
        x, y, w = n["x"], n["y"], n["w"]
        h = node_h(n["loc"])
        if x < 0 or x + w > W:
            raise LayoutError(f"node {n['id']!r} spills the canvas: x={x} w={w}")
        if y < 0 or y + h > Y_CLEAR:
            raise LayoutError(
                f"node {n['id']!r} spills the band: y={y} h={h:.1f} > {Y_CLEAR}"
            )

    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                    and a["y"] < b["y"] + node_h(b["loc"])
                    and b["y"] < a["y"] + node_h(a["loc"])):
                raise LayoutError(f"nodes {a['id']!r} and {b['id']!r} overlap")

    for e in edges:
        if e["a"] not in ids or e["b"] not in ids:
            raise LayoutError(f"edge {e['a']}->{e['b']} names a node that is not emitted")


# ----------------------------------------------------------------- build_map

def _measure(groups, gedges, diag) -> dict:
    """Everything the layout needs, derived from one group set.

    Recomputed from scratch after a density merge, because a merge changes
    labels, widths, heights and the fan counts all at once — carrying any of
    them over is how a layout ends up measured against the previous group set.

    The `W_MAX` clamp is handled here, before anything measures a column: a
    label wide enough to bite the clamp is middle-ellipsised for the SVG and
    kept in full inside `why`.
    """
    full_labels, labels, widths, heights, locs = {}, {}, {}, {}, {}
    for nid, g in groups.items():
        full_labels[nid] = g["label"]
        label = g["label"]
        if node_w(label, g["loc"], g["files"]) >= W_MAX and len(label) > LABEL_MAX:
            label = _ellipsise(label)
            diag["labels_clamped"] = diag.get("labels_clamped", 0) + 1
        labels[nid] = label
        widths[nid] = node_w(label, g["loc"], g["files"])
        heights[nid] = node_h(g["loc"])
        locs[nid] = g["loc"]

    fan_in, fan_out = {}, {}
    for (a, b) in gedges:
        fan_out[a] = fan_out.get(a, 0) + 1
        fan_in[b] = fan_in.get(b, 0) + 1

    return {
        "full_labels": full_labels,
        "labels": labels,
        "widths": widths,
        "heights": heights,
        "locs": locs,
        "fan_in": fan_in,
        "fan_out": fan_out,
        "order": order_nodes(list(groups), fan_in, fan_out, locs),
    }


def build_map(sv: dict, cap: int = MAP_CAP) -> dict:
    """`survey.json` -> `map.json` (`trailhead/map@1`). Deterministic, no model.

    `render` is `"table"` below `MIN_GRAPH_NODES`: the generator then emits a
    table plus an info callout **instead of** a `graph` block (§4.4 / §9 row 4).
    The nodes and edges are still emitted — `verify-contract.js:167` does
    `D.map.nodes.map(...)` unconditionally, and the table is built from them.

    `diagnostics.columns` is the node column index. It is the provenance of the
    `cp-c1` answer key ("ordered by fan-in − fan-out over the import DAG"), so
    it is published rather than left for a consumer to reverse-engineer out of
    the x coordinates.
    """
    files_by_path = {}
    for f in sv.get("files") or []:
        if isinstance(f, dict) and f.get("path"):
            files_by_path[_norm_dir(f["path"])] = f
    label_of_metric = _rank_label(sv)

    groups, gedges, diag = collapse(sv, cap)
    m = _measure(groups, gedges, diag)

    # §4.2 step 6. Merging is the only path by which build_map may reduce the
    # node count below what collapse produced, and it must never raise:
    # MAP_CAP = 14 makes it unreachable on every repo measured, but an
    # unfamiliar repo at hour 8 is not the place to discover an assertion.
    density_merges = 0
    laid = _lay_out(m["order"], m["widths"], m["heights"])
    while laid is None and len(groups) > MIN_GRAPH_NODES:
        density_merges += 1
        groups, gedges, diag = collapse(sv, max(1, len(groups) - 1))
        m = _measure(groups, gedges, diag)
        laid = _lay_out(m["order"], m["widths"], m["heights"])

    overflow = laid is None
    if overflow:
        # Merging has stopped helping: node height goes as sqrt(loc), so pouring
        # groups into one another shrinks the total slowly and can walk all the
        # way down to a single blob. Give the graph up rather than the content —
        # restore everything collapse found and let the caller table it. A
        # fourteen-row table beats one merged rectangle labelled `pkg`.
        groups, gedges, diag = collapse(sv, cap)
        m = _measure(groups, gedges, diag)
        density_merges = 0
        laid = _lay_out(m["order"], m["widths"], m["heights"], force=True)
        # Clamp into the canvas anyway. These nodes overlap — that is what
        # "does not fit" means — but a consumer that keys the substitution off
        # `len(map.nodes) < 3` (§9 row 4) rather than off `render` would draw
        # them, and a crowded map inside the frame beats rectangles hanging off
        # the bottom edge.
        for i, p in laid[1].items():
            p["x"] = int(max(0.0, min(p["x"], W - m["widths"][i])))
            p["y"] = int(max(0.0, min(p["y"], Y_CLEAR - m["heights"][i])))
    diag["density_merges"] = density_merges

    full_labels, labels = m["full_labels"], m["labels"]
    widths, heights, order = m["widths"], m["heights"], m["order"]
    fan_in, fan_out = m["fan_in"], m["fan_out"]
    col, pos, _ = laid

    nodes = []
    for nid in order:
        g = groups[nid]
        ranked = _rank_files(g, sv, files_by_path, label_of_metric)
        nodes.append({
            "id": nid,
            "label": labels[nid],
            "loc": g["loc"],
            "files": g["files"],
            "x": pos[nid]["x"],
            "y": pos[nid]["y"],
            "w": widths[nid],
            "why": _why(g, fan_out.get(nid, 0), fan_in.get(nid, 0), ranked,
                        labels[nid], full_labels[nid]),
            "top": [f"{_basename(p)} — {lab} {v}" for p, v, lab in ranked[:3]],
        })

    # §4.2 step 7: an edge whose target sits in a column to the LEFT backtracks
    # across the canvas and reads as a horizontal band, so it is dropped and
    # counted. Measured on the proving-ground repo: 9 such edges among 14 nodes,
    # one of them running 626 px right-to-left across a 900 px canvas.
    edges, dropped_backward = [], 0
    for (a, b), n in sorted(gedges.items()):
        if col.get(b, 0) >= col.get(a, 0):
            edges.append({"a": a, "b": b, "n": n})
        else:
            dropped_backward += 1
    diag["edges_dropped_backward"] = dropped_backward
    diag["columns"] = {nid: col.get(nid, 0) for nid in order}
    if overflow:
        # The one case where the §4.3 invariants are NOT asserted: no graph
        # block is emitted, so there is nothing on the canvas to spill off it.
        # Say so in the diagnostics rather than letting a silent skip look like
        # a pass.
        diag["overflow_table"] = len(nodes)
    else:
        check_invariants(nodes, edges)

    return {
        "contract": "trailhead/map@1",
        "render": "graph" if (len(nodes) >= MIN_GRAPH_NODES and not overflow) else "table",
        "nodes": nodes,
        "edges": edges,
        "diagnostics": diag,
    }
