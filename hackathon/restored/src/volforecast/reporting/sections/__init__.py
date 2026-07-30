"""Report section registry.

Each section module exposes a ``render(data) -> str`` function that returns
an HTML fragment (one ``<section>`` block with Plotly chart divs).

Sections are rendered in the order listed in ``SECTIONS``.
"""

from __future__ import annotations

# Ordered list of (section_id, display_title, module_path) for the report.
# html_report.py iterates this to call each renderer.
SECTIONS: list[tuple[str, str, str]] = [
    ("summary", "Experiment Summary", "volforecast.reporting.sections.summary"),
    ("forecast", "Forecast vs Actual", "volforecast.reporting.sections.forecast_vs_actual"),
    ("qlike", "QLIKE Analysis", "volforecast.reporting.sections.qlike_analysis"),
    ("diagnostics", "Diagnostics", "volforecast.reporting.sections.diagnostics"),
    ("statistical_tests", "Statistical Tests", "volforecast.reporting.sections.statistical_tests"),
    ("economic_value", "Economic Value", "volforecast.reporting.sections.economic_value"),
]
