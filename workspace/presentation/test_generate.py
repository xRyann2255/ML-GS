"""Unit tests for the presentation generator.

Run from ml-vol-estimator/:
    ./vol shell -m pytest ../../workspace/presentation/test_generate.py -v
"""
import json
import sys
from pathlib import Path

# pytest runs in importlib mode with rootdir ml-vol-estimator/src; make the
# presentation directory importable so `import generate` finds our module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate  # noqa: E402

TRACES = {
    "1": [
        {
            "x": ["2022-05-03", "2022-05-04", "2022-05-05", "2022-05-06"],
            "y": [1.001, 1.004, 0.998, 1.006],
            "name": "xgb_hariv0dte_init [long_flat]",
            "_signal_y": [1.0, 0.0, 1.0, 1.0, 0.0],
        },
        {
            "x": ["2022-05-03", "2022-05-04", "2022-05-05", "2022-05-06"],
            "y": [1.002, 1.005, 0.997, 1.004],
            "name": "[baseline] always_long",
            "_signal_y": [1.0, 1.0, 1.0, 1.0, 1.0],
        },
        {
            "x": ["2022-05-03", "2022-05-04", "2022-05-05", "2022-05-06"],
            "y": [0.998, 0.995, 1.003, 0.996],
            "name": "[baseline] always_short",
            "_signal_y": [-1.0, -1.0, -1.0, -1.0, -1.0],
        },
    ]
}
HTML = (
    "<html><script>\nconst somethingElse = 3;\n"
    "const gsvivsPnlTraces = " + json.dumps(TRACES) + ";\n"
    "const after = 1;\n</script></html>"
)


def test_parse_traces_roundtrip():
    assert generate._parse_gsvivs_traces(HTML) == TRACES


def test_parse_returns_none_without_marker():
    assert generate._parse_gsvivs_traces("<html>mock stub, no traces</html>") is None


def test_parse_returns_none_on_malformed_json():
    bad = "const gsvivsPnlTraces = {broken json};"
    assert generate._parse_gsvivs_traces(bad) is None


def test_select_prefers_all_long_baseline():
    tr = generate._select_index_trace(TRACES)
    assert tr is not None
    assert tr["name"] == "[baseline] always_long"


def test_select_falls_back_to_name_match():
    # No _signal_y arrays at all: primary criterion cannot fire.
    stripped = {"1": [{k: v for k, v in tr.items() if k != "_signal_y"}
                      for tr in TRACES["1"]]}
    tr = generate._select_index_trace(stripped)
    assert tr is not None
    assert "always_long" in tr["name"]


def test_select_returns_none_when_no_h1():
    assert generate._select_index_trace({"5": []}) is None


def test_extract_series_scales_first_point_to_100():
    series = generate._extract_index_series(HTML)
    assert series is not None
    assert series[0][0] == "2022-05-03"
    # float roundtrip (100/y0)*y0 is not exactly 100.0; compare with tolerance
    assert abs(series[0][1] - 100.0) < 1e-9
    assert len(series) == 4
    assert abs(series[-1][1] - 100.0 * 1.004 / 1.002) < 1e-9


def test_extract_series_none_on_real_mock_stub():
    stub = Path(__file__).resolve().parent / "tournament_dashboard_mock.html"
    assert generate._extract_index_series(stub.read_text(encoding="utf-8")) is None


def test_extract_series_normalizes_datetime_suffix():
    traces = {"1": [{
        "x": ["2022-05-03T00:00:00", "2022-05-04T00:00:00", "2022-05-05T00:00:00"],
        "y": [1.0, 1.01, 1.02],
        "name": "[baseline] always_long",
        "_signal_y": [1.0, 1.0, 1.0, 1.0],
    }]}
    html = "const gsvivsPnlTraces = " + json.dumps(traces) + ";"
    series = generate._extract_index_series(html)
    assert series is not None
    assert series[0][0] == "2022-05-03"


def test_extract_series_none_on_unparseable_date():
    traces = {"1": [{
        "x": ["not-a-date", "2022-05-04"],
        "y": [1.0, 1.01],
        "name": "[baseline] always_long",
        "_signal_y": [1.0, 1.0, 1.0],
    }]}
    html = "const gsvivsPnlTraces = " + json.dumps(traces) + ";"
    assert generate._extract_index_series(html) is None


def test_extract_series_none_on_non_numeric_y():
    traces = {"1": [{
        "x": ["2022-05-03", "2022-05-04"],
        "y": [1.0, "n/a"],
        "name": "[baseline] always_long",
        "_signal_y": [1.0, 1.0, 1.0],
    }]}
    html = "const gsvivsPnlTraces = " + json.dumps(traces) + ";"
    assert generate._extract_index_series(html) is None


def test_extract_series_none_on_nan_level():
    traces = {"1": [{
        "x": ["2022-05-03", "2022-05-04", "2022-05-05"],
        "y": [1.0, float("nan"), 1.02],
        "name": "[baseline] always_long",
        "_signal_y": [1.0, 1.0, 1.0, 1.0],
    }]}
    html = "const gsvivsPnlTraces = " + json.dumps(traces) + ";"
    assert generate._extract_index_series(html) is None


def test_extract_series_none_on_non_increasing_dates():
    traces = {"1": [{
        "x": ["2022-05-03", "2022-05-03", "2022-05-04"],
        "y": [1.0, 1.01, 1.02],
        "name": "[baseline] always_long",
        "_signal_y": [1.0, 1.0, 1.0, 1.0],
    }]}
    html = "const gsvivsPnlTraces = " + json.dumps(traces) + ";"
    assert generate._extract_index_series(html) is None


def test_chart_synthetic_has_labeled_axes():
    svg = generate._diagram_product_day(None)
    assert "index level" in svg
    # Jan-1 year ticks inside the 2022-07..2026-05 synthetic span
    assert ">2023<" in svg and ">2026<" in svg
    # y gridline labels at 10-point steps
    assert ">100<" in svg and ">130<" in svg
    # fallback is honest about itself
    assert "illustrative" in svg


def test_chart_real_series_no_illustrative_note():
    series = [("2022-01-03", 100.0), ("2023-01-03", 110.0), ("2024-01-02", 120.0)]
    svg = generate._diagram_product_day(series)
    assert "illustrative" not in svg


def test_chart_red_ticks_mark_only_negative_days():
    series = [("2022-01-03", 100.0), ("2022-01-04", 101.0), ("2022-01-05", 99.0),
              ("2022-01-06", 100.5), ("2022-01-07", 100.2)]
    svg = generate._diagram_product_day(series)
    # two negative-return days (idx 2 and 4) -> exactly two red tick lines
    assert svg.count(f'stroke="{generate.THEME["red"]}"') == 2


def test_chart_red_ticks_capped_at_15():
    # 40 alternating up/down days -> 20 negative days, capped at 15 ticks
    series = [("2022-01-03", 100.0)]
    lvl = 100.0
    for k in range(1, 41):
        lvl = lvl * (0.99 if k % 2 else 1.02)
        series.append((f"2022-{1 + k // 25:02d}-{1 + k % 25:02d}", lvl))
    svg = generate._diagram_product_day(series)
    assert svg.count(f'stroke="{generate.THEME["red"]}"') == 15


def test_apply_series_numbers():
    generate._apply_series_numbers([("2022-01-01", 100.0), ("2026-01-01", 136.0)])
    assert generate.NUMBERS["index_path"] == "100 to 136"
    assert generate.NUMBERS["index_per_year"] == "9.0 points a year"


def test_generate_mock_stub_falls_back(tmp_path, capsys):
    mock = Path(__file__).resolve().parent / "tournament_dashboard_mock.html"
    out = tmp_path / "deck.html"
    html = generate.generate(str(mock), out)
    assert 'data-diagram="product_day"' in html
    assert "slide 2 chart: synthetic fallback" in capsys.readouterr().out


def test_deck_has_eleven_slides_and_feature_stack(tmp_path):
    mock = Path(__file__).resolve().parent / "tournament_dashboard_mock.html"
    out = tmp_path / "deck.html"
    html = generate.generate(str(mock), out)
    assert html.count('<section class="slide') == 11
    assert 'data-diagram="feature_stack"' in html


def test_feature_stack_diagram_content():
    svg = generate._diagram_feature_stack()
    assert "LAYER 0" in svg and "LAYER 1" in svg and "LAYER 2" in svg
    assert "bipower" in svg
    assert "semivariance" in svg
    assert "signed jump" in svg
    assert "quarticity" in svg
    # layers 3-5 named in the footnote
    assert "microstructure" in svg and "cross-asset" in svg and "calendar" in svg
