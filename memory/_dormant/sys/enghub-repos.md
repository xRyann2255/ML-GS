---
created: 2026-04-13
updated: 2026-04-14
tags: [enghub, gitlab, documentation, repos, registry]
status: active
relates:
  - sys/enghub.md
---

# EngHub Repos — Registry

Full registry of GS internal EngHub documentation repos from GitLab. Used by the `ENGHUB` skill to clone into `workspace/knowledge/enghub/`. All repos are shallow-cloned from `https://gitlab.aws.site.gs.com`.

## CI/CD & Developer Experience

| Repo | GitLab Path | Content |
|------|-------------|---------|
| cicd-platform-docs | `sdlc-global/cicd-platform-docs` | CI/CD pipeline platform — build systems, deploy pipelines, artifact management |
| set-up-infrastructure | `developer-experience/enghub-happy-paths/set-up-infrastructure` | Infrastructure setup guides — provisioning, environment config |
| working-with-python | `developer-experience/enghub-happy-paths/working-with-python` | Python at GS — packaging, virtual envs, internal PyPI, best practices |
| enghub-solutions | `developer-experience/enghub-happy-paths/enghub-solutions` | Cross-cutting solution guides and patterns |
| well-architected-platform-docs | `developer-experience/well-architected/well-architected-platform-docs` | Architecture principles, design reviews, well-architected framework |

## IAM (Identity & Access Management)

| Repo | GitLab Path | Content |
|------|-------------|---------|
| iam-docs | `iam/iam-docs` | IAM platform — authentication, authorization, Kerberos, certificates, service accounts |
| application-entitlement-management | `developer-experience/enghub-happy-paths/application-entitlement-management` | App entitlement management — ACLs, role-based access |
| demise-webid | `developer-experience/enghub-happy-paths/demise-webid` | WebID deprecation guide — migration paths from legacy web identity |

## Cloud

| Repo | GitLab Path | Content |
|------|-------------|---------|
| cloud-platform-docs | `derun/sky/cloud-platform-docs` | Cloud platform (Sky) — compute, networking, load balancing, DNS |
| fi-docs | `infra/container-runtime/fi-docs` | Container runtime / foundational infra — Docker, Kubernetes, container orchestration |

## Foundational Infrastructure

| Repo | GitLab Path | Content |
|------|-------------|---------|
| dc-enghub | `foundational-infra/dynamic-computing/dc-enghub` | Dynamic computing — job scheduling, batch processing, grid compute |
| converge-docs | `foundational-infra/computing-and-development-platform-engineering/converge-docs` | Converge — development platform engineering, build tooling |
| inventory-central-enghub | `foundational-infra/inventory-management/inventory-central-enghub` | Inventory Central — asset tracking, host/service inventory |
| linux-image-enghub-docs | `derun/unixeng/linux-image-enghub-docs` | Linux image management — OS images, patching, golden images |
| luma-enghub | `infra/luma/luma-enghub` | LUMA — infrastructure management and automation |
| dev-desktop-docs | `derun/dev-desktop/dev-desktop-docs` | Developer desktop — devtools, workstation setup, H:\ drive tooling |

## Storage

| Repo | GitLab Path | Content |
|------|-------------|---------|
| storage-cdot-enghub | `foundational-infra/storage-products/storage-cdot-enghub` | CDOT storage — NetApp, NFS, filer management |
| storage-fourier-enghub | `foundational-infra/storage-products/storage-fourier-enghub` | Fourier storage — object storage, distributed FS |
| storage-onpremobs-enghub | `foundational-infra/storage-products/storage-onpremobs-enghub` | On-prem object storage — S3-compatible, MinIO |

## Observability

| Repo | GitLab Path | Content |
|------|-------------|---------|
| obs-and-rel-platform-docs | `sre/playground/obs-and-rel-platform-docs` | Observability & reliability — metrics, logging, alerting, SRE patterns |

## AI & Data

| Repo | GitLab Path | Content |
|------|-------------|---------|
| nlp-platform-enghub-documentation | `dsml/nlp/nlp-platform-enghub-documentation` | NLP platform — LLMs, text processing, model serving |
| alloy-platform-docs | `data-engineering/alloy/alloy-platform-docs` | Alloy — data engineering platform, ETL, data pipelines |
| quantum-docs | `quantumeng/quantum-data-discovery/quantum-docs` | Quantum — data discovery, catalog, lineage |
| ai-program-office | `developer-experience/enghub-happy-paths/ai-program-office` | AI program office — governance, policies, AI tooling guidelines |

## Web

| Repo | GitLab Path | Content |
|------|-------------|---------|
| web-platform-enghub-docs | `wf/web-platform/web-platform-enghub-docs` | Web platform — React, Angular, UI frameworks, web standards |

## Risk

| Repo | GitLab Path | Content |
|------|-------------|---------|
| work-with-tech-risk | `developer-experience/enghub-happy-paths/work-with-tech-risk` | Tech risk — vulnerability management, compliance, security practices |

---

## SecDB

| Repo | GitLab Path | Content |
|------|-------------|--------|
| secdb-platform-docs | `secdb/secdb-docs/secdb-platform-docs` | SecDB platform docs — Graph framework, Slang, PySlang, Java, Inform, Zebra, Slang Extension, SlangAI |

## Adding a New Repo

1. Clone: `skills/ENGHUB/src/clone-one.sh <group>/<repo>`
2. Add a row to the category table above.
3. Add the `clone_or_update` line to `skills/ENGHUB/src/clone-all.sh`.
4. Navigate: `cat workspace/knowledge/enghub/<repo>/<product>/mkdocs.yml` for the nav tree.
