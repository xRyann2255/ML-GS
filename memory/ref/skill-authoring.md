---
created: 2026-04-22
updated: 2026-04-22
tags: [skills, authoring, vscode, validation, frontmatter, links]
status: active
relates:
  - ref/skill-scripts.md
---

# SKILL.md Authoring Rules

VS Code validates SKILL.md files. These rules prevent warnings/errors.

## Frontmatter Attributes

Only these YAML frontmatter keys are supported:

| Attribute | Required | Purpose |
|-----------|----------|---------|
| `name` | Yes | Skill identifier (must match folder name, UPPER_SNAKE_CASE) |
| `description` | Yes | One-line or multi-line skill description |
| `argument-hint` | No | Hint text for skill invocation |
| `compatibility` | No | Compatibility constraints |
| `disable-model-invocation` | No | Prevent model from auto-invoking |
| `license` | No | License info |
| `metadata` | No | Arbitrary metadata |
| `user-invocable` | No | Whether user can invoke directly |

**Never use `skill:` — it was the old convention but VS Code rejects it.** Use `name:` instead.

## Link Validation

The SKILL.md validator resolves markdown link targets as filesystem paths. Rules:

1. **No relative-path markdown links.** Avoid bracket-paren link syntax pointing to relative filesystem paths. The validator resolves from the workspace root, not the file's location, so relative paths won't match. Use plain text paths instead.
2. **No `#anchor` fragments.** The validator treats the fragment as part of the filename, causing false negatives. Strip anchors from link targets.
3. **Cross-skill references** (relative paths to other skill folders) also fail for the same path-resolution reason. Use plain text skill names instead.

### What to use instead

```
Instead of                                           → Use
`ref`                     → memory/ref/example.md
`SKILL`                       → OTHER_SKILL/SKILL.md
`text`             → memory/ref/example.md
```

The agent resolves plain text paths just as well — no markdown link syntax needed for agent-facing references.
