---
description: "Slang development — full context: skill guides, tools, language reference, and search"
argument-hint: "task or script name"
model: Claude Opus 4.6
---

You are working on a **Slang** task. Slang is Goldman Sachs' proprietary scripting language running on SecDb.

## Skill Guides (operational how-to)

- `skills/SLANG_READ/SKILL.md`
- `skills/SLANG_EDIT/SKILL.md`
- `skills/SLANG_LINT/SKILL.md`
- `skills/SLANG_GLIMPSE/SKILL.md`
- `skills/CVS/SKILL.md`

## Language Reference (syntax, builtins, patterns)

- `workspace/docs/slang/copilot-instructions.md`
- `memory/slang/best-practices.md`
- `memory/slang/formatting.md`

## Key Reminders

- **VFS first:** Read scripts via `slang:/!NYC_Source/{script}.s` — zero allows. Only fall back to secexpr/CVS when VFS is unavailable.
- Use SLANG_GLIMPSE (`glimpse.py`) when script name is unknown.
- Use secexpr (`edit.py`) only for colon-named scripts and deletes.
- CVS is for revision history/diffs only — NOT for reading current content.
- All tool output goes to `workspace/tmp/`.
