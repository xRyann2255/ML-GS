# Reasonable Deviations — Notes on López de Prado's AFML

**Source:** https://reasonabledeviations.com/notes/adv_fin_ml/
**Used in:** Ch 20 (Backtesting done right), Ch 21 (ML for trading), Ch 22 (Which strategy when — meta-labeling)

## Status

The WebFetch attempt returned only a structural summary because the target page reproduces substantial copyrighted material. The key concepts are listed below so Ch 20–22 know what to cover; the actual derivations will come from primary AFML chapters (when the book is available locally) or from my training knowledge plus the López de Prado SSRN preprints.

## Key concepts covered by the notes

1. **Financial ML as a distinct subject.** Finance-specific data structure and validation problems make standard ML workflows dangerous in trading.

2. **Data structures.** Time bars vs tick bars vs volume bars vs dollar bars; information-driven bars (tick imbalance, volume imbalance) respond to informed-trading activity and have better statistical properties than calendar-time bars.

3. **Feature labeling — the triple-barrier method.** Labels derived from whether the price first hits an upper barrier (profit take), a lower barrier (stop loss), or a time barrier (hold period). Dynamic horizons; much richer than fixed-horizon return labels.

4. **Sample weighting.** Labels in financial ML are not independent because of overlapping horizons. Sequential bootstrapping and uniqueness weights correct for this.

5. **Fractional differentiation.** Non-integer backshift operator balances the stationarity requirement (needed for most ML models) with memory preservation (needed for predictive power). Integer differencing destroys memory; fractional differencing keeps it.

6. **Cross-validation — purged K-fold and CPCV.** Standard k-fold CV leaks information in time-series data because overlapping training labels touch validation-period information. Purging (removing training samples whose label horizon overlaps the validation set) and embargoing (extending the purge by a small buffer to account for serial correlation) fix this. Combinatorial Purged CV runs this across many train/test splits to produce a *distribution* of out-of-sample Sharpe ratios.

7. **Feature importance.** López de Prado argues feature importance analysis is more reliable than backtest-driven research. MDI (mean decrease impurity) and MDA (mean decrease accuracy) are the primary approaches.

8. **Meta-labeling.** A secondary ML model decides whether to *act* on a primary signal — effectively a trade-level filter. Primary model generates "direction" (long/short), secondary model generates "size" (bet or skip).

## Notes for the PDF

- Ch 20 should cover CPCV with a full worked toy example — the concept is simple and the diagram is teachable.
- Ch 21 should frame the whole chapter around "validation is harder than prediction" and use triple-barrier + meta-labeling as the running examples.
- Ch 22 uses meta-labeling as the trade-level selector in the decision pipeline.
- Fractional differentiation is worth a dedicated section — it's one of the genuinely novel contributions of the book.
