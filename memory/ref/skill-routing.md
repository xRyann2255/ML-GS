---
created: 2026-04-24
updated: 2026-04-24
tags: [ref, skills, routing, search, nds, canvas, host, lookup]
status: active
relates: []
---

# Skill Routing — Discovery & Hostname Resolution

## Discovery Rule

**Before implementing infrastructure or lookup tasks, always run the SEARCH skill first** to find relevant skills and memory files. Don't assume which skill handles a domain — the SEARCH index covers all skills and memory with priority-weighted ranking.

Pattern: `create_file` (write search_args.json with query) → `run_task("search")` → `read_file` (read search_out.txt) → load the top-scoring skill.

## Host Resolution Routing

When resolving a hostname to its owner, application, or user, match the hostname pattern to the correct skill:

| Hostname Pattern | Skill | API | Returns |
|-----------------|-------|-----|---------|
| `dcnds*` (NDS desktops) | **NDS_INFRA** | `nds.py desktop DCNDS<num>` | `mappedUsers[]` with kerberos, name; also FQDN, OS, datacenter, hardware |
| `d<DID>-*` (Canvas deployments) | **CANVAS** | `query.py hierarchy <DID>` | `applicationName`, `familyName`, contacts, creator |

### NDS Desktops (`dcnds*`)

- Extract the NDS name: `dcnds0309862.dc.gs.com` → `DCNDS0309862` (uppercase, strip `.dc.gs.com`).
- Call NDS_INFRA desktop lookup: returns `mappedUsers[]` — each has `Username` (kerberos).
- Chain with **DIRGET** for full employee details (name, title, department) if needed.
- NDS desktops are personal workstations — `mappedUsers[0].Username` is the primary owner.

### Canvas Deployments (`d<DID>-*`)

- Extract the DID: `d241081-001-e12.dc.gs.com` → DID `241081`.
- Call CANVAS hierarchy: returns `applicationName`, `familyName`, `businessUnitName`.
- Call CANVAS deployed-application: returns `contacts[]`, `createdBy`, `systemAccounts[]`.
- Many grid/fleet nodes have no individual owner — `contacts` may be empty, `createdBy` often `dcadm`.

### Lesson Learned

Canvas was incorrectly used for `dcnds*` hostnames — it returned empty results because NDS desktops are not Canvas deployments. NDS_INFRA is the correct skill for NDS desktop lookups. Always use SEARCH to find the right skill first.
