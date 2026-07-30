---
name: ENGHUB
description: "Clone and navigate GS internal EngHub documentation from GitLab."
---

# ENGHUB — Engineering Documentation

> **Purpose:** Clone and navigate GS internal EngHub documentation from GitLab into `workspace/knowledge/`.

**Out of scope:** Editing upstream docs; publishing to EngHub; GitLab CI/CD; non-EngHub documentation sources.

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `ENGHUB` |
| **Scope** | Clone, update, and search EngHub GitLab repos |
| **Inputs** | GitLab repo paths, search terms |
| **Outputs** | Cloned docs under `workspace/knowledge/enghub/` |
| **Authority** | Read-only (git clone/fetch); writes only to `workspace/knowledge/` |

---

## When to Use

- User asks to set up, update, or search GS engineering platform docs.
- Need to pull reference material from an EngHub GitLab repo.

---

## Prerequisites

- Git available on `$PATH`.
- Network access to `gitlab.aws.site.gs.com`.

---

## Task Execution (Preferred)

```json
// workspace/tmp/enghub_args.json
{
  "command": "clone-all",
  "out_file": "workspace/tmp/enghub_out.txt"
}
```

Commands: `clone-all`, `clone-one`, `update-all`, `update-one`, `list`, `search`

For `clone-one`: `{"command": "clone-one", "path": "sdlc-global/cicd-platform-docs"}`
For `search`: `{"command": "search", "pattern": "pricing"}`
For `update-one`: `{"command": "update-one", "path": "cicd-platform-docs"}`

Task label: `enghub`

---

## Procedure (Legacy bash — prefer task above)

### Clone All Repos

```bash
skills/ENGHUB/src/clone-all.sh
```

### Update All Repos

```bash
skills/ENGHUB/src/update-all.sh
```

### Clone a Single Repo

```bash
skills/ENGHUB/src/clone-one.sh <gitlab-path> [target-dir]
# Example:
skills/ENGHUB/src/clone-one.sh sdlc-global/cicd-platform-docs
```

### Update a Single Repo

```bash
git -C workspace/knowledge/enghub/<repo> fetch --depth=1 --quiet
git -C workspace/knowledge/enghub/<repo> reset --hard origin/HEAD --quiet
```

All clones are shallow (`--depth=1 --single-branch`) to stay fast and small. The process is idempotent: clone what's missing, update what exists.

---

## Repo Structure

Most EngHub doc repos follow this pattern:

```
repo-root/
├── assembly.xml              # Manifest: which product dirs are published
├── pom.xml                   # Maven build config
├── README.md
├── product-a/
│   ├── mkdocs.yml            # Navigation tree + metadata
│   └── docs/                 # All markdown content
└── product-b/
    ├── mkdocs.yml
    └── docs/
```

### Key Files

| File | Purpose |
|------|---------|
| `assembly.xml` | Authoritative list of published product dirs |
| `{product}/mkdocs.yml` | Navigation tree (`nav:` key) — table of contents |
| `{product}/docs/intro.md` | Landing page; always exists; start here |
| `{product}/docs/**/*.md` | Documentation content |

---

## Navigation

### 1. Find Products in a Repo

```bash
ls workspace/knowledge/enghub/<repo>/ | grep -v -E '^(pom|assembly|settings|README|\.)'
```

### 2. Get Table of Contents

```bash
cat workspace/knowledge/enghub/<repo>/<product>/mkdocs.yml
```

### 3. Search

```bash
# Search all enghub docs
grep -r "<topic>" workspace/knowledge/enghub/ --include="*.md" -l

# Read landing page
cat workspace/knowledge/enghub/<repo>/<product>/docs/intro.md
```

### Adding a New Repo

1. Clone it: `skills/ENGHUB/src/clone-one.sh <group>/<repo>`
2. Add it to the registry in the memory file below.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Clone fails with 403 | GSSSO cookie expired | Re-authenticate via GSSSO skill |
| Repo not in registry | New EngHub repo | Add via `clone-one.sh` and update `enghub-repos.md` |

## Links

- memory/_dormant/sys/enghub-repos.md — full registry of all EngHub GitLab repos by category with clone paths
