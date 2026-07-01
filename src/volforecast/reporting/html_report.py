"""Main report orchestrator: loads experiment artifacts and assembles HTML.

See workspace/plans/html-report.md for the full implementation plan.
"""

from __future__ import annotations

from pathlib import Path

from volforecast.config import ExperimentConfig


def generate_report(
    config: ExperimentConfig,
    output_path: Path | None = None,
) -> Path:
    """Generate an interactive HTML report for a completed experiment.

    Loads metrics, predictions, and config from the experiment output directory,
    renders each report section, and assembles the final HTML file.

    Parameters
    ----------
    config : ExperimentConfig
        The experiment configuration (used to locate saved artifacts).
    output_path : Path, optional
        Override output path. Defaults to ``{experiment_dir}/report.html``.

    Returns
    -------
    Path
        Absolute path to the generated ``.html`` report file.
    """
    # TODO: implement — full plan in workspace/plans/html-report.md
    #
    # Implementation steps:
    # 1. Load metrics via persistence.load_all_metrics(config)
    # 2. Load predictions via persistence.load_predictions(config, symbol, horizon)
    #    for each symbol/horizon combination
    # 3. Load config snapshot from experiment_dir(config) / "config.yaml"
    # 4. Call each section renderer from reporting.sections (summary, forecast_vs_actual,
    #    qlike_analysis, statistical_tests, economic_value, diagnostics)
    # 5. Render base.html Jinja2 template with all section HTML fragments
    # 6. Write assembled HTML to output_path
    # 7. Return output_path
    raise NotImplementedError("TODO: implement report generation")
