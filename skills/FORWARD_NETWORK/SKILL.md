---
name: FORWARD_NETWORK
description: |
  Query the Forward Networks API — run NQE queries, trace path searches, list
  networks/snapshots/devices, manage checks, device tags, topology, vulnerability
  analysis, or any other Forward Networks operation. Covers the ETP and Neteng
  Forward Network instances, authentication via API token files, and the full
  OpenAPI spec.
---

# FORWARD_NETWORK — Forward Networks API

> **Purpose:** Query the Forward Networks REST API from a Windows NDS workstation.
> Run NQE queries, trace path searches, list networks/snapshots/devices, manage checks,
> device tags, topology, vulnerability analysis, and more.

**Out of scope:** Modifying network configs, credential provisioning.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `FORWARD_NETWORK` |
| **Scope** | Forward Networks API queries (ETP + Neteng instances) |
| **Inputs** | Instance name, API path, optional JSON body |
| **Outputs** | JSON responses in `workspace/tmp/` |
| **Authority** | Read-only API queries (Basic Auth via token file) |

## When to Use

- Run NQE queries to inspect device configs, routes, ACLs.
- Trace packet paths between source and destination IPs/ports.
- List networks, snapshots, devices.
- Check network health, vulnerabilities, topology.
- Look up firewall rules, routing tables, interface status.

---

## Instances

| Instance | Base URL | Token file | Connectivity |
|----------|----------|------------|--------------|
| **ETP** | `https://fwd.app/` | `%USERPROFILE%\.forward_network_etp_token` | Via Zscaler proxy (PAC auto-detected) |
| **Neteng** | `https://prod.ui.fwdnetcluster.url.gs.com/` | `%USERPROFILE%\.forward_network_neteng_token` | Direct (internal GS network, no proxy) |

When the user does not specify which instance, **ask** before making calls.

---

## Network Selection

### ETP instance

The ETP instance has **multiple networks organised by business unit** (ETP, GSET,
FICC, EMM, LATAMSMM, SIGMAX, QMM). If the user does **not** specify which network:

1. Call `GET /api/networks` to list all available networks.
2. Present the list to the user (name + id).
3. **Ask the user to choose** before running any query.

Known ETP and Neteng network IDs are in memory/ref/forward-network.md. Use as a shortcut when the user clearly names the BU. If the result looks unexpected, fall back to `GET /api/networks` and re-confirm.

### Neteng instance

The Neteng instance has multiple networks. The main one is **AllRegions** (id `104`)
which is the parent network containing all devices. Default to **AllRegions** (`104`)
unless the user specifies a sub-network. See memory/ref/forward-network.md for full ID table.

---

## Snapshot Selection

Default to the **latest processed snapshot**. Most endpoints accept an optional
`snapshotId` parameter — omit it to use the latest.

- Latest processed: `GET /api/networks/{networkId}/snapshots/latestProcessed`
- List all: `GET /api/networks/{networkId}/snapshots`

---

## Prerequisites

### API Token

Two-line file: access key (line 1), secret key (line 2).

| Instance | Token file path |
|----------|-----------------|
| ETP | `%USERPROFILE%\.forward_network_etp_token` |
| Neteng | `%USERPROFILE%\.forward_network_neteng_token` |

If missing, instruct user to create at `https://fwd.app/?/settings/account?` and save via `Set-Content`.

### Connectivity

- **ETP** (`fwd.app`): internet-facing, needs Zscaler proxy `http://production.zscaler.nimbus.gs.com:443`
- **Neteng** (`prod.ui.fwdnetcluster.url.gs.com`): internal GS DNS, direct access — no proxy needed

The Python helper handles connectivity automatically.

---

## Authentication

HTTP Basic Auth (access key = username, secret key = password). Token read pattern in memory/ref/forward-network.md.

---

## Reusable Python Helper

CLI at `skills/FORWARD_NETWORK/src/fwd_api.py`:

```powershell
# Windows:
cmd /c "H:\uv-env.cmd && uv run python skills/FORWARD_NETWORK/src/fwd_api.py etp GET /networks"
cmd /c "H:\uv-env.cmd && uv run python skills/FORWARD_NETWORK/src/fwd_api.py etp POST /nqe '{\"query\":\"foreach d in network.devices select {Name: d.name}\"}'"

# Linux:
uv run python skills/FORWARD_NETWORK/src/fwd_api.py etp GET /networks
uv run python skills/FORWARD_NETWORK/src/fwd_api.py etp POST /nqe '{"query":"foreach d in network.devices select {Name: d.name}"}'
```

Also importable: `from fwd_api import fwd_api; fwd_api('GET', '/networks', instance='etp')`

---

## Common Operations Quick Reference

Consult `skills/FORWARD_NETWORK/src/forward_network_api.yaml` for complete schemas. All paths relative to `/api`.

| Operation | Method | Path |
|-----------|--------|------|
| List networks | GET | `/networks` |
| List snapshots | GET | `/networks/{networkId}/snapshots` |
| Latest snapshot | GET | `/networks/{networkId}/snapshots/latestProcessed` |
| List devices | GET | `/networks/{networkId}/devices` |
| Get device | GET | `/networks/{networkId}/devices/{deviceName}` |
| Device config file | GET | `/networks/{networkId}/devices/{deviceName}/files/{fileName}` |
| Path search | GET | `/networks/{networkId}/paths?srcIp=...&dstIp=...&dstPort=...&ipProto=6` |
| Run NQE query | POST | `/nqe?networkId={networkId}` (body: `{query}` or `{queryId}`) |
| List NQE queries | GET | `/nqe/queries` |
| Compare snapshots | POST | `/nqe-diffs/{beforeSnapshotId}/{afterSnapshotId}` |
| Get checks | GET | `/snapshots/{snapshotId}/checks` |
| Vulnerabilities | GET | `/networks/{networkId}/vulnerabilities` |
| Topology | GET | `/snapshots/{snapshotId}/topology` |
| Device tags | GET | `/networks/{networkId}/device-tags` |
| API version | GET | `/version` |

For path search parameters, NQE schema details, and undocumented endpoints, see memory/ref/forward-network.md.

---

## Error Handling

> See memory/ref/forward-network.md for HTTP status codes and meanings.

---

## Full API Specification

The complete OpenAPI 3.1 spec is at:

```
skills/FORWARD_NETWORK/src/forward_network_api.yaml
```

Reference it for all available endpoints, request/response schemas, filter objects
(DeviceFilter, PacketFilter, InterfaceFilter), synthetic device management,
credential management, and system administration endpoints.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | GSSSO cookie expired or missing | Re-run GSSSO_AUTH skill to refresh cookie |

## Task-Based Execution

**Task label:** `forward-network` | **Args file:** `workspace/tmp/forward_network_args.json`

Preferred. Write args JSON, then `run_task("forward-network")`. CLI args pass through via `%*`.

## Links

- memory/ref/forward-network.md — Forward Networks API reference
