---
created: 2026-03-01
updated: 2026-03-01
tags: [systems, enghub, documentation, gitlab, gs-internal]
status: dormant
relates:
  - ref/python-setup.md
---

# EngHub

Goldman Sachs' internal documentation platform. Each engineering platform publishes docs from a GitLab repo into EngHub. Repos follow a common structure (`assembly.xml` manifest, `{product}/mkdocs.yml` nav tree, `{product}/docs/` content).

## How I Use It

I shallow-clone EngHub doc repos into `workspace/docs/enghub/` so I can read them locally. My skill guide (`skills/ENGHUB/SKILL.md`) has the full repo registry with GitLab paths — I clone and update repos directly from those instructions.

## Detailed Reference

My full skill guide lives in `skills/ENGHUB/SKILL.md`. It covers:

- Full repo registry with GitLab paths (clone URLs derivable from paths)
- How I clone and update doc repos (commands, not a script)
- Repo structure (assembly.xml, mkdocs.yml, product dirs)
- Navigation patterns I follow (finding products, reading nav trees, locating content)
- Product breakdowns per repo

## Quick Navigation

```bash
# List products in a repo
ls workspace/docs/enghub/<repo>/ | grep -v -E '^(pom|assembly|settings|README|\.)'

# Read nav tree
cat workspace/docs/enghub/<repo>/<product>/mkdocs.yml

# Search all enghub docs
grep -r "<topic>" workspace/docs/enghub/ --include="*.md" -l
```
