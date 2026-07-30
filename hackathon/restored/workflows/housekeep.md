# Workflow: Housekeep

Housekeeping loop: run linters, fix issues, re-verify. Route design-compliance findings to `/cure`.

---

## Entry Conditions

Enter when:
- User explicitly uses `/lint-workspace` or `/housekeep`.
- Task pattern matches: "lint", "clean up", "fix lint", "maintenance"

---

## Loop

1. **SCAN** — Run workspace linters (code lint, structural checks). Collect findings.
   - Separate: housekeep-scope (lint, schema, broken links) vs. cure-scope (design violations).
   - If only cure-scope found → report and recommend `/cure`. Stop.
2. **FIX** — Apply changes: one logical fix at a time, lowest risk first. Skip failures and continue.
3. **VERIFY** — Re-run the checks that triggered the workflow. Confirm no new violations.
   - If new violations: loop back to FIX (max 2 loops).
4. **REPORT** — Summary of what was fixed, what remains. Numbered next-steps.

---

## Constraints

- Design-compliance violations are `/cure` domain — never fix those here.
- Small, reversible diffs only.
- Max 2 FIX↔VERIFY loops before reporting remaining issues.

---

## Allowed Personas

| Phase | Allowed |
|-------|---------|
| SCAN | MODEL-BUILDER |
| FIX | MODEL-BUILDER |
| VERIFY | MODEL-BUILDER |

## Error Handling

Per `_protocol.md` error hooks (4-class model).
- Lint/schema tool failures: retry once, then report tool failure.
- Memory write failures: follow memory governance hard gates.

---

## Constraints

- Memory maintenance follows governance rules — never write unstructured content to `memory/`.
- Lint tasks must use the workspace lint tools.
- Verification re-runs the same checks that triggered the workflow — no partial verification.
- Changes must be small, reviewable, and reversible.
- **Design-compliance remediation belongs to `cure.md`.** Housekeep runs design lint (structural category) for mechanical checks but never touches compliance findings. If compliance issues are detected, report them and recommend `/cure`.
