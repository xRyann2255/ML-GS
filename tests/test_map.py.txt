"""Stage 2 MAP: collapse, DAG layering, and the geometry invariants.

The map is the one artifact whose correctness neither gate can see:
`check-bundle.js` and `verify-contract.js` between them check self-containment
and every anchor in the payload, and not one coordinate. A node laid out past
the canvas edge, or overlapping its neighbour, passes both gates and is
visible to everybody in the room.

So the invariants are asserted twice: inside `build_map`, so a bad layout
fails generation, and here, so a bad *formula* fails the build. The height
formula is the template build's `42 + min(28, round(sqrt(loc)/6))` and it is
emitted explicitly on every node, because the renderer draws `n.h` verbatim.

The layout itself is template parity (spec section 3): longest-path layering
over the group import graph, at most `MAX_COLUMNS` columns, a fixed 1000-unit
canvas width with computed height, placeholder `LAYER <n>` column headers,
test containers off the board and named in `map.note`, and `tour_order` for
stage 3 to write tour text against.

Run:  PYTHONPATH=src python -m pytest tests/test_map.py -q
"""
import json
import re
import unittest
from pathlib import Path

from trailhead import mapper

RENDERER = Path(__file__).resolve().parents[1] / "src" / "trailhead" / "template.html"

#: The barred dash characters, spelled with chr so this file carries neither.
EM = chr(0x2014)
EN = chr(0x2013)


def survey_of(specs, edges=(), *, churn=True, declared=("pkg",), import_root="src"):
    """A minimal `trailhead/survey@1` over `src/pkg/<name>/` directories.

    `specs` is `[(name, [(filename, loc, commits), ...]), ...]`; `name` may
    contain a slash to nest a module below its group. `edges` is
    `[(a_name, b_name, n), ...]` over module dotted names.

    Deliberately hand-built rather than loaded from `fixtures/survey.sample.json`:
    the fixture carries 10 of its 68 file rows, so it cannot express "this group
    holds exactly one file", which is the condition rule 3 of the collapse
    merges on.
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


def chain_of(n, *, loc=200):
    """`n` groups wired into one import chain m0 -> m1 -> ... -> m(n-1)."""
    assert n <= 10, "single-digit ids keep the lexicographic tiebreak honest"
    return repo_of(n, loc=loc, edges=[(f"m{i}", f"m{i + 1}", 3) for i in range(n - 1)])


class NodeGeometry(unittest.TestCase):
    def test_node_h_matches_the_template_builds_formula(self):
        # 42 + min(28, round(sqrt(loc)/6)), half-up like JS Math.round.
        self.assertEqual(mapper.node_h(0), 42)
        self.assertEqual(mapper.node_h(9), 43)       # sqrt 3 / 6 = 0.5, rounds up
        self.assertEqual(mapper.node_h(36), 43)      # 6/6 = 1
        self.assertEqual(mapper.node_h(3600), 52)    # 60/6 = 10
        self.assertEqual(mapper.node_h(1_000_000), 70)   # capped at 42 + 28

    def test_the_renderer_draws_the_explicit_height(self):
        # The map emits h because the renderer reads n.h first and only
        # derives a height for legacy payloads that carry none.
        if not RENDERER.exists():
            self.skipTest("renderer template not present")
        html = RENDERER.read_text(encoding="utf-8")

        self.assertIsNotNone(
            re.search(r"const nodeH=n=>n\.h\|\|", html),
            "renderer no longer prefers the explicit node height")

    def test_the_density_cap_is_fourteen_not_forty(self):
        self.assertEqual(mapper.MAP_CAP, 14)

    def test_the_canvas_and_node_width_are_the_templates(self):
        self.assertEqual(mapper.W, 1000.0)
        self.assertEqual(mapper.NODE_W, 150)
        self.assertEqual(mapper.MAX_COLUMNS, 7)

    def test_the_label_cap_fits_the_fixed_node_width(self):
        self.assertEqual(mapper.LABEL_MAX, 18)


class OrderNodes(unittest.TestCase):
    IDS = ["a", "b", "c"]

    def test_pure_importers_sort_left_and_pure_libraries_sort_right(self):
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


class Layering(unittest.TestCase):
    def test_a_chain_gets_one_layer_per_node(self):
        order = ["a", "b", "c", "d"]
        layer = mapper.layer_nodes(order, {("a", "b"): 1, ("b", "c"): 1,
                                           ("c", "d"): 1})

        self.assertEqual(layer, {"a": 0, "b": 1, "c": 2, "d": 3})

    def test_a_diamond_shares_the_middle_layer(self):
        order = ["a", "b", "c", "d"]
        layer = mapper.layer_nodes(order, {("a", "b"): 1, ("a", "c"): 1,
                                           ("b", "d"): 1, ("c", "d"): 1})

        self.assertEqual(layer, {"a": 0, "b": 1, "c": 1, "d": 2})

    def test_the_layer_is_the_longest_path_not_the_shortest(self):
        # a -> d directly, but also a -> b -> c -> d: d sits at layer 3.
        order = ["a", "b", "c", "d"]
        layer = mapper.layer_nodes(order, {("a", "d"): 1, ("a", "b"): 1,
                                           ("b", "c"): 1, ("c", "d"): 1})

        self.assertEqual(layer["d"], 3)

    def test_an_order_backward_edge_is_left_out_of_the_layering(self):
        # The cycle-closing edge d -> a must not drag a to layer 4.
        order = ["a", "b", "c", "d"]
        layer = mapper.layer_nodes(order, {("a", "b"): 1, ("b", "c"): 1,
                                           ("c", "d"): 1, ("d", "a"): 1})

        self.assertEqual(layer, {"a": 0, "b": 1, "c": 2, "d": 3})

    def test_squeeze_is_identity_below_the_cap(self):
        layer = {"a": 0, "b": 3, "c": 6}

        self.assertEqual(mapper.squeeze_layers(layer), layer)

    def test_squeeze_merges_middle_layers_and_keeps_the_ends(self):
        layer = {f"n{i}": i for i in range(10)}
        col = mapper.squeeze_layers(layer)

        self.assertEqual(col["n0"], 0)
        self.assertEqual(col["n9"], mapper.MAX_COLUMNS - 1)
        self.assertEqual(sorted(set(col.values())), list(range(7)))
        for i in range(9):     # monotone: never skips, never reverses
            self.assertIn(col[f"n{i + 1}"] - col[f"n{i}"], (0, 1))


class Collapse(unittest.TestCase):
    def test_every_input_module_belongs_to_exactly_one_node(self):
        groups, _, _ = mapper.collapse(repo_of(6))
        seen = [m for g in groups.values() for m in g["modules"]]

        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {f"pkg.m{i}" for i in range(6)})

    def test_a_single_file_group_is_merged_into_its_parent(self):
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
        sv = repo_of(2, edges=[("m0", "m1", 214)])
        _, edges, diag = mapper.collapse(sv)

        self.assertEqual(list(edges.values()), [mapper.EDGE_CAP])
        self.assertEqual(diag["edge_cap_hits"], 1)

    def test_a_self_edge_is_never_drawn(self):
        sv = repo_of(2, edges=[("m0", "m0", 9)])
        _, edges, _ = mapper.collapse(sv)

        self.assertEqual(edges, {})

    def test_labels_drop_the_declared_package_prefix(self):
        groups, _, _ = mapper.collapse(repo_of(2))

        self.assertEqual(sorted(g["label"] for g in groups.values()), ["m0", "m1"])

    def test_the_package_root_keeps_its_own_name(self):
        sv = survey_of([("", [("__init__.py", 8, 2), ("registry.py", 300, 9)]),
                        ("core", [("a.py", 100, 5), ("b.py", 100, 5)])])
        groups, _, _ = mapper.collapse(sv)

        self.assertEqual(sorted(g["label"] for g in groups.values()), ["core", "pkg"])

    def test_an_svg_hostile_label_is_sanitised(self):
        sv = survey_of([("a<script>&", [("x.py", 30, 2), ("y.py", 30, 2)])])
        groups, _, _ = mapper.collapse(sv)

        for g in groups.values():
            self.assertNotIn("<", g["label"])
            self.assertNotIn("&", g["label"])


class OffBoardRule(unittest.TestCase):
    def test_a_survey_pinned_test_root_is_off_by_definition(self):
        self.assertTrue(mapper._is_offboard({"is_test": True, "paths": []}))

    def test_sixty_percent_under_a_test_directory_is_off(self):
        g = {"is_test": False,
             "paths": ["a/tests/x.py", "a/tests/y.py", "b/tests/z.py",
                       "a/core.py", "a/util.py"]}

        self.assertTrue(mapper._is_offboard(g))       # 3 of 5, exactly 60%

    def test_below_sixty_percent_stays_on_board(self):
        g = {"is_test": False, "paths": ["a/tests/x.py", "a/core.py"]}

        self.assertFalse(mapper._is_offboard(g))      # 1 of 2

    def test_a_loose_test_file_at_the_root_is_not_a_container(self):
        g = {"is_test": False, "paths": ["test_x.py"]}

        self.assertFalse(mapper._is_offboard(g))

    def test_a_rollup_only_group_stays_on_board(self):
        self.assertFalse(mapper._is_offboard({"is_test": False, "paths": []}))


class BuildMap(unittest.TestCase):
    def assert_invariants(self, m):
        """Every geometry invariant, re-asserted outside build_map's own check."""
        mapper.check_invariants(m["nodes"], m["edges"], m["columns"], m["h"])
        self.assertEqual(m["w"], 1000)
        for n in m["nodes"]:
            self.assertGreaterEqual(n["x"], 0)
            self.assertLessEqual(n["x"] + n["w"], 1000)
            self.assertGreaterEqual(n["y"], mapper.Y_START)
            self.assertLessEqual(n["y"] + n["h"], m["h"])
            self.assertEqual(n["w"], mapper.NODE_W)
            self.assertEqual(n["h"], mapper.node_h(n["loc"]))
            self.assertGreaterEqual(len(n["top"]), 1)
            for field in ("id", "label", "loc", "files", "x", "y", "w", "h",
                          "path", "why", "top"):
                self.assertIn(field, n)

    def test_every_rect_fits_the_canvas_from_three_to_fourteen_nodes(self):
        for n in range(3, 15):
            with self.subTest(nodes=n):
                m = mapper.build_map(repo_of(n))

                self.assertEqual(len(m["nodes"]), n)
                self.assert_invariants(m)

    def test_a_chain_lays_out_one_column_per_node_in_import_order(self):
        m = mapper.build_map(chain_of(5))
        col = m["diagnostics"]["columns"]

        self.assertEqual([col[f"n-src-pkg-m{i}"] for i in range(5)],
                         [0, 1, 2, 3, 4])
        self.assertEqual(len(m["columns"]), 5)
        self.assertEqual(m["diagnostics"]["edges_dropped_backward"], 0)
        self.assertEqual(len(m["edges"]), 4)
        self.assert_invariants(m)

    def test_a_chain_deeper_than_seven_squeezes_to_seven_columns(self):
        m = mapper.build_map(chain_of(10))
        col = m["diagnostics"]["columns"]
        along = [col[f"n-src-pkg-m{i}"] for i in range(10)]

        self.assertEqual(len(m["columns"]), 7)
        self.assertEqual(along[0], 0)
        self.assertEqual(along[-1], 6)
        for a, b in zip(along, along[1:]):     # monotone, no skipped column
            self.assertIn(b - a, (0, 1))
        self.assert_invariants(m)

    def test_a_graph_with_no_edges_lays_out_in_a_single_column(self):
        m = mapper.build_map(repo_of(5))

        self.assertEqual(m["edges"], [])
        self.assertEqual(set(m["diagnostics"]["columns"].values()), {0})
        self.assertEqual(len(m["columns"]), 1)
        self.assertFalse(m["columns"][0]["line"])
        self.assert_invariants(m)

    def test_columns_are_stacked_from_forty_with_the_template_gap(self):
        m = mapper.build_map(repo_of(5))
        ys = sorted((n["y"], n["h"]) for n in m["nodes"])

        self.assertEqual(ys[0][0], 40)
        for (y0, h0), (y1, _) in zip(ys, ys[1:]):
            self.assertEqual(y1, y0 + h0 + 26)

    def test_the_canvas_height_is_the_tallest_columns_cursor_plus_pad(self):
        for sv in (repo_of(5), chain_of(4), repo_of(14, loc=400_000)):
            m = mapper.build_map(sv)
            per_col = {}
            for n in m["nodes"]:
                c = m["diagnostics"]["columns"][n["id"]]
                per_col[c] = max(per_col.get(c, 0), n["y"] + n["h"] + 26)

            self.assertEqual(m["h"], max(per_col.values()) + 8)

    def test_a_dense_repo_grows_the_canvas_instead_of_giving_up(self):
        # The old overflow-table mode is gone: map.h is computed, so fourteen
        # maximum-height nodes simply get a taller board.
        m = mapper.build_map(repo_of(14, loc=400_000))

        self.assertEqual(m["render"], "graph")
        self.assertEqual(len(m["nodes"]), 14)
        self.assertGreater(m["h"], 400)
        self.assertNotIn("overflow_table", m["diagnostics"])
        self.assert_invariants(m)

    def test_column_headers_are_placeholder_layers_with_centred_x(self):
        m = mapper.build_map(chain_of(7))

        self.assertEqual(len(m["columns"]), 7)
        for i, c in enumerate(m["columns"]):
            self.assertEqual(sorted(c), ["label", "line", "x"])
            self.assertEqual(c["label"], f"LAYER {i + 1}")
            self.assertEqual(c["line"], i > 0)
            self.assertTrue(0 <= c["x"] <= 1000)
        xs = [c["x"] for c in m["columns"]]
        self.assertEqual(xs, sorted(xs))
        self.assert_invariants(m)

    def test_tour_order_walks_left_to_right_then_top_to_bottom(self):
        # An entry-less survey keeps the pure stack walk: leftmost column to
        # rightmost, top to bottom inside a column.
        m = mapper.build_map(chain_of(5))
        col = m["diagnostics"]["columns"]
        y = {n["id"]: n["y"] for n in m["nodes"]}
        expect = sorted((n["id"] for n in m["nodes"]),
                        key=lambda i: (col[i], y[i], i))

        self.assertEqual(m["tour_order"], expect)
        self.assertEqual(sorted(m["tour_order"]),
                         sorted(n["id"] for n in m["nodes"]))

    def test_tour_order_starts_at_the_entry_group_within_its_column(self):
        # Five sibling groups, one column, stacked m0..m4. The entry point
        # lives in m3, so the tour opens there; the rest keep stack order.
        sv = repo_of(5)
        sv["entry_points"] = [{
            "kind": "console_script", "name": "t", "file": "src/pkg/m3/f0.py",
            "line": 1, "target": "pkg.m3.f0:main", "confidence": "high",
            "provenance": "test fixture"}]
        m = mapper.build_map(sv)

        self.assertEqual(m["tour_order"],
                         ["n-src-pkg-m3", "n-src-pkg-m0", "n-src-pkg-m1",
                          "n-src-pkg-m2", "n-src-pkg-m4"])

    def test_the_entry_anchor_is_per_column_not_global(self):
        # Diamond: m0 -> {m1, m2} -> m3. Columns are 0, 1, 1, 2 and the
        # column-1 stack is m1 above m2. An entry in m2 promotes it within
        # its own column only; m0 still opens the tour from column 0.
        sv = repo_of(4, edges=[("m0", "m1", 2), ("m0", "m2", 2),
                               ("m1", "m3", 2), ("m2", "m3", 2)])
        sv["entry_points"] = [{
            "kind": "main_guard", "name": "src/pkg/m2/f0.py",
            "file": "src/pkg/m2/f0.py", "line": 1, "target": "pkg.m2.f0",
            "confidence": "low", "provenance": "test fixture"}]
        m = mapper.build_map(sv)
        y = {n["id"]: n["y"] for n in m["nodes"]}

        self.assertEqual(m["tour_order"],
                         ["n-src-pkg-m0", "n-src-pkg-m2", "n-src-pkg-m1",
                          "n-src-pkg-m3"])
        self.assertLess(y["n-src-pkg-m1"], y["n-src-pkg-m2"])  # stack intact

    def test_the_entry_anchor_reorders_the_walk_not_the_geometry(self):
        plain = mapper.build_map(repo_of(5))
        sv = repo_of(5)
        sv["entry_points"] = [{
            "kind": "module_main", "name": "python -m pkg.m3",
            "file": "src/pkg/m3/f0.py", "line": 1, "target": "pkg.m3.f0",
            "confidence": "high", "provenance": "test fixture"}]
        anchored = mapper.build_map(sv)

        self.assertEqual(anchored["nodes"], plain["nodes"])
        self.assertEqual(anchored["columns"], plain["columns"])
        self.assertEqual(anchored["h"], plain["h"])
        self.assertNotEqual(anchored["tour_order"], plain["tour_order"])

    def test_an_entry_file_outside_every_group_changes_nothing(self):
        # The console-script row can name pyproject.toml, which no Python
        # group contains; the walk must fall back to pure stack order.
        plain = mapper.build_map(repo_of(4))
        sv = repo_of(4)
        sv["entry_points"] = [{
            "kind": "console_script", "name": "t", "file": "pyproject.toml",
            "line": 3, "target": "pkg.m0:main", "confidence": "high",
            "provenance": "test fixture"}]
        m = mapper.build_map(sv)

        self.assertEqual(m["tour_order"], plain["tour_order"])
        self.assertEqual(m, plain)

    def test_a_single_very_long_label_is_ellipsised_for_the_fixed_width(self):
        long = "z" * 120
        sv = survey_of([
            (long, [("a.py", 200, 4), ("b.py", 200, 3)]),
            ("m1", [("a.py", 100, 2), ("b.py", 100, 1)]),
            ("m2", [("a.py", 100, 2), ("b.py", 100, 1)]),
        ])
        m = mapper.build_map(sv)
        clamped = [n for n in m["nodes"] if n["label"].startswith("z")][0]

        self.assertEqual(clamped["w"], mapper.NODE_W)
        self.assertLessEqual(len(clamped["label"]), mapper.LABEL_MAX)
        self.assertIn("...", clamped["label"])
        self.assertIn(long, clamped["why"])          # the full name survives
        self.assert_invariants(m)

    def test_top_is_never_empty_even_when_every_file_is_a_tiny_init(self):
        sv = survey_of([
            ("root", [("__init__.py", 8, 3)]),
            ("root/sub", [("__init__.py", 5, 2)]),
        ])
        m = mapper.build_map(sv)

        self.assertEqual(len(m["nodes"]), 1)
        self.assertGreaterEqual(len(m["nodes"][0]["top"]), 1)
        for row in m["nodes"][0]["top"]:
            self.assertIn("__init__.py", row)

    def test_top_says_fan_in_when_there_is_no_git_history(self):
        sv = survey_of([("core", [("a.py", 100, 9), ("b.py", 90, 4)])], churn=False)
        m = mapper.build_map(sv)

        self.assertIn("fan-in (no git history)", m["nodes"][0]["top"][0])
        self.assertIn("fan-in (no git history)", m["nodes"][0]["why"])

    def test_top_joins_with_a_plain_hyphen_never_a_dash(self):
        m = mapper.build_map(repo_of(3))

        for n in m["nodes"]:
            for row in n["top"]:
                self.assertRegex(row, r"^f\d\.py - commits \d+$")

    def test_no_emitted_string_carries_a_dash_character(self):
        surveys = [repo_of(4), repo_of(3, edges=[("m0", "m1", 4)]),
                   survey_of([("core", [("a.py", 90, 2), ("b.py", 80, 1)])],
                             churn=False)]
        sv = repo_of(3)
        sv["dangling"] = [{"target": "gs.quant", "n": 4, "sites": []}]
        surveys.append(sv)
        for i, s in enumerate(surveys):
            with self.subTest(survey=i):
                blob = json.dumps(mapper.build_map(s), ensure_ascii=False)

                self.assertNotIn(EM, blob)
                self.assertNotIn(EN, blob)

    def test_every_node_carries_its_group_path(self):
        m = mapper.build_map(repo_of(2))

        self.assertEqual(sorted(n["path"] for n in m["nodes"]),
                         ["src/pkg/m0", "src/pkg/m1"])

    def test_the_why_sentence_is_unchanged_from_map_at_one(self):
        m = mapper.build_map(repo_of(3))
        n = m["nodes"][0]

        self.assertRegex(
            n["why"],
            r"^2 files, 200 loc\. Imports 0 of these; imported by 0\. "
            r"Busiest file: f\d\.py \(commits \d+\)\.$")

    def test_every_edge_names_an_emitted_node_and_never_points_backward(self):
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

    def test_a_pinned_test_root_leaves_the_board_and_lands_in_the_note(self):
        sv = survey_of([("core", [("a.py", 100, 5), ("b.py", 90, 4)]),
                        ("other", [("c.py", 80, 3), ("d.py", 70, 2)]),
                        ("web", [("e.py", 60, 3), ("f.py", 50, 2)])])
        sv["modules"]["tests"] = {"path": "src/tests", "files": 2, "loc": 40,
                                  "commits": 1, "top": []}
        sv["files"] += [{"path": "src/tests/test_x.py", "module": "tests",
                         "loc": 20, "commits": 1},
                        {"path": "src/tests/test_y.py", "module": "tests",
                         "loc": 20, "commits": 1}]
        sv["roots"]["test_roots"] = ["src/tests"]
        sv["edges"].append({"a": "tests", "b": "pkg.core", "n": 5})
        m = mapper.build_map(sv)
        ids = {n["id"] for n in m["nodes"]}

        self.assertEqual(sorted(n["label"] for n in m["nodes"]),
                         ["core", "other", "web"])
        for e in m["edges"]:
            self.assertIn(e["a"], ids)
            self.assertIn(e["b"], ids)
        self.assertEqual(m["diagnostics"]["offboard_groups"], ["src/tests"])
        self.assertEqual(m["diagnostics"]["edges_offboard"], 1)
        self.assertEqual(m["note"]["title"], "WHAT IS NOT ON THIS BOARD")
        self.assertIn("src/tests (2 files, 40 loc)", m["note"]["text"])
        self.assertNotIn("tests", m["diagnostics"]["columns"].keys())
        self.assert_invariants(m)

    def test_an_undeclared_tests_directory_is_still_taken_off_the_board(self):
        # No survey test_roots at all: the 60 percent directory-name rule
        # catches the container on its own.
        sv = survey_of([
            ("app", [("a.py", 100, 4), ("b.py", 90, 3)]),
            ("lib", [("c.py", 80, 3), ("d.py", 70, 2)]),
            ("web", [("e.py", 60, 2), ("f.py", 50, 1)]),
            ("app/tests", [("t1.py", 30, 1), ("t2.py", 20, 1), ("t3.py", 10, 1)]),
        ])
        m = mapper.build_map(sv)

        self.assertEqual(sorted(n["label"] for n in m["nodes"]),
                         ["app", "lib", "web"])
        self.assertEqual(m["diagnostics"]["offboard_groups"],
                         ["src/pkg/app/tests"])
        self.assertIn("src/pkg/app/tests (3 files, 60 loc)", m["note"]["text"])
        self.assert_invariants(m)

    def test_dangling_imports_are_counted_in_the_note_without_offboard_groups(self):
        sv = repo_of(3)
        sv["dangling"] = [{"target": "gs.quant", "n": 4, "sites": []},
                          {"target": "marquee", "n": 2, "sites": []}]
        m = mapper.build_map(sv)

        self.assertIn("2 imported module names", m["note"]["text"])
        self.assertIn("6 import sites", m["note"]["text"])
        self.assertNotIn("Not drawn", m["note"]["text"])

    def test_no_note_is_emitted_when_there_is_nothing_to_say(self):
        m = mapper.build_map(repo_of(3))

        self.assertNotIn("note", m)

    def test_fewer_than_three_nodes_asks_for_a_table_but_still_ships_the_nodes(self):
        one = mapper.build_map(repo_of(1))
        three = mapper.build_map(repo_of(3))

        self.assertEqual(one["render"], "table")
        self.assertEqual(len(one["nodes"]), 1)
        self.assertEqual(three["render"], "graph")

    def test_thirty_top_level_packages_collapse_to_the_cap_losing_nothing(self):
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
        self.assertEqual(sorted(set(m["diagnostics"]["columns"].values())), [0, 1, 2])
        self.assert_invariants(m)

    def test_a_survey_with_no_roots_key_still_maps(self):
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
        self.assertEqual(m["columns"], [])
        self.assertEqual(m["tour_order"], [])
        self.assertEqual(m["render"], "table")
        self.assertEqual(m["w"], 1000)

    def test_the_contract_tag_and_key_set_are_the_frozen_ones(self):
        m = mapper.build_map(repo_of(3))

        self.assertEqual(m["contract"], "trailhead/map@1")
        self.assertEqual(sorted(m), ["columns", "contract", "diagnostics",
                                     "edges", "h", "nodes", "render",
                                     "tour_order", "w"])

    def test_the_layout_is_deterministic(self):
        first = mapper.build_map(repo_of(9, edges=[("m1", "m2", 4), ("m3", "m1", 2)]))
        again = mapper.build_map(repo_of(9, edges=[("m1", "m2", 4), ("m3", "m1", 2)]))

        self.assertEqual(first, again)


class Invariants(unittest.TestCase):
    GOOD = {"id": "n-a", "label": "a", "loc": 100, "files": 2,
            "x": 10, "y": 40, "w": 150, "h": mapper.node_h(100),
            "path": "src/a", "why": "why", "top": ["a.py - commits 1"]}

    def test_a_node_past_the_right_edge_is_rejected(self):
        bad = dict(self.GOOD, x=900)      # 900 + 150 > 1000

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([bad], [])

    def test_a_node_past_the_computed_bottom_is_rejected(self):
        bad = dict(self.GOOD, y=70)       # 70 + 44 > 100

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([bad], [], canvas_h=100)

    def test_an_empty_top_is_rejected(self):
        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([dict(self.GOOD, top=[])], [])

    def test_a_missing_field_is_rejected(self):
        for field in ("why", "h", "path"):
            thin = {k: v for k, v in self.GOOD.items() if k != field}

            with self.subTest(field=field), self.assertRaises(mapper.LayoutError):
                mapper.check_invariants([thin], [])

    def test_a_height_that_is_not_node_h_is_rejected(self):
        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([dict(self.GOOD, h=99)], [])

    def test_a_dash_in_an_authored_string_is_rejected(self):
        for bad in (dict(self.GOOD, top=[f"a.py {EM} commits 1"]),
                    dict(self.GOOD, why=f"why {EN} why")):
            with self.assertRaises(mapper.LayoutError):
                mapper.check_invariants([bad], [])

    def test_overlapping_rects_are_rejected(self):
        a = dict(self.GOOD, id="n-a")
        b = dict(self.GOOD, id="n-b", y=50)

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([a, b], [])

    def test_the_seven_column_kiss_is_tolerated(self):
        # At seven columns the span (137) is narrower than the node width
        # (150), so aligned rects in adjacent columns overlap by 13 units by
        # design; the hand-built template ships exactly this geometry.
        cols = [{"label": "LAYER 1", "x": 89, "line": False},
                {"label": "LAYER 2", "x": 226, "line": True}]
        a = dict(self.GOOD, id="n-a", x=14)
        b = dict(self.GOOD, id="n-b", x=151)

        mapper.check_invariants([a, b], [], cols)     # must not raise

        with self.assertRaises(mapper.LayoutError):   # strict without columns
            mapper.check_invariants([a, b], [])

    def test_an_edge_to_an_unemitted_node_is_rejected(self):
        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([self.GOOD], [{"a": "n-a", "b": "n-ghost", "n": 1}])

    def test_a_column_outside_the_canvas_is_rejected(self):
        cols = [{"label": "LAYER 1", "x": 1200, "line": False}]

        with self.assertRaises(mapper.LayoutError):
            mapper.check_invariants([self.GOOD], [], cols)


if __name__ == "__main__":
    unittest.main()
