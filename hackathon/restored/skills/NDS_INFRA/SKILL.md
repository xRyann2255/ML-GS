---
name: NDS_INFRA
description: Query NDS Infrastructure Services for user desktop assignments, desktop details (OS, hardware, hypervisor, datacenter, IP, memory, disk). Use when looking up NDS desktops, machine specs, or user-to-desktop mappings.
---

# NDS_INFRA — Network Desktop Services Lookup

> **Purpose:** Query the NDS Infrastructure Services web UI to retrieve desktop assignments for a user and detailed machine information for a specific NDS desktop.

**Out of scope:** Modifying NDS mappings, provisioning desktops, dialtone checks, or placement rules.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `NDS_INFRA` |
| **Scope** | Read-only NDS desktop lookups |
| **Inputs** | Kerberos ID (user lookup) or NDS name like `DCNDS0000000` (desktop lookup) |
| **Outputs** | Console summary + JSON in `workspace/tmp/` |
| **Authority** | Read-only (Windows integrated auth) |

## When to Use

- Look up which **NDS desktops** are assigned to a user.
- Find **machine specs** for a desktop: OS, CPU count, RAM, disk, hypervisor, hardware model, IP address.
- Determine the **datacenter location** and build date of a desktop.
- Find the **FQDN** (fully-qualified domain name) for an NDS name.
- Check which **users are mapped** to a specific desktop.
- Find recent **NDC clients** (thin client hostnames) used by a user.

Do **not** use for:
- Modifying desktop assignments → use the NDS web UI directly.
- Dialtone checks → use the NDS web UI or Iridium.
- Host-level monitoring → use Pulse.

## Connection

| Field | Value |
|-------|-------|
| **Base URL** | `http://iws.web.gs.com/NdsInfraServices/Home` |
| **Auth** | Windows integrated auth (GSSSO session) |
| **User lookup** | `/Users/Display/{kerberos}?domain=FIRMWIDE` |
| **Desktop lookup** | `/Desktops/Display/{nds}` |

## Usage

```bash
# Windows:
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py user jdoe"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py user jdoe jdoe1"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py desktop DCNDS0000000"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py desktop DCNDS0000000 DCNDS0000001"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py dialtone DCNDS0000000"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py dialtone DCNDS0000000 --last 5"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py user jdoe --json"
cmd /c "H:\uv-env.cmd && uv run python skills/NDS_INFRA/src/nds.py desktop DCNDS0000000 --json"

# Linux:
uv run python skills/NDS_INFRA/src/nds.py user jdoe
uv run python skills/NDS_INFRA/src/nds.py desktop DCNDS0000000
uv run python skills/NDS_INFRA/src/nds.py dialtone DCNDS0000000 --last 5
```

## Output Fields

### User Lookup

| Field | Example |
|-------|---------|
| `kerberos` | `jdoe` |
| `name` | `Doe, John [GBM Public]` |
| `title` | `Managing Director` |
| `location` | `Country/City/000/000/000A00` |
| `division` | `Global Banking & Markets` |
| `department` | `Example Strats (E000)` |
| `email` | `first.last@gs.com` |
| `desktops` | Array of NDS assignments (name, datacenter, pool, caliber) |
| `ndcClients` | Array of recent thin-client check-ins |

### Desktop Lookup

| Field | Example |
|-------|---------|
| `nds` | `DCNDS0000000` |
| `fqdn` | `dcnds0000000.dc.gs.com` |
| `osVersion` | `Win10 x64` |
| `processors` | `8` |
| `memory` | `65536 MB` |
| `disk` | `201897 MB (39%) free of 512000 MB total` |
| `hypervisor` | `ESX ESX80-250729 on esx-example.ny.fw.gs.com` |
| `hardware` | `Dell PowerEdge R6515 Epyc 7502 (Asset:SN0000000 Serial:SN0000000)` |
| `datacenterLocation` | `ExampleDC / 0000AA / GND / EX00A00 / A00A00-00` |
| `lastIP` | `10.0.0.1` |
| `buildDate` | `2025-01-28 02:40:20Z` |
| `lastCheckin` | `2026-04-16 08:04:32Z` |
| `mappedUsers` | Array of mapped users (username, name, disabled, expires) |

### Dialtone History

| Field | Example |
|-------|---------|
| `nds` | `DCNDS0000000` |
| `history` | Array of scan entries |
| `history[].scannedOn` | `2026-04-16 17:41:19Z` |
| `history[].healthCheck` | `Broker (HTTPS)`, `Desktop Agent`, `Ping` |
| `history[].status` | `Passed` or `Failed` |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty response | Invalid host/resource name | Check spelling and casing against NDS inventory |

## Task-Based Execution

**Task label:** `nds-infra` | **Args file:** `workspace/tmp/nds_infra_args.json`

Preferred. Write args JSON, then `run_task("nds-infra")`. CLI args pass through via `%*`.

## Links

- [NDS Infrastructure Services](http://iws.web.gs.com/NdsInfraServices/Home/) — Web UI
- memory/_dormant/ref/gssso-auth.md — GSSSO authentication details
