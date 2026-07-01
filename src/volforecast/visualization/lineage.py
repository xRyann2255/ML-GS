"""Mermaid flowchart generator for model lineage visualization."""

from __future__ import annotations


def _truncate_list(items: list[str], max_items: int = 3) -> str:
    """Join list items, truncating with '...' if too many."""
    if len(items) <= max_items:
        return ", ".join(items)
    return ", ".join(items[:max_items]) + ", ..."


def lineage_to_mermaid(
    lineage: dict,
    *,
    n_daily_features: int | None = None,
    main_model_label: str = "Main Model",
) -> str:
    """Convert a model lineage spec to a Mermaid flowchart LR string.

    Parameters
    ----------
    lineage : dict
        Keys: "base_model" (dict|None), "feature_stack" (dict|None).
    n_daily_features : int, optional
        Number of daily tabular features for the DAILY node label.
    main_model_label : str
        Display label for the main model node (e.g., "LightGBM<br/>5000 trees").

    Returns
    -------
    str
        Mermaid flowchart markup, or "" if no lineage to display.
    """
    base_model = lineage.get("base_model")
    feature_stack = lineage.get("feature_stack")

    if not base_model and not feature_stack:
        return ""

    lines: list[str] = ["flowchart LR"]

    # DAILY node (always present)
    if n_daily_features is not None:
        daily_label = f"Daily Features<br/>{n_daily_features} columns"
    else:
        daily_label = "Daily Features"

    # MODEL node
    model_label = main_model_label

    # Build feature_stack nodes if present
    if feature_stack:
        source = feature_stack.get("source_model", "LSTM").upper()
        outputs = feature_stack.get("outputs", [])
        seq_features = feature_stack.get("sequence_features", [])
        params = feature_stack.get("model_params", {})

        # SEQ node
        seq_label = f"Sequence Features<br/>{_truncate_list(seq_features)}"
        lines.append(f'    SEQ["{seq_label}"] --> {source}["{_build_model_sublabel(source, params)}"]')

        # LSTM/source → FEAT
        feat_label = f"Stacked Features<br/>{_truncate_list(outputs)}"
        lines.append(f'    {source} --> FEAT["{feat_label}"]')

    # DAILY → MODEL
    lines.append(f'    DAILY["{daily_label}"] --> MODEL["{model_label}"]')

    # FEAT → MODEL (if feature_stack)
    if feature_stack:
        lines.append("    FEAT --> MODEL")

    # BASE → MODEL (if base_model, dashed edge)
    if base_model:
        name = base_model.get("name", "base")
        features = base_model.get("features", [])
        base_label = f"{name}<br/>{len(features)} features"
        lines.append(f'    BASE["{base_label}"] -.init score.-> MODEL')

    # Output node (stadium shape)
    lines.append('    MODEL --> OUT(["Prediction"])')

    return "\n".join(lines)


def _build_model_sublabel(source: str, params: dict) -> str:
    """Build a descriptive label for the sequence model node."""
    parts = [source]
    sublabel_parts = []
    if "hidden_dim" in params:
        sublabel_parts.append(f"hidden={params['hidden_dim']}")
    if "n_layers" in params:
        sublabel_parts.append(f"{params['n_layers']} layers")
    if sublabel_parts:
        parts.append("<br/>" + ", ".join(sublabel_parts))
    return "".join(parts)
