---
name: SLANG_COPILOT
description: "Clone the Slang Copilot customization repo and set up Slang reference docs."
---

# SLANG_COPILOT — Slang Reference Docs Setup

> **Purpose:** Populate workspace with the Slang Copilot repo — Copilot agent customization and language reference for Slang development.

**Out of scope:** Editing upstream docs; contributing to the Slang Copilot repo; Slang script editing (use `SLANG_EDIT`).

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_COPILOT` |
| **Scope** | Clone Slang Copilot repo into `workspace/docs/slang/` for local AI reference |
| **Inputs** | None |
| **Outputs** | Slang reference docs under `workspace/docs/slang/` |
| **Auth** | Network access to `gitlab.aws.site.gs.com` |
| **Authority** | Read-only (git clone); writes only to `workspace/docs/` |

---

## When to Use

- First-time workspace setup — need Slang language reference docs locally.
- Docs are missing or stale and need a refresh.
- User asks about Slang syntax/builtins and docs haven't been cloned yet.

---

## Repo

**Source**: [eq-tech/booking-controls/slang-copilot-code](https://gitlab.aws.site.gs.com/eq-tech/booking-controls/slang-copilot-code)

## Task Execution (Preferred)

```json
// workspace/tmp/slang_copilot_args.json
{
  "command": "clone",
  "out_file": "workspace/tmp/slang_copilot_out.txt"
}
```

Commands: `clone`, `update`, `status`

Task label: `slang-copilot`

---

## Setup (Legacy bash — prefer task above)

```bash
cd /tmp
git clone --depth=1 --single-branch https://gitlab.aws.site.gs.com/eq-tech/booking-controls/slang-copilot-code.git
mkdir -p workspace/docs/slang
cp -r /tmp/slang-copilot-code/.github/* workspace/docs/slang/
rm -rf /tmp/slang-copilot-code
```

## Update

Re-run the same clone + copy commands above.

## Navigate

```bash
find workspace/docs/slang -type f                              # list all files
grep -r "pricing" workspace/docs/slang/ --include="*.md" -l    # search topic
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Copilot missing Slang context | Docs not cloned | Run setup script to clone Slang reference docs |
| Stale docs | Docs not updated | Re-run clone to refresh |

## Related Slang Skills

| Skill | Purpose |
|-------|---------|
| `SLANG_READ` | Read script content (VFS-first, CVS fallback) |
| `SLANG_EDIT` | Edit, create, delete scripts (VFS-first, secexpr fallback) |
| `SLANG_LINT` | Run native lint on scripts |
| `SLANG_CLEANUP` | Apply formatting/best-practice conventions |
| `SLANG_REVIEW` | Submit scripts for code review |
| `SLANG_REVIEW_INSPECT` | Inspect review containers |
| `SLANG_REGTEST_FIX` | Fix failing RegTests |
| `SLANG_GLIMPSE` | Search Slang codebases via ELPS/Glimpse |
| `CVS` | CVS revision history, diffs, blame |

## Links

- memory/slang/language.md — Slang language reference
- memory/slang/best-practices.md — Slang coding conventions
