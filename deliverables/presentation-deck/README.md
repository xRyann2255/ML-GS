# Predicting Volatility, the deck

Final deliverables of the 16-17 Aug 2026 live-editing session. 28 slides, self-contained
HTML, arrow keys to present (several slides step through equation builds and diagrams
before advancing).

| File | What it is |
|---|---|
| `presentation-template.html` | The canonical frozen deck. Byte-identical to `-latest` unless a live edit has not been re-frozen. |
| `presentation-latest.html` | The presented file. Rebuilt from the template by `reorder_model_first.py.txt`. |
| `pca-surface-snippet.html` | Standalone copy of the layer-2 IV-surface PCA animation. |
| `har_equation.svg` | The assembled HAR-IV equation (matplotlib render), kept as a build asset. |
| `generate.py.txt` | v1 generator (11-slide deck from the tournament dashboard). Historical. |
| `reorder_model_first.py.txt` | v2 build script: template to latest, plus the real-GSVIVS01 chart graft on GS. |
| `reorder_model_first.legacy.py.txt` | The pre-v2 lift-and-retarget script. Historical. |
| `ale_data.py.txt` | ALE curve data for the response-curve slide. |
| `session-transforms/` | The one-shot scripts that produced the session's slide changes, in order of application. Their output is baked into the template; kept for provenance. |

Scripts are shipped as `.py.txt` because this branch must carry no Python files.
Canonical working copies live in `ml-vol-estimator/workspace/presentation/` (not in git).
