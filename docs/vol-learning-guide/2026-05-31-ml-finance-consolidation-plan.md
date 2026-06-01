# ml-finance → vol-learning-guide Consolidation Plan

**Date:** 2026-05-31
**Goal:** Port the genuinely-useful, general ML methodology out of the archived `guides/ml-finance/` ("Risk as Alpha") guide into `vol-learning-guide`, then archive the old guide and all remaining risk-as-alpha material.
**Source of plan:** gap-analysis workflow (`ml-finance-vol-gap-analysis`, 29 agents) comparing all 14 ml-finance chapters against the 18 vol-guide chapter files.
**Execution mode (user-chosen):** draft ALL 9 sections, then a single review pass.
**Status: COMPLETE (2026-06-01)** — all 9 sections drafted, reviewed, fixed, and verified (clean compile, 0 errors / 0 undefined refs); `guides/ml-finance/` archived to `archive/risk-as-alpha/`; references updated; 7 markdown twins regenerated; committed and synced to `main` + `docs-only`.

## Verdict

- **5 of 14 ml-finance chapters → nothing to port** (archived as-is):
  - Ch1 Asset Pricing, Ch2 Intermediary Asset Pricing, Ch3 Risk Systems/VaR, Ch10 Labeling/Targets — pure risk-as-alpha / off-topic for single-asset RV forecasting.
  - Ch4 Microstructure — general content already covered in vol-guide ch03/ch08/ch09/ch10.
- **9 of 14 chapters → 9 consolidated edit tasks** across 7 vol-guide chapters. **No new chapters.** Three tasks also fix pre-existing internal inconsistencies in the vol-guide.

## The 9 scaffold tasks (all edit-existing)

| # | Target | Section added | Source (ml-finance) | Reframe | Priority | Status |
|---|--------|---------------|---------------------|:------:|:------:|:------:|
| 1 | ch06 har-model | Ridge + Elastic-Net HAR ("Ridge/Lasso-HAR" baseline; collinearity angle) | Ch5 | low | High | done |
| 2 | ch11 tree-methods-vol | Tree Foundations (CART/bagging/RF) — fixes ch12 prereq gap | Ch6 | low | High | done |
| 3 | ch16 forecast-evaluation | CPCV, PBO, Haircut/multiple-testing, cross-sectional CV leakage, 1-SE rule, trial-counting, survivorship | Ch5/8/9/11 | med | High | done |
| 4 | ch11 tree-methods-vol | TreeSHAP + SHAP plot toolkit | Ch7/14 | low | Med | done |
| 5 | ch10 feature-engineering | Incremental-info test, Spearman stability metric, signed-√ transform | Ch7/9 | med | Med | done |
| 6 | ch13 hybrid-ensemble | GMM/EM/BIC + Markov-switching regime ID — fixes ch11 dangling ref | Ch13 | high | Med | done |
| 7 | ch17 applications-projects | Transaction costs, turnover, net economic value — delivers ch16's promised cost test | Ch12 | med | Med | done |
| 8 | ch15 spillovers-connectedness | Pooled panel forecasting across instruments | Ch8 | med | Low | done |
| 9 | ch17 applications-projects | Communicating vol-forecasting results | Ch14 | med | Low | done |

### Internal inconsistencies this also fixes
1. ch12's prereq box assumes ch11 taught CART/split/bagging — ch11 currently skips it → Task 2.
2. ch11 (~line 488) forward-references a "GMM-based regime probability" never defined → Task 6.
3. ch16 repeatedly requires improvements to "survive transaction costs"/report turnover but never gives the method → Task 7.

## Sequencing (per gap-analysis synthesis)
- Task 2 (ch11 foundations) early — highest structural-integrity fix.
- Task 1 (ch06 ridge) before/with Task 3's 1-SE-rule note.
- Task 3 (ch16) before Tasks 8 (ch15) and 9 (ch17) — they cross-link ch16's CV-leakage and overfitting material.
- Task 4 (ch11 TreeSHAP) before Task 5 (ch10 stability metric references it).
- Tasks 7+9 share ch17 — write in one pass (costs first, then communication). Tasks 2+4 share ch11.

## Archive step (after done + review)
1. `git mv guides/ml-finance/ archive/risk-as-alpha/guides/ml-finance/`
2. Update **live** references (leave historical logs as-is):
   - `.claude/skills/sync-docs/SKILL.md` — drop ml-finance from compile loop, commit, docs-only sync, "what stays" list.
   - `.claude/skills/research/SKILL.md`, `.claude/skills/write-chapter/SKILL.md` — drop ml-finance from guide lists.
   - `CLAUDE.md` — repo structure tree + docs-only sync section.
   - `README.md` — guides table + repo structure tree.
3. Leave historical: `logs/progress.md`, `docs/claude-code-optimization/*`, `docs/superpowers/plans/*`.
4. Regenerate vol-guide markdown copies (convert-chapter-markdown) for changed chapters; recompile via /sync-docs.
