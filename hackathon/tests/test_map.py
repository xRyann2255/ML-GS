"""Stage 2 MAP — collapse and the geometry invariants.

The map is the one artifact whose correctness neither gate can see:
`check-bundle.js` and `verify-contract.js` between them check 21 self-containment
properties and every anchor in the payload, and **not one coordinate**. A node
laid out past the canvas edge, or overlapping its neighbour, passes both gates
and is visible to everybody in the room.

So the invariants of plan §4.3 are asserted twice — inside `build_map`, so a bad
layout fails generation, and here, so a bad *formula* fails the build. That
distinction is the whole point of `test_node_h_matches_the_renderers_own_height`:
the first draft of the layout reserved `34 + sqrt(loc)/9` while the renderer drew
`44 + sqrt(loc)/6`, under-reserving twelve nodes by 166 px — and every invariant
asserted against the wrong formula passed.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_map -v
"""
import re
import unittest
from pathlib import Path

from trailhead import mapper

TEMPLATE = Path(__file__).resolve().parents[1] / "demo" / "trailhead-demo.html"


def survey_of(specs, edges=(), *, churn=True, declared=("pkg",), import_root="src"):
    """A minimal `trailhead/survey@1` over `src/pkg/<name>/` directories.

    `specs` is `[(name, [(filename, loc, commits), ...]), ...]`; `name` may
    contain a slash to nest a module below its group. `edges` is
    `[(a_name, b_name, n), ...]` over module dotted names.

    Deliberately hand-built rather than loaded from `fixtures/survey.sample.json`:
    the fixture carries 10 of its 68 file rows, so it cannot express "this group
    holds exactly one file", which is the condition rule 3 of §4.1 merges on.
    """
    modules, files = {}, []
    for name, rows in specs:
        d = "/".join(p for p in (import_root, "pkg", name) if p)
        dotted = "pkg" + ("." + name.replace("/", ".") if name else "")
        top = []
        for fname, loc, commits in rows:
            path = f"{d}/{fname}"
            files.append({
                "path": path,
                "module": dotted if fname == "__init__.py" else f"{dotted}.{fname[:-3]}",
                "loc": loc,
                "commits": commits if churn else None,
                "last_commit": None,
                "authors": [],
            })
            top.append({"path": path, "commits" if churn else "fan_in": commits})
        top.sort(key=lambda t: -(t.get("commits") or t.get("fan_in") or 0))
        modules[dotted] = {
            "path": d,
            "files": len(rows),
            "loc": sum(r[1] for r in rows),
            "commits": sum(r[2] for r in rows) if churn else None,
            "top": top[:3],
        }

    return {
        "contract": "trailhead/survey@1",
        "repo": {"name": "t", "root": "/repo", "commit": "deadbeef",
                 "branch": None, "surveyed_at": "2026-07-30T00:00:00Z"},
        "stats": {"files": len(files), "py_files": len(files),
                  "loc": sum(f["loc"] for f in files),
                  "modules": len(modules), "external_deps": []},
        "files": files,
        "modules": modules,
        "edges": [{"a": f"pkg.{a}".replace("/", "."),
                   "b": f"pkg.{b}".replace("/", "."), "n": n} for a, b, n in edges],
        "entry_points": [],
        "command_candidates": [],
        "checkpoints": {},
        "roots": {"repo_root": "/repo", "import_roots": [import_root],
                  "test_roots": [], "pyproject": None,
                  "declared_packages": list(declared), "rule": "test fixture"},
        "churn": {"state": "GIT_OK" if churn else "NO_GIT", "available": bool(churn),
                  "reason": "", "substitute": None if churn else "fan_in",
                  "by_file": {}, "committers": {}, "discarded_paths": 0},
    }


def repo_of(n, *, loc=200, files_per=2, edges=()):
    """`n` sibling groups of `files_per` files each, none of them mergeable."""
    specs = []
    for i in range(n):
        rows = [(f"f{j}.py", loc // files_per, 10 + i + j) for j in range(files_per)]
        specs.append((f"m{i}", rows))
    return survey_of(specs, edges)


class NodeGeometry(unittest.TestCase):
    def test_node_h_matches_the_renderers_own_height(self):
        # The single most expensive thing to get wrong in this stage: the
        # layout reserves what the browser draws, or the invariants are worse
        # than useless. Read the constants back out of the shipped template.
        if not TEMPLATE.exists():
            self.skipTest("demo template not present")
        html = TEMPLATE.read_text(encoding="utf-8")
        m = re.search(r"const h=n=>([\d.]+)\+Math\.sqrt\(n\.loc\)/([\d.]+);", html)

        self.assertIsNotNone(m, "renderer's h() no longer matches the expected shape")
        self.assertEqual((float(m.group(1)), float(m.group(2))),
                         (mapper.H_BASE, mapper.H_DIV))

    def test_node_h_is_the_only_height_definition(self):
        self.assertAlmostEqual(mapper.node_h(0), 44.0)
        self.assertAlmostEqual(mapper.node_h(36), 45.0)      # 44 + 6/6

    def test_the_density_cap_is_fourteen_not_forty(self):
        # Decision #16. 900x400 with node widths around 142 holds 5 columns of
        # 6; 40 nodes is 71% fill on a canvas with no zoom and no pan.
        self.assertEqual(mapper.MAP_CAP, 14)

    def test_width_covers_both_the_label_and_the_stats_string(self):
        # The renderer clips neither string, so whichever is longer sets w.
        long_label = mapper.node_w("a" * 30, 10, 1)
        long_stats = mapper.node_w("x", 1234567, 4321)

        self.assertGreaterEqual(long_label, 22 + 6.9 * 30)
        self.assertGreaterEqual(long_stats, 22 + 6.0 * len("1,234,567 loc · 4321 files"))

    def test_width_is_clamped_so_a_column_count_always_exists(self):
        self.assertLessEqual(mapper.node_w("z" * 400, 999999, 999), mapper.W_MAX)


class OrderNodes(unittest.TestCase):
    IDS = ["a", "b", "c"]

    def test_pure_importers_sort_left_and_pure_libraries_sort_right(self):
        # a imports both; c is imported by both. Edges are drawn a.x+a.w -> b.x,
        # so a right-to-left edge backtracks into a horizontal S.
        order = mapper.order_nodes(
            self.IDS,
            fan_in={"b": 1, "c": 2}, fan_out={"a": 2, "b": 1},
            loc={"a": 1, "b": 1, "c": 1},
        )

        self.assertEqual(order, ["a", "b", "c"])

    def test_ties_break_by_size_then_id(self):
        order = mapper.order_nodes(
            ["x", "y", "z"], fan_in={}, fan_out={},
            loc={"x": 10, "y": 900, "z": 900},
        )

        self.assertEqual(order, ["y", "z", "x"])


class Place(unittest.TestCase):
    def test_a_single_column_does_not_divide_by_zero_in_the_gap(self):
        # gap = (W - 2*X_PAD - sum(colw)) / (C - 1) is a ZeroDivisionError at
        # C = 1, which is the layout of any repo with no internal edges.
        pos = mapper.place({"a": 0, "b": 0}, ["a", "b"],
                           {"a": 120, "b": 120}, {"a": 50.0, "b": 50.0})

        self.assertEqual(sorted(pos), ["a", "b"])
        self.assertEqual(pos["a"]["col"], 0)

    def test_a_column_holding_one_node_does_not_divide_by_zero_in_the_row_gap(self):
        # The greedy line-break routinely leaves the last column holding one
        # node; rg divides by max(1, n - 1) for exactly this case.
        pos = mapper.place({"a": 0, "b": 0, "c": 1}, ["a", "b", "c"],
                           {"a": 120, "b": 120, "c": 120},
                           {"a": 300.0, "b": 40.0, "c": 40.0})

        self.assertEqual(pos["c"]["col"], 1)
        self.assertGreaterEqual(pos["c"]["y"], mapper.Y_TOP)

    def test_columns_never_overlap_horizontally(self):
        pos = mapper.place({"a": 0, "b": 1}, ["a", "b"],
                           {"a": 200, "b": 120}, {"a": 50.0, "b": 50.0})

        self.assertLess(pos["a"]["x"] + 200, pos["b"]["x"])


class Collapse(unittest.TestCase):
    def test_every_input_module_belongs_to_exactly_one_node(self):
        groups, _, _ = mapper.collapse(repo_of(6))
        seen = [m for g in groups.values() for m in g["modules"]]

        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {f"pkg.m{i}" for i in range(6)})

    def test_a_single_file_group_is_merged_into_its_parent(self):
        # §4.1 rule 3, unconditionally — not only above the cap. Running it only
        # above the cap is a measured no-op on the proving-ground repo and
        # leaves 2 of 14 slots spent on single files, one an 8-line __init__.py.
        # This is that repo in miniature: a package root with loose files, one
        # healthy subpackage, one subpackage that is a single file. Appendix A.2
        # measured the same shape — `__init__.py`, `__main__.py`, `registry.py`
        # arriving as one 3-file node.
        sv = survey_of([
            ("", [("__init__.py", 8, 2), ("registry.py", 300, 9)]),
            ("core", [("a.py", 100, 5), ("b.py", 100, 5)]),
            ("lonely", [("only.py", 10, 1)]),
        ])
        groups, _, diag = mapper.collapse(sv)
        by_label = {g["label"]: g for g in groups.values()}

        self.assertEqual(sorted(by_label), ["core", "pkg"])
        self.assertEqual(by_label["pkg"]["files"], 3)
        self.assertEqual(by_label["core"]["files"], 2)
        self.assertGreaterEqual(diag["collapse_merges"], 1)

    def test_a_test_root_collapses_to_one_node_whatever_its_depth(self):
        # Measured: depth-2 on the proving-ground repo gives 26 groups of which
        # 13 are loose tests/*.py. Forcing tests to depth 1 gives 14.
        sv = survey_of([("core", [("a.py", 100, 5), ("b.py", 90, 4)]),
                        ("other", [("c.py", 80, 3), ("d.py", 70, 2)])])
        for sub in ("", "/unit", "/unit/deep"):
            dotted = "tests" + sub.replace("/", ".")
            sv["modules"][dotted] = {"path": "src/tests" + sub, "files": 2,
                                     "loc": 40, "commits": 1, "top": []}
            sv["files"].append({"path": f"src/tests{sub}/test_x.py", "module": dotted,
                                "loc": 20, "commits": 1, "last_commit": None,
                                "authors": []})
        sv["roots"]["test_roots"] = ["src/tests"]

        groups, _, _ = mapper.collapse(sv)

        self.assertEqual(sorted(g["label"] for g in groups.values()),
                         ["core", "other", "tests"])

    def test_the_node_count_never_exceeds_the_cap(self):
        groups, _, _ = mapper.collapse(repo_of(30), cap=14)

        self.assertLessEqual(len(groups), 14)

    def test_edge_weight_is_capped(self):
        # Stroke width is 0.7 + n/16 with no clamp in the renderer: a raw 214
        # draws a 14 px band across a 400-unit canvas.
        sv = repo_of(2, edges=[("m0", "m1", 214)])
        _, edges, diag = mapper.collapse(sv)

        self.assertEqual(list(edges.values()), [mapper.EDGE_CAP])
        self.assertEqual(diag["edge_cap_hits"], 1)

    def test_a_self_edge_is_never_drawn(self):
        sv = repo_of(2, edges=[("m0", "m0", 9)])
        _, edges, _ = mapper.collapse(sv)

        self.assertEqual(edges, {})

    def test_labels_drop_the_declared_package_prefix(self):
        # Label length sets w and w sets the column count, so this is the
        # layout algorithm, not cosmetics: `visualization` needs w=142 and 5
        # columns, `volforecast/visualization` needs w=195 and 4. §4.1's
        # examples are `data`, `models`, `cli` — never `volforecast/data`.
        groups, _, _ = mapper.collapse(repo_of(2))

        self.assertEqual(sorted(g["label"] for g in groups.values()), ["m0", "m1"])

    def test_the_package_root_keeps_its_own_name(self):
        # Stripping the prefix must not leave the root node with a blank label.
        sv = survey_of([("", [("__init__.py", 8, 2), ("registry.py", 300, 9)]),
                        ("core", [("a.py", 100, 5), ("b.py", 100, 5)])])
        groups, _, _ = mapper.collapse(sv)

        self.assertEqual(sorted(g["label"] for g in groups.values()), ["core", "pkg"])

    def test_an_svg_hostile_label_is_sanitised(self):
        # n.label is interpolated into SVG <text> unescaped; malformed SVG
        # breaks the whole map rather than one cell.
        sv = survey_of([("a<script>&", [("x.py", 30, 2), ("y.py", 30, 2)])])
        groups, _, _ = mapper.collapse(sv)

        for g in groups.values():
            self.assertNotIn("<", g["label"])
            self.assertNotIn("&", g["label"])


class BuildMap(unittest.TestCase):
    def assert_invariants(self, m):
        """Every §4.3 invariant, re-asserted outside build_map's own check."""
        mapper.check_invariants(m["nodes"], m["edges"])
        for n in m["nodes"]:
            self.assertGreaterEqual(n["x"], 0)
            self.assertLessEqual(n["x"] + n["w"], 900)
            self.assertGreaterEqual(n["y"], 0)
            self.assertLessEqual(n["y"] + mapper.node_h(n["loc"]), 372.0)
            self.assertGreaterEqual(len(n["top"]), 1)
            for field in ("id", "label", "loc", "files", "x", "y", "w", "why", "top"):
                self.assertIn(field, n)

    def test_every_rect_fits_the_canvas_from_three_to_fourteen_nodes(self):
        for n in range(3, 15):
            with self.subTest(nodes=n):
                m = mapper.build_map(repo_of(n))

                self.assertEqual(len(m["nodes"]), n)
                self.assert_invariants(m)

    def test_the_invariants_hold_at_one_three_eight_and_fourteen_nodes(self):
        for n in (1, 3, 8, 14):
            with self.subTest(nodes=n):
                m = mapper.build_map(repo_of(n))

                self.assertEqual(len(m["nodes"]), n)
                self.assert_invariants(m)

    def test_no_two_nodes_overlap(self):
        # Heights come from node_h, never a literal — check_invariants does the
        # pairwise test, this asserts it was actually reached at every size.
        for n in (2, 6, 11, 14):
            m = mapper.build_map(repo_of(n, loc=4000))
            rects = [(x["x"], x["y"], x["w"], mapper.node_h(x["loc"]))
                     for x in m["nodes"]]
            for i, (ax, ay, aw, ah) in enumerate(rects):
                for bx, by, bw, bh in rects[i + 1:]:
                    with self.subTest(nodes=n):
                        self.assertFalse(ax < bx + bw and bx < ax + aw
                                         and ay < by + bh and by < ay + ah)

    def test_a_graph_with_no_edges_lays_out_without_dividing_by_zero(self):
        # No internal edges is a real, named acceptance repo (`qrt`: 7 loose
        # .py, 0 internal references), not a hypothetical.
        m = mapper.build_map(repo_of(5))

        self.assertEqual(m["edges"], [])
        self.assertEqual(set(m["diagnostics"]["columns"].values()), {0})
        self.assert_invariants(m)

    def test_a_column_holding_one_node_does_not_divide_by_zero_in_the_row_gap(self):
        m = mapper.build_map(repo_of(8, loc=900))
        per_column = {}
        for nid, c in m["diagnostics"]["columns"].items():
            per_column.setdefault(c, []).append(nid)

        self.assertIn(1, [len(v) for v in per_column.values()])
        self.assert_invariants(m)

    def test_a_single_very_long_label_still_fits_the_canvas(self):
        # The W_MAX clamp. Without it max_w > 442, no C satisfies the capacity
        # rule, Cmax falls to 0 and both the placement walk and the
        # x + w <= 900 invariant break.
        long = "z" * 120
        sv = survey_of([
            (long, [("a.py", 200, 4), ("b.py", 200, 3)]),
            ("m1", [("a.py", 100, 2), ("b.py", 100, 1)]),
            ("m2", [("a.py", 100, 2), ("b.py", 100, 1)]),
        ])
        m = mapper.build_map(sv)
        clamped = [n for n in m["nodes"] if n["label"].startswith("z")][0]

        self.assertLessEqual(clamped["w"], mapper.W_MAX)
        self.assertLessEqual(len(clamped["label"]), mapper.LABEL_MAX)
        self.assertIn("...", clamped["label"])
        self.assertIn(long, clamped["why"])          # the full name survives
        self.assert_invariants(m)

    def test_top_is_never_empty_even_when_every_file_is_a_tiny_init(self):
        # The package-root group on the proving-ground repo is one 8-line
        # __init__.py with the highest fan-in in the repo (92). It sits at the
        # far right of the map, so it is the first node a judge clicks.
        sv = survey_of([
            ("root", [("__init__.py", 8, 3)]),
            ("root/sub", [("__init__.py", 5, 2)]),
        ])
        m = mapper.build_map(sv)

        self.assertEqual(len(m["nodes"]), 1)
        # The 20-loc __init__ filter empties the ranking, so the unfiltered one
        # comes back rather than the heading rendering with nothing under it.
        self.assertGreaterEqual(len(m["nodes"][0]["top"]), 1)
        for row in m["nodes"][0]["top"]:
            self.assertIn("__init__.py", row)

    def test_top_says_fan_in_when_there_is_no_git_history(self):
        # The drawer heading is hard-coded MOST-EDITED FILES, so the
        # substitution has to be visible inside the strings (decision #18).
        sv = survey_of([("core", [("a.py", 100, 9), ("b.py", 90, 4)])], churn=False)
        m = mapper.build_map(sv)

        self.assertIn("fan-in (no git history)", m["nodes"][0]["top"][0])
        self.assertIn("fan-in (no git history)", m["nodes"][0]["why"])

    def test_every_edge_names_an_emitted_node_and_never_points_backward(self):
        # A cycle guarantees at least one edge whose target sits left of its
        # source. Measured on the proving-ground repo: 9 such edges among 14
        # nodes, one running 626 px right-to-left across a 900 px canvas.
        ring = [(f"m{i}", f"m{(i + 1) % 8}", 3) for i in range(8)]
        m = mapper.build_map(repo_of(8, edges=ring))
        col = m["diagnostics"]["columns"]
        ids = {n["id"] for n in m["nodes"]}

        self.assertEqual(m["diagnostics"]["edges_dropped_backward"], 1)
        self.assertEqual(len(m["edges"]), 7)
        for e in m["edges"]:
            self.assertIn(e["a"], ids)
            self.assertIn(e["b"], ids)
            self.assertGreaterEqual(col[e["b"]], col[e["a"]])

    def test_fewer_than_three_nodes_asks_for_a_table_but_still_ships_the_nodes(self):
        # §4.4 / §9 row 4. verify-contract.js:167 does D.map.nodes.map(...)
        # unconditionally, and the substituted table is built from these nodes.
        one = mapper.build_map(repo_of(1))
        three = mapper.build_map(repo_of(3))

        self.assertEqual(one["render"], "table")
        self.assertEqual(len(one["nodes"]), 1)
        self.assertEqual(three["render"], "graph")

    def test_a_repo_too_dense_to_draw_keeps_every_node_and_asks_for_a_table(self):
        # §4.2 step 6 must never raise. Node height goes as sqrt(loc), so
        # merging shrinks the total slowly and would walk fourteen nodes down
        # to one blob; the graph is given up instead of the content, and the
        # coordinates stay inside the canvas in case a consumer draws them.
        m = mapper.build_map(repo_of(14, loc=400_000))

        self.assertEqual(m["render"], "table")
        self.assertEqual(len(m["nodes"]), 14)
        self.assertEqual(m["diagnostics"]["overflow_table"], 14)
        for n in m["nodes"]:
            self.assertLessEqual(n["x"] + n["w"], 900)
            self.assertLessEqual(n["y"] + mapper.node_h(n["loc"]), 372.0)

    def test_thirty_top_level_packages_collapse_to_the_cap_losing_nothing(self):
        # Rule 3's second pass: over the cap, the smallest groups fold into the
        # repo root rather than being thrown away. Every file is still counted
        # somewhere, which is the property that matters — a node count is a
        # layout constraint, not a licence to lose a directory silently.
        mods, files = {}, []
        for i in range(30):
            mods[f"p{i}"] = {"path": f"p{i}", "files": 2, "loc": 100 + i,
                             "commits": i, "top": [{"path": f"p{i}/a.py", "commits": i}]}
            files += [{"path": f"p{i}/a.py", "module": f"p{i}", "loc": 50, "commits": i},
                      {"path": f"p{i}/b.py", "module": f"p{i}.b", "loc": 50 + i,
                       "commits": i}]
        m = mapper.build_map({
            "modules": mods, "files": files, "edges": [],
            "roots": {"repo_root": "/r", "import_roots": [""], "test_roots": [],
                      "declared_packages": []},
            "churn": {"available": False},
        })

        self.assertEqual(len(m["nodes"]), 14)
        self.assertEqual(m["diagnostics"]["groups_dropped"], 0)
        self.assertEqual(sum(n["files"] for n in m["nodes"]), 60)
        self.assert_invariants(m)

    def test_more_import_roots_than_the_cap_drops_the_smallest_and_says_so(self):
        # The one shape rule 3 cannot fix: each root's group key is already
        # empty, so there is no parent to merge into. Keep the largest and
        # count the rest — the terminal root cascade (§3.2 rule 5) makes every
        # directory holding a .py its own import root, so this is reachable.
        files = [{"path": f"r{i}/a.py", "module": "a", "loc": 10 + i, "commits": 1}
                 for i in range(20)]
        m = mapper.build_map({
            "modules": {}, "files": files, "edges": [],
            "roots": {"repo_root": "/r", "import_roots": [f"r{i}" for i in range(20)],
                      "test_roots": [], "declared_packages": []},
            "churn": {"available": True},
        })

        self.assertEqual(len(m["nodes"]), 14)
        self.assertEqual(m["diagnostics"]["groups_dropped"], 6)
        self.assert_invariants(m)

    def test_a_repo_with_no_declared_packages_still_produces_a_graph(self):
        # §4.1 rule 4's fallback. Without it the scope is empty on two of four
        # fixture repos and two of three real acceptance repos, map.nodes is []
        # everywhere, and the map is never exercised on a repo with git history.
        mods = {"main": {"path": "", "files": 1, "loc": 300, "commits": 4,
                         "top": [{"path": "main.py", "commits": 4}]},
                "cogs.a": {"path": "cogs", "files": 2, "loc": 500, "commits": 9,
                           "top": [{"path": "cogs/a.py", "commits": 9}]},
                "utils.b": {"path": "utils", "files": 2, "loc": 200, "commits": 3,
                            "top": [{"path": "utils/b.py", "commits": 3}]}}
        files = [{"path": "main.py", "module": "main", "loc": 300, "commits": 4},
                 {"path": "cogs/a.py", "module": "cogs.a", "loc": 250, "commits": 9},
                 {"path": "cogs/c.py", "module": "cogs.c", "loc": 250, "commits": 2},
                 {"path": "utils/b.py", "module": "utils.b", "loc": 100, "commits": 3},
                 {"path": "utils/d.py", "module": "utils.d", "loc": 100, "commits": 1}]
        m = mapper.build_map({
            "modules": mods, "files": files,
            "edges": [{"a": "main", "b": "cogs.a", "n": 5},
                      {"a": "cogs.a", "b": "utils.b", "n": 3}],
            "roots": {"repo_root": "/r", "import_roots": [""], "test_roots": [],
                      "declared_packages": []},
            "churn": {"available": True},
        })

        self.assertEqual(sorted(n["label"] for n in m["nodes"]), [".", "cogs", "utils"])
        self.assertEqual(m["render"], "graph")
        self.assert_invariants(m)

    def test_a_survey_with_no_roots_key_still_maps(self):
        # fixtures/survey.sample.json has no `roots`: the repo root is then the
        # import root and every directory under it is in scope.
        m = mapper.build_map({
            "modules": {"a": {"path": "src/a", "files": 2, "loc": 100, "top": []},
                        "b": {"path": "src/b", "files": 2, "loc": 90, "top": []}},
            "files": [{"path": "src/a/x.py", "loc": 50, "commits": 3},
                      {"path": "src/a/y.py", "loc": 50, "commits": 1},
                      {"path": "src/b/z.py", "loc": 90, "commits": 2},
                      {"path": "src/b/w.py", "loc": 90, "commits": 2}],
            "edges": [{"a": "a", "b": "b", "n": 4}],
        })

        self.assertEqual(sorted(n["label"] for n in m["nodes"]), ["src/a", "src/b"])
        self.assert_invariants(m)

    def test_an_empty_survey_produces_an_empty_map_without_raising(self):
        m = mapper.build_map({"modules": {}, "files": [], "edges": []})

        self.assertEqual(m["nodes"], [])
        self.assertEqual(m["edges"], [])
        self.assertEqual(m["render"], "table")

    def test_the_contract_tag_is_the_frozen_one(self):
        m = mapper.build_map(repo_of(3))

        self.assertEqual(m["contract"], "trailhead/map@1")
        self.assertEqual(sorted(m), ["contract", "diagnostics", "edges", "nodes", "render"])

    def test_the_layout_is_deterministic(self):
        first = mapper.build_map(repo_of(9, edges=[("m1", "m2", 4), ("m3", "m1", 2)]))
        again = mapper.build_map(repo_of(9, edges=[("m1", "m2", 4), ("m3", "m1", 2)]))

        self.assertEqual(first, again)


class Invariants(unittest.TestCase):
    GOOD = {"id": "n-a", "label": "a", "loc": 100, "files": 2,
            "x": 10, "y": 10, "w": 120, "why": "why", "top": ["a.py — commits 1"]}

    def test_a_node_past_the_right_edge_is_rejected(self):
        bad = dict(self.GOOD, x=850)

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([bad], [])

    def test_a_node_over_the_ruler_is_rejected(self):
        # The ruler is drawn at y = 381-392 and a rect may reach 372.
        bad = dict(self.GOOD, y=340)

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([bad], [])

    def test_an_empty_top_is_rejected(self):
        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([dict(self.GOOD, top=[])], [])

    def test_a_missing_field_is_rejected(self):
        thin = {k: v for k, v in self.GOOD.items() if k != "why"}

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([thin], [])

    def test_overlapping_rects_are_rejected(self):
        a = dict(self.GOOD, id="n-a")
        b = dict(self.GOOD, id="n-b", y=20)

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([a, b], [])

    def test_an_edge_to_an_unemitted_node_is_rejected(self):
        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([self.GOOD], [{"a": "n-a", "b": "n-ghost", "n": 1}])


if __name__ == "__main__":
    unittest.main()
