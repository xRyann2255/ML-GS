# Session 3: Write Detailed Copilot Prompts

I need to write a series of extremely detailed prompts that I will give to GitHub Copilot on my GS work machine (H:\ml-vol-estimator) to implement the next phases of my ML vol forecasting project.

Context:
- Read notes/ml_vol_forecasting_docs.md for the complete current state
- The review session (notes/review-codebase-audit.md) identified: 2 Critical correctness bugs (CV purge gap not enforced for h=22, QLIKE log-space sign convention reversed), FeatureLayer protocol cannot serve Layers 2-5, ensemble strategy revised to prediction blending at all horizons (not stacking), 5 P0 debt items, and a 16-week phased roadmap. Top 5 actions: fix correctness bugs, extend protocol + P0 debt, build QLIKE tournament, implement tradeable signal, use prediction blending.
- The project reference was updated with [INSERT FROM SESSION 2]
- Copilot has access to .github/prompts/ (48 slash commands), AGENTS.md, and the full memory/ system, but it doesn't have the deep context that Claude Code has from our sessions

Each prompt must be COMPLETELY SELF-CONTAINED -- include:
- Exact file paths to read/modify
- Exact function signatures expected
- Mathematical formulas where relevant
- Test patterns to follow (reference existing test files)
- Which existing patterns to reuse (registry decorators, feature layer protocol, etc.)
- Acceptance criteria (what "done" looks like)

Write prompts for these implementation tasks (priority order):

1. **P0 debt fixes:** shared safe_log utility, deduplicate log/lag/rolling pattern across feature layers

2. **Layer 2: Options-implied features:** VRP, skew, term slope, butterfly. Data access already works (marquee.py). Follow the AsymmetryLayer pattern.

3. **Layer 4: Cross-asset features:** Treasury slope, FX vol, commodity vol, Diebold-Yilmaz spillover. TSDB access already works.

4. **Layer 5: Calendar/event features:** FOMC, NFP, OpEx proximity, day of week, month. Pure calendar math, no data source needed.

5. **LightGBM with custom QLIKE objective:** Gradient and Hessian derivation in log-space, Optuna hyperparameter tuning, early stopping.

6. **Statistical tests:** Diebold-Mariano (HAC for h>1), Model Confidence Set (block bootstrap), Mincer-Zarnowitz efficiency regression.

7. **Full HAR baseline tournament:** Run all 7 HAR models on all 34 symbols, 3 horizons, expanding-window CV. Save results for comparison.

For each prompt, specify which existing slash command (/execute, /feature, /plan) should be used and which persona it activates. The prompts should be copy-pasteable directly into Copilot Chat.

No em dashes. Be extremely specific -- Copilot doesn't have our conversation history.
