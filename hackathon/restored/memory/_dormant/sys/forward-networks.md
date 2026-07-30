---
created: 2026-04-16
updated: 2026-04-16
tags: [systems, forward-networks, network-verification, firewall, api]
status: dormant
confidence: high
---

# Forward Networks

Network verification / digital-twin platform used at GS to model, trace, and audit network paths, firewall rules, and device configurations.

## Instances

| Instance | Base URL | Access | Use Case |
|---|---|---|---|
| **ETP** | `https://fwd.app/` | Zscaler proxy, multiple BU networks | ETP/GSET/FICC/EMM/LATAMSMM trading infra |
| **Neteng** | `https://prod.ui.fwdnetcluster.url.gs.com/` | Direct internal, single default network | Firm-wide network devices |

Auth: HTTP Basic via token file (`~/.forward_network_{instance}_token`). Two lines: access key, secret key.

## API v25.3.6 Endpoint Issues (April 2026)

### Network-level device endpoints BROKEN for FQDNs

The new network-level device endpoints (`/networks/{netId}/devices/{deviceName}/...`) are **broken** in v25.3.6 when `{deviceName}` contains dots (FQDNs like `host.net.gs.com`). The URL router returns "No endpoint" (404). This affects ALL Neteng devices since they all use FQDNs.

- `GET /networks/{netId}/devices/{name}` — 404
- `GET /networks/{netId}/devices/{name}/files` — 404
- `GET /networks/{netId}/devices/{name}/files/{fileName}` — 404
- URL-encoding dots (`%2E`) does not help.

**Working alternatives:**
- Path search: `GET /networks/{netId}/paths?srcIp=X&dstIp=Y` — works (IPs are query params, no dots in path)
- Device list: `GET /networks/{netId}/devices` — works (no device name in path)
- **Device file download: `GET /snapshots/{snapId}/files/{deviceName},configuration,16.txt?download=1`** — still works despite being "removed" from the spec

### Workaround for device file download

1. Fetch snapshot ID: `GET /networks/{netId}/snapshots/latestProcessed` → `{"id": 27573, ...}`
2. Download config: `GET /snapshots/{snapId}/files/{deviceName},configuration,16.txt?download=1`

**Affected script:** `AHN: Firewall Review` in `~nunesa` — fixed 2026-04-16.

## Key Endpoints

- Path search: `GET /api/networks/{networkId}/paths?srcIp=...&dstIp=...`
- Device config: `GET /api/snapshots/{snapshotId}/files/{deviceName},configuration,16.txt?download=1` *(old endpoint, still works)*
- Device list: `GET /api/networks/{networkId}/devices`
- NQE query: `POST /api/nqe?networkId={networkId}`
- Networks: `GET /api/networks`
- Snapshots: `GET /api/networks/{networkId}/snapshots/latestProcessed`

## Skill Reference

Full usage patterns, code examples, and OpenAPI spec: `skills/FORWARD_NETWORK/SKILL.md`.
