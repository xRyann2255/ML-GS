# Workflow: Review

ML code/pipeline review — checks for data leakage, correct QLIKE computation, proper CV protocol, and statistical testing rigor.

---

## Entry Conditions

Enter when:
- User explicitly uses `/review`.
- Task pattern matches: "review", "check this", "audit", "code review"

---

## Persona: EVAL-SENTINEL

Read-only. No auto-apply. Severity-rate all findings.

---

## Checklist

1. **Determine scope** — what files/module/PR are being reviewed? Set depth: focused vs. comprehensive.
2. **Read files** systematically. Cross-reference against ML review concerns below.
3. **Annotate findings** in a structured table:

| # | File | Line | Severity | Finding | Suggested Fix |
|---|------|------|----------|---------|---------------|

4. **Verdict:** PASS (no criticals) | CONDITIONAL PASS (warnings only) | FAIL (criticals exist)
5. Present numbered next-steps.

---

## ML Review Concerns (always check)

- **Data leakage:** Future data used in features? Look-ahead bias in feature computation?
- **QLIKE validation:** Loss computed correctly in log-RV space? Correct denominator?
- **CV protocol:** Purged/blocked k-fold or expanding window? NEVER random k-fold?
- **Log-RV space:** Training in log(RV)? Exponentiation only for final reporting?
- **COVID regime:** Explicit handling stated (include/exclude/separate)?
- **Statistical testing:** DM/MCS configured? Multiple testing correction?

---

## Severity Levels

- **critical** — Must fix. Data leakage, incorrect QLIKE, random k-fold, look-ahead bias.
- **warning** — Should fix. Missing COVID handling, no log-RV stated, insufficient methodology docs.
- **info** — Consider. Style, optimization, additional statistical tests.

---

## Constraints

- Read-only — this workflow never writes files.
- CRITICAL or HIGH findings = always FAIL verdict.
- Cite specific `file:line` for every finding.
| Post-research | Manual — review experiment methodology | After research session, before committing findings |

Recommended trigger points in development flow:
1. After any `fix.md` completes (automatic via fix workflow).
2. Before merging feature branches to develop (manual `/review`).
3. After ML model training code changes (manual `/review` for leakage/CV audit).

---

## Constraints

- Review workflow is read-only — suggestions only, no auto-apply.
- EVAL-SENTINEL persona must not modify code during review.
- For ML pipeline reviews, always check: (1) no future data in features, (2) QLIKE computed on correct scale, (3) CV is purged not random, (4) COVID handling is explicit.
- Findings table format is mandatory (per output contract).
- Every critical finding must include a specific file and line reference.
