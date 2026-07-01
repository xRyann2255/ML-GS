---
created: 2026-04-14
updated: 2026-04-14
tags: [systems, canvas, appdir, infrastructure, deployment, sky-gateway, beans, rbac]
status: active
relates:
  - ref/gssso-auth.md
---

# Canvas / AppDir — GS Infrastructure Deployment Platform

AppDir 2.0 is the data model; Canvas is the UI/API layer. Both terms refer to the same platform: deployments, hosts, system accounts, BU/family/app hierarchy.

## Access Paths

- **Canvas backend API:** `https://api.canvas.site.gs.com:7443/v1` (desktop, GSSSO auth)
- **Sky Gateway:** `https://prod.gateway.sky.site.gs.com/skygateway/appdir2sg_prod/v1/appdir/api` (cloud-only)
- **Canvas UI:** `https://canvas.site.gs.com/#/deployment/{did}` or `https://canvas.io.gs.com`

## Hierarchy

`BusinessUnit → SubBusinessUnit → Family → Application → Deployment (DID) → {Resources, Hosts, SystemAccounts}`

Best starting point for an unknown DID: `/v1/hierarchies/did-{did}` — returns full org chain in one call.

## Key Concepts

- **Bean** = canonical resource template. Resources inherit `VMShape` (cores, memory, size) from their bean when not locally overridden. Fetch via `/v1/beans/{ids}/versions`.
- **DC vs EC:** `attributes.Elasticity.isElastic` — `"False"` = data center, `"True"` = elastic cloud.
- **Role checking:** `/v1/appdir-entities/new/for-current-user` returns user's family assignments + roles. Match `familyId` + `rmsResponsibilityCode` for authorization gates.

## Our Skill

`CANVAS` (`skills/CANVAS/`) — covers Canvas backend + Sky Gateway. Endpoints: hierarchy, deployments, resources, beans, hosts, system accounts, org structure, RBAC, storage, certificates, audit.

## Cross-Team Implementations (Apr 2026)

Renamed to `CANVAS` (Apr 2026) to align with firm-wide convention. Same underlying platform as other teams' `canvas` skills.

| Repo | Path | Notes |
|------|------|-------|
| equities/eq-cp/ca-dev-ai | `skills/canvas/SKILL.md` | Node/resource inventory |
| ficc-tech/credit/credit-ai-workspace | `skills/canvas/SKILL.md` | Same template |
| equities/equities-fast/fa-ai-workspace | `skills/canvas/SKILL.md` | Same template |
| eq-tech/asia-cep-ai-tools/exec-platform-ai-sharing | `shared/skills/canvas/SKILL.md` | Most feature-rich shared version — adds beans, families, resources, DIDs |
| equities/dmm/sonic-agent | `sonic-agent-skills/skills/handlers/canvas/` | Python handler with 6hr caching |
| secdb/secdb-runtime/secdb-services-copilot | `.github/skills/secdba-canvas-auth/` | Uses Canvas roles for SecDBA auth verification |
