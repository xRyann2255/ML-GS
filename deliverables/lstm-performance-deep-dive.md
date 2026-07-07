# LSTM Performance Deep Dive: Why We Are at 0.16 and What It Takes to Beat 0.129

**Date:** 2026-07-02
**Scope:** full audit of the LSTM implementation, pipeline integration, experiment record (trials 051 to 075), and the published state of the art, to answer: why does our best standalone LSTM sit at h=1 QLIKE ~0.162 when the tree champion sits at ~0.129, and what is the complete set of actions that could close the gap.
**Companion audit files (working artifacts, not part of this deliverable):** `workspace/tmp/lstm-audit-implementation.md`, `lstm-audit-pipeline.md`, `lstm-audit-record.md`, `lstm-audit-literature.md`. All file:line citations below refer to `ml-vol-estimator/src/volforecast/` (dev copy) unless stated.

---

## 1. Executive summary

**Direct answers to the questions asked:**

**Is it normalization?** Partly. Input normalization mechanics are clean (train-only fit, per fold, pad-aware). The problem is a design mismatch: per-symbol z-scored inputs against a raw pooled log-RV target whose per-symbol level the model cannot identify (trial-051 had no symbol identity at all; later trials only a static embedding). Rosenbaum and Zhang normalize the target scale per stock; we never do.

**Is it hyperparameters?** Not primarily, and we could not have known: the Optuna search is broken (Bug 1 below), so hyperparameters have never actually been searched. Every "tuned" trial trained identical configs differing only by seed, then installed sampled-but-never-evaluated parameters into production folds.

**Are there real errors?** Yes. Two high-severity bugs (dead HPO search; early-stopping validation leakage through synthetic dates), one blocking bug (the IV-context path, trial-075, cannot run at all on this snapshot: `UnboundLocalError`), and seven smaller defects. None of them corrupts the outer test sets, so the 0.162 number is real, but model selection, early stopping, and tuning have all been operating degraded.

**The dominant cause, however, is none of the above. It is the information set.** The standalone LSTM has never seen the inputs that power the champion: implied volatility and the options surface. The champion's edge is a har_iv_0dte linear spine plus IV-family features; every standalone LSTM saw either one day of intraday microstructure (no cross-day memory at all) or 22 days of RV-only daily features. Our Rosenbaum replication scored 0.16205 against HAR's 0.16186 in the same run, which is exactly what the paper predicts: on returns+RV inputs, an LSTM ties or slightly beats HAR. The remaining 330 bps to XGBoost (0.12941 same run) is carried by information the LSTM was never given, not by architecture.

**Calibration from the literature (Section 4):** the Rosenbaum-Zhang edge over HAR is roughly 10% of MSE, median, per stock, and a fixed 5-parameter rough-volatility blend matches their LSTM exactly. "LSTMs perform well" in that paper means "a universal LSTM on 862 pooled stocks matches or slightly beats per-stock HAR with ~100 parameters." We reproduced that. Nothing in the paper implies an LSTM on RV+returns should approach an IV-armed tree.

**Consequently the path to 0.129 is:** (1) fix the bugs, (2) fix the measurement protocol, (3) give the LSTM the champion's information (IV context and multi-day memory), (4) adopt the published training recipe (tiny capacity or HAR warm start, seed averaging, per-symbol target scaling), and (5) hold it to honest decision gates, including the possibility that the right end state is a hybrid (feature extractor or regime-gated blend) rather than a standalone win. Ranked attribution and the full plan follow.

---

## 2. Where we actually stand (the scoreboard)

Tree champions on the tournament window: XGBoost h=1 **0.12941** (trial-066 run; 0.1292 in the 067 reseed), LightGBM 5-seed mean **0.13679** (trial-047). All numbers are h=1 pooled log-space QLIKE; 1 bp = 1e-4.

| Trial | Setup | LSTM QLIKE | Same-run reference | Verdict |
|---|---|---|---|---|
| 051 | Standalone, 2340 x 5 ten-second bars, 1-day window, QLIKE loss | 0.4332 | HAR 0.1607 | Catastrophic; wrong inputs |
| 053 | Residual on LightGBM champion | 0.12878 | champion 0.12887 | Learns to output ~0 (noise target) |
| 054 | Residual, single fold, 6y OOS | 0.12053 | har_iv_0dte 0.12915 | Later ruled NOT ROBUST (1 fold, 1 seed, COVID in OOS) |
| 057b/058 | Residual retuned / rich channels + Optuna | 0.12353 / 0.12255 | champion 0.12188 / 0.12086 | Worse than base; "residual approach is DEAD" |
| 061b | Feature stack into LightGBM | stack = control 0.12869 | control 0.12869 | Tree ignores every LSTM column |
| **065/066** | **Rosenbaum daily LSTM, 22-day lookback, MSE** | **0.16205** | **XGB 0.12941, HAR 0.16186** | **Best standalone on the full pool; ties HAR, -330 bps vs XGB** |
| 066b/c | Residual on XGBoost | 0.12940 / 0.12989 | xgb 0.12938 / 0.12940 | Noise / worse; "line definitively closed" (2026-06-22) |
| 071/072b/073 | Standalone 5-min enriched (78 x 12), SPY+AAPL only | 0.3307 / 0.2369 / **0.1998** | HAR 0.1989 (2-symbol panel) | Line REOPENED: 073 in MCS, DM p=0.076; train_size dominates (+37 bps), bidir+capacity (+94 bps) |
| 074 | 21 symbols, single 252d fold, XGB-aligned OOS | ~10 bps behind XGB (exp-space) | XGB same window | LSTM wins 40.3% of observations; spike days +22 bps worse |
| 072 blend | 80/20 XGB/LSTM prediction blend | +0.62 bps over XGB | residual corr 0.34 | Real but negligible at current LSTM quality |
| 075 | IV context vector into LSTM head | never validly ran | n/a | Blocked by Bug 3 |

Three protocol facts that shape everything downstream:

1. **The 0.16-vs-0.129 gap has been measured properly exactly once** (trial-066, matched OOS dates). Most other comparisons cross universes (21 symbols vs SPY+AAPL), fold geometries, and date ranges. The 073 "0.1998 vs HAR 0.1989" reopening result is a 2-symbol panel and does not transfer to the pooled bar.
2. **Every LSTM number ever reported is single-seed**, inside a seed envelope LightGBM measured at +/-6.6 bps, and the seed itself differs by GPU count (Bug 5). Rosenbaum averages 10 seeds before reporting anything.
3. The Week-11 claim that an independently trained LSTM feature-stacked into XGBoost produced "a new best QLIKE, Sharpe 2.81" is **unregistered** (no number in trials.yaml) and inadmissible until multi-seeded, but it is also the most promising open lead (Section 7, Tier 4).

---

## 3. Real errors found (the direct answer to "are there bugs?")

Outer-test evaluation is clean: purge = max(purge_gap, h) on unique dates, train-only normalizer fits, no input/target lookahead (verified index math in `utils/targets.py:87`), loss identical to the eval metric, correct prediction alignment. The 0.162 is not an artifact. The bugs corrupt tuning, early stopping, and reproducibility:

| # | Severity | Bug | Mechanism | Fix |
|---|---|---|---|---|
| 1 | HIGH (any tuned trial) | **Optuna HPO is a dead search** | `runner.py:1439` passes the entire YAML `model.params` as `fixed_params`; `lstm_tuning.py:120` merges `{**sampled, **fixed_params}` so fixed overrides every sampled value; all trials train identically, differing only by seed (`seed + trial.number`). Then `runner.py:1512` installs `best_params`, which are Optuna's sampled, never-trained values, into the production folds. Trial-058 onward: hyperparameters were random draws selected by CV noise. The correct key-stripping logic exists but only in dead code (`lstm.py:572`, `tune_and_fit`, unused on the sequence path). | In the runner, strip the six tunable keys (`hidden_dim, n_layers, learning_rate, dropout, weight_decay, batch_size`) from `_tune_fixed` before calling the tuner, mirroring `_TUNABLE_KEYS` in lstm.py. One-line conceptually; add a regression test that two Optuna trials with different sampled params produce different training configs. |
| 2 | HIGH at h=5/22, MODERATE at h=1 | **Early stopping validates on leaked labels** | All three callers wrap fold tensors in synthetic one-date-per-row indices (`runner.py:1741`, `fold_worker.py:134`, `lstm_tuning.py:198`), so the date-aware val split in `lstm.py:318-360` degenerates to a row split and `val_purge_gap` (default 1, never overridden in any LSTM YAML) purges one ROW instead of h dates x 21 symbols. Epoch selection, ReduceLROnPlateau, and best-state restore all key on a contaminated val loss. The tabular path clamps `val_purge_gap = max(val_purge_gap, h)` (`runner.py:104`); the sequence path never does. | Thread real dates into the SequenceTensor wrappers (they exist upstream), or split val at the runner level with a purged date boundary. Also apply the `max(val_purge_gap, h)` clamp on the sequence path and set `val_purge_gap: 10` in LSTM configs (every LightGBM config already does this). |
| 3 | BLOCKING (trial-075) | **IV-context path cannot run** | GS `runner.py:2520` writes `model_params["context_dim"]` before `model_params` is bound at 2535: `UnboundLocalError` whenever `sequences.context_features` is set. The parallel fold path additionally never threads the context kwarg, and `fit` raises when `context_dim>0` without context. The one experiment designed to close the information gap has never validly run. | Reorder the binding, thread `context` through `_execute_fold`, add an integration test with a 2-feature context vector. Verify no trial-075 number is trusted until rerun. |
| 4 | MODERATE, silent | **Precision differs by execution path** | `_resolve_precision` matches `device == "cuda"` exactly (`lstm.py:85-88`); multi-GPU folds and all HPO trials use `cuda:N` and silently run fp32 while single-GPU refits run bf16. Explicit `bf16` + multi-GPU would crash autocast (`lstm.py:1017`). | Match on `device.startswith("cuda")`; pass bare device type to autocast. |
| 5 | MODERATE | **Seeds differ by GPU count** | Sequential path reuses seed 42 for every fold (`runner.py:1788`); parallel path adds `+fold_num` (`fold_worker.py:176`). Same YAML, different results depending on `n_gpus`. | Unify on `seed + fold_num` in both paths. |
| 6 | MODERATE (hygiene) | **HPO consumes outer test windows** | Tuning runs once pre-folds on the FULL panel (`runner.py:1484`); inner folds span later outer-test dates. Any tuned headline is not honestly out-of-sample (contained: only trial-058 tuned, and Bug 1 made the search inert anyway). | Tune inside the first outer training window only, or adopt nested CV. |
| 7 | LATENT | **Fold-cache fingerprint gaps** | GS cache key has no data fingerprint (`fold_cache.py:82-110`); sequence tensor content unfingerprinted in both trees; `norm_mode`, `source`, `bar_interval`, `context_features` absent from the config fingerprint; feature-stack cache keyed on positional train_idx with no universe/date hash (cross-experiment collision risk). | Add tensor + config-field hashes to the key; include date-range hash in the feature-stack key. |
| 8 | LATENT | **Feature-stack OOF leaks for h>1** | Inner OOF chunks have zero purge between chunks (`runner.py:927-949`), and fold k's features come from models trained on future chunks. `independent: false` is a stub training against a constant (`runner.py:955-961`). | Purge h dates at chunk boundaries; do not use `independent: false` until implemented. |
| 9 | LATENT | **Per-symbol normalizer passes unseen symbols through raw** (`pipeline/norm.py:111-115`) | Silent if the universe grows or a symbol lists mid-sample. | Raise or fall back to pooled stats with a warning. |
| 10 | MINOR | **QLIKE loss clamp creates a dead-gradient zone at cold start** | `_qlike_loss` clamps the whole diff at +/-10 (`lstm.py:261`), unlike the metric which clips only inside the exp (`metrics.py:46`). At init (head ~0, y ~ -8 to -12), low-vol samples sit in the zero-gradient region; with patience 5-7 on the leaky val set (Bug 2), the model can stop barely warmed up. Matches the recorded "converges in 7-12 epochs to a poor local minimum". | Initialize the head bias to the train-mean log-RV (one line, standard practice); clip inside the exp only. |

Also noted: `cv_for_horizon` drops `embargo` on horizon overrides (`config.py:315-327`), unused by LSTM trials today but a foot-gun; HPO swallows all exceptions (`lstm_tuning.py:413`), so a crashing search region records as FAIL silently.

---

## 4. Rosenbaum-Zhang: what the paper actually shows vs what we built

Verified against the full arXiv 2206.14114 text (Rosenbaum and Zhang, "On the universality of the volatility formation process", published Frontiers of Mathematical Finance 2024; follow-up Tang-Rosenbaum-Zhou arXiv 2311.04727 replicates on crypto).

**Their recipe:** inputs x_t = (sigma_t^2, r_t), lookback 22 days (most signal within 15); NO log transform, per-stock scale normalization (sigma divided by root mean sigma^2; returns z-scored per stock); target = next-day scaled vol, linear head, **MSE loss** (QLIKE appears nowhere); 2-layer LSTM with **hidden dim 2** (~100 parameters), SiLU, no dropout; pooled training on **862 US stocks** 2010-2015 (~1.3M rows), Adam 1e-3, batch 512, **5 epochs**, no early stopping; **10 seeds averaged**; test 2016-2020 with COVID (Feb-Jun 2020) excluded; evaluation = per-stock MSE ratio vs HAR.

**Their result:** median MSE ~90% of HAR's. Universal beats sector-specific; per-stock fine-tuning adds nothing; US-trained transfers zero-shot to Europe; and a fixed-parameter RFSV+QRH blend (5 parameters, H=0.055, lambda~0.1) **matches the LSTM exactly**. The paper's content is the universal endogenous vol-formation mechanism, not deep architecture.

**Our trials 065/066 vs the paper:**

| Dimension | Paper | Ours | Materiality |
|---|---|---|---|
| Universe | 862 stocks, ~1.3M rows | 21 symbols, ~10K rows/fold | Huge: pooling breadth is their central claim |
| Inputs | (sigma^2, r), 2 channels | 5 channels incl. HAR-style w/m aggregates | Deviates from "faithful"; moderate |
| Scale | per-stock vol scaling, no log | pooled z-score inputs, raw pooled log-RV target | Material: per-stock scale identity lost |
| Hidden dim | 2 | 32 | Paper says bigger buys nothing; 32 raises overfit risk on 100x less data |
| Seeds | 10 averaged | 1 | Material: our own seed envelope is +/-6.6 bps |
| Loss/metric | MSE on scaled vol; per-stock MSE ratio | MSE loss; pooled QLIKE tournament | Metric mismatch; paper never claimed QLIKE gains |
| COVID | excluded from test | included | Material under our own regime rule |
| Competition | per-stock HAR/AR/RFSV (no IV) | 128-feature IV-armed XGBoost | The decisive difference |

**The honest conclusion:** our replication succeeded on the paper's own terms (LSTM 0.16205 vs HAR 0.16186: tie-to-slightly-better is exactly the published result at our data scale). The paper does not promise what we asked of it. The 330 bps to XGBoost is the IV/options information advantage plus tree-friendly tabular structure, and no returns+RV-only sequence model of any architecture should be expected to close it. This reframes the goal: **the LSTM must ingest the champion's information set, and/or be used where sequences genuinely add signal (intraday shape, regime persistence), and/or be hybridized.**

Supporting literature calibration (full citations in `lstm-audit-literature.md`): HARNet (arXiv 2205.07719) shows QLIKE as a training loss unlocks gains where MSE stalls, but ONLY with a HAR-consistent warm start; random-init QLIKE training is unstable, which matches our cold-start pathology (Bug 10). Rahimikia-Poon show the LSTM edge is regime-dependent: it wins calm days and loses jump days, exactly our +22 bps spike-day deficit. Guyon-Lekeufack's 2-feature TSPL regression explains up to ~65% of future daily RV and is the cheapest strong baseline we do not currently run. DeepVol's larger NN edges come from richer intraday inputs, not bigger nets.

---

## 5. Root-cause attribution for the 330 bps (ranked)

1. **Information deficit (est. 200-280 bps of the gap).** No IV, no options surface, no VRP, no calendar distance ever reaches a standalone LSTM (the one config that tries, 075, is blocked by Bug 3). Additionally the 5-min configs (071-074) see one day only: HAR's weekly/monthly memory is structurally absent (the `parquet_5min_multiday` source exists and has never been used by the LSTM). Evidence: har_iv (a 4-parameter model WITH IV) beats every standalone LSTM ever run here; the daily LSTM ties HAR (RV-only information) almost exactly.
2. **Scale/identity mismatch (est. 20-60 bps).** Per-symbol z-scored inputs with a raw pooled log-RV target and no (or static-only) symbol identity make per-symbol levels partly unidentifiable; QLIKE ~ diff^2/2 for small log errors, so persistent per-symbol offsets are expensive. Rosenbaum solves this by scaling the TARGET per stock; we never have.
3. **Optimization pathology at cold start under QLIKE (est. 10-40 bps, config-dependent).** Zero-init head vs y ~ -9, saturating over-prediction gradient, dead-zone clamp (Bug 10), short patience on a leaked val set (Bug 2): the recorded "stops at epoch 7-12 barely moved from initialization" is this.
4. **Selection and measurement noise (does not move the true mean but corrupts decisions).** Dead HPO (Bug 1), path-dependent seeds (Bug 5), single-seed single-fold headline numbers, cross-trial universe drift (Bug B9 in the pipeline audit). Some past "improvements" and "failures" are within seed noise.
5. **Architecture (small residual factor).** 2340-step recurrence in the 10s configs was genuinely bad (vanishing gradients); the 78-step 5-min and 22-step daily configs are fine. Hidden 32-128 vs the paper's 2 is a real overfit risk at our sample size but secondary to items 1-2.

---

## 6. Dead ends already established (do not re-propose)

Evidence-backed closures from the experiment record: residual learning on any strong tree base (six trials; the residual is white noise and QLIKE's flat basin makes the LSTM a zero-attractor); richer intraday channels as a residual fix (the target is noise, not the features); feature-stacking a residual/QLIKE-trained LSTM's outputs into trees (tree ignores all columns); symbol embeddings to rescue residuals; the daily Rosenbaum LSTM as a direct champion challenger; prediction blending at current quality (provably capped ~0.6 bps at corr 0.34); raw-returns-only TCN standalone (0.306); trusting single-fold single-seed wins (the trial-054 trap).

---

## 7. Everything we can do to improve LSTM performance

Ordered by expected value per unit effort. Tiers 0-1 are prerequisites: without them we cannot even measure progress honestly.

### Tier 0: Fix the code (days)

0.1 Fix Bug 1 (strip tunable keys in the runner tuning block) and add the regression test.
0.2 Fix Bug 2 (real dates or runner-side purged val split; clamp `val_purge_gap` to max(h, 10); set `val_purge_gap: 10` in all LSTM YAMLs).
0.3 Fix Bug 3 (context binding order + thread context through parallel folds) so trial-075 can actually run.
0.4 Fix Bugs 4, 5 (precision prefix match; unified per-fold seeds).
0.5 Head-bias init to train-mean log-RV and metric-consistent clamp (Bug 10). This alone may cure the "7-12 epochs, barely moved" failure mode.
0.6 Add fingerprint fields (Bug 7) before any new experiment wave, or every rerun risks stale-cache contamination.

### Tier 1: Fix the measurement (days, in parallel)

1.1 One canonical comparison config (trial-066 pattern): full 21-symbol pool, pinned window, identical OOS dates for LSTM and XGBoost, DM test in the run.
1.2 **Seed-average the LSTM prediction** (5 seeds minimum, mean of predictions, Rosenbaum-style). This is not just noise reduction; ensembled NN predictions are typically a few bps better than any single seed. All headline claims from now on are seed-ensembled.
1.3 Report calm/spike-day QLIKE splits (top-decile |return| or RV) in every LSTM run, since the failure mode is concentrated there.
1.4 Register everything in trials.yaml at run time (071-074 currently live only in config headers and the journal).
1.5 Add the cheap strong baselines to the tournament: Guyon-Lekeufack TSPL regression and the fixed RFSV+QRH blend (5 parameters). If a future LSTM cannot beat these, it has learned nothing beyond the universal mechanism.

### Tier 2: Close the information gap (the main event, 1-2 weeks)

2.1 **IV context vector, fixed and extended (rerun of 075).** z-scored [atm_iv_1d, atm_iv_0dte, vrp_d, vvix_d, iv_skew_25d, iv_term_slope_0dte1w] concatenated at the pool-to-head junction. Cheap, surgical, directly injects the champion's strongest signal family. Expected: largest single gain available; if IV-in-LSTM cannot get standalone below ~0.145, the standalone bar is likely unreachable and effort should shift to hybrids.
2.2 **Daily-context channels per timestep (a "HAR-X sequence").** Instead of (or in addition to) the head-level context, build `daily_lookback` sequences whose per-day channels are the champion's daily features: log_rv_d/w/m, log_atm_iv (tenor-matched), vrp_d, iv_skew, days_to_fomc, signed_return_d. The LSTM then models the joint temporal dynamics of RV AND IV, which no tree sees as a sequence. This is the experiment the literature actually motivates: sequence models win when the sequence itself carries structure.
2.3 **Multi-day intraday memory.** Use the existing-but-never-LSTM-used `parquet_5min_multiday` source (e.g. 10 days x 78 bars) with hierarchical pooling: per-day intraday encoder (attention pool over 78 bars) producing a daily embedding, then a second-stage LSTM over the 10 daily embeddings. Gives intraday shape AND cross-day persistence without a 780-step recurrence.
2.4 Overnight/calendar channels: overnight gap return, day-of-week, FOMC/NFP/OpEx distances as context. Free information the tabular models exploit.

### Tier 3: Adopt the published training recipe (days, alongside Tier 2)

3.1 **Per-symbol target scaling** (Rosenbaum): predict per-symbol scale-normalized vol (or per-symbol demeaned log-RV), restore the scale at prediction. Removes the identity burden entirely; pairs with keeping per-symbol input z-scores.
3.2 **Capacity sweep downward, not upward:** hidden {2, 4, 8, 16, 32} on the daily variants. The paper's entire result lives at hidden 2 with 5 epochs; our 32-128 nets on 100x less data are the overfit-prone deviation. (Only after Bug 1 is fixed can this sweep actually run through Optuna.)
3.3 **Loss ablation, isolated:** (a) MSE on per-symbol-scaled vol (pure Rosenbaum), (b) MSE on log-RV, (c) QLIKE with warm start. HARNet's finding: QLIKE training only stabilizes with a HAR-consistent initialization; option (c) should be pretrained 3-5 epochs under MSE then fine-tuned under QLIKE, or initialized from a fitted HAR mapping.
3.4 Short lookbacks are fine (paper: most signal within 15 days); prefer L=22 over 44 unless 2.2's IV channels argue otherwise.
3.5 Train-window size: 073 showed train_size 2000 was worth +37 bps on the small panel; on the full pool prefer max-window folds over many short folds for NN training, with the purge/embargo discipline unchanged.
3.6 Ten-seed prediction averaging for any headline claim (Tier 1.2, repeated here because it is also a performance lever, not just hygiene).

### Tier 4: Architecture and hybridization (second wave)

4.1 **Verify and formalize the Week-11 lead:** independently trained LSTM (raw log-RV target, 44-day daily lookback) feature-stacked into XGBoost, which claims "new best QLIKE, Sharpe 2.81" but is unregistered. If it survives seed-ensembling and purged OOF (Bug 8 fixed), this, not standalone, may be the fastest route to a champion improvement, and it sidesteps the zero-attractor because the LSTM trains on levels, not residuals.
4.2 HARNet-style warm start: initialize a small recurrent/convolutional net to reproduce fitted HAR-IV weights, then fine-tune under QLIKE. Gives the linear spine for free inside the network.
4.3 Regime-gated ensemble (Rahimikia-Poon): tree forecast on spike days, blend or LSTM on calm days; gate on yesterday's realized measures. Our own data (LSTM +22 bps worse on spikes, wins 40.3% of observations overall) says the conditional blend beats the unconditional one that already yielded +0.62 bps.
4.4 GRU/TCN variants of 2.3's hierarchical design; transformer-lite (attention over daily summary tokens) only after LSTM variants plateau, since the sample size favors small recurrent nets.
4.5 Multi-horizon heads (h=1,5,22 jointly) as regularization once h=1 works; do not lead with this.

### Tier 5: Decision gates and the honest exit

- Gate A (after Tiers 0-2): seed-ensembled standalone LSTM with IV context, canonical config. If QLIKE > 0.150: stop pursuing standalone-beats-champion; pivot fully to 4.1/4.3.
- Gate B (after Tier 3 recipe): if 0.135-0.150, continue one architecture wave (Tier 4); if <= 0.135, scale seeds and window and attempt the champion head-on.
- Gate C (always): any claimed win must be seed-ensembled (>=5), DM-tested against XGBoost on identical OOS dates, reported with calm/spike split, and economically validated on the GSVIVS01 overlay (trial-074c config exists) before the word "champion" is used.
- The realistic end states, in descending probability: (1) LSTM contributes via feature-stack or regime-gated blend worth 5-30 bps on top of 0.129; (2) IV-context standalone LSTM lands 0.13-0.14, competitive but not champion; (3) standalone < 0.129. The literature supports (1)-(2); nothing published supports (3) without the information set plus far more data.

---

## 8. Concrete next experiments (ready to config)

| ID | What | Key config deltas | Success bar |
|---|---|---|---|
| 076 | Bug-fix validation rerun of 066 | identical to 066 + Tier 0 fixes + 5-seed ensemble | Establishes the TRUE current baseline (expect 0.155-0.165) |
| 077 | 075 fixed: IV context vector | context_features [atm_iv_1d, atm_iv_0dte, vrp_d, vvix_d, iv_skew_25d, iv_term_slope_0dte1w], 5-min 78x12, 5 seeds | < 0.150 to pass Gate A |
| 078 | HAR-X daily sequence | daily_lookback 22 x [log_rv_d/w/m, log_atm_iv_tenor, vrp_d, iv_skew, days_to_fomc, signed_return_d, abs_ret_d]; per-symbol target scaling; hidden 8; MSE-then-QLIKE | beat har_iv (~0.152) standalone |
| 079 | Hierarchical multiday 5-min | parquet_5min_multiday 10d x 78 bars, day-encoder + cross-day LSTM, IV context at head | beat 077 |
| 080 | Capacity/loss grid on 078 | hidden {2,4,8,16,32} x loss {mse-scaled, mse-log, qlike-warm}, Optuna (post-fix), seed-averaged | pick recipe; document seed envelope |
| 081 | Feature-stack v3 verification | Week-11 setup, purged OOF, independent=true, 5 seeds, registered | reproduce "best QLIKE" claim or bury it |
| 082 | Regime-gated blend | tree on spike-gate days, 077/079 LSTM else; gate = trailing RV percentile | beat 0.12941 with DM p<0.05 + GSVIVS Sharpe check |

---

## 9. Expected impact summary

| Intervention | Expected h=1 QLIKE effect | Cost | Confidence |
|---|---|---|---|
| Tier 0 bug fixes | 0 to +15 bps directly; unblocks everything | days | High (correctness) |
| Seed ensembling (5-10) | +3 to +8 bps and honest error bars | trivial | High |
| IV context (077) | +50 to +150 bps vs 0.162 | small | Medium-high |
| HAR-X daily sequences (078) | +30 to +100 bps | medium | Medium |
| Multi-day hierarchical (079) | +10 to +40 bps over 077 | medium | Medium |
| Rosenbaum recipe (scaling, tiny nets, warm start) | +10 to +40 bps | small | Medium-high |
| Feature-stack v3 verified (081) | +5 to +30 bps ON TOP of the champion | small | Unknown until verified |
| Regime-gated blend (082) | +5 to +20 bps on champion | small | Medium |
| Standalone LSTM < 0.129 | reaching it requires most of the above compounding | weeks | Low-medium; treat as stretch, not plan |

---

## 10. Appendix: what is verified clean (do not re-audit)

Outer CV purge and date handling; train-only normalizer fits with pad-aware stats; sequence construction is backward-looking (no lookahead into t+1..t+h); target index math; loss = metric in log space (exp is the QLIKE-optimal retransform; Duan intercept applied on top); prediction/actual positional alignment on both execution paths; eval-mode and masking hygiene (pack/unpack, attention mask, dropout off at inference); residual-contract fail-loud checks; early-stopping best-state restore; save/load round-trip; atomic cache writes. Full verification notes with line cites in `lstm-audit-implementation.md` section D and `lstm-audit-pipeline.md` "Verified-clean items".
