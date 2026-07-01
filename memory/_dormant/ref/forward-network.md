---
created: 2026-04-22
updated: 2026-04-22
confidence: high
tags: [forward-networks, api, network, reference]
status: active
relates:
  - ref/gssso-auth.md
---

# Forward Networks API Reference

Static knowledge extracted from `skills/FORWARD_NETWORK/SKILL.md` — network IDs, API schemas, and error codes.

## Known Network IDs

### ETP Instance

Last verified 2026-04-08.

| Network | ID |
|---|---|
| ETP | `156163` |
| GSET | `164632` |
| FICC | `164651` |
| EMM | `164652` |
| LATAMSMM | `213532` |
| SIGMAX | `233682` |
| QMM | `233683` |

### Neteng Instance

Last verified 2026-04-16.

| Network | ID | Note |
|---|---|---|
| AllRegions | `104` | Parent network, all devices |
| Taiwan | `11099` | Taiwan DC |
| India Network | `11374` | India region |
| PSM | `8657` | |
| Cloud-OnRamp | `9825` | Cloud OnRamp inventory |
| EMM - ETP Handoff | `9824` | EMM nodes handed to ETP |
| QKF DHCP | `9311` | |

Default to **AllRegions** (`104`) unless the user specifies a sub-network.

## Path Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `srcIp` | string | — | Source IP or subnet. Required unless `from` is set |
| `dstIp` | string | — | **Required.** Destination IP or subnet |
| `from` | string | — | Source device name (if set, `srcIp` is header-only, not resolved to location) |
| `ipProto` | int | — | IP protocol number (see table below) |
| `srcPort` | string | — | L4 source port, e.g. `"80"` or range `"8080-8088"` |
| `dstPort` | string | — | L4 destination port, e.g. `"443"` or range |
| `icmpType` | int | — | ICMP type (implies `ipProto=1`) |
| `intent` | string | `PREFER_DELIVERED` | `PREFER_DELIVERED` \| `PREFER_VIOLATIONS` \| `VIOLATIONS_ONLY` |
| `includeNetworkFunctions` | bool | `false` | Include detailed forwarding info per hop (slower) |
| `includeTags` | bool | `false` | Include device tags per hop |
| `maxCandidates` | int | `5000` | Candidate results before ranking (1–10,000) |
| `maxResults` | int | `1` | Results returned after ranking (1–maxCandidates) |
| `maxReturnPathResults` | int | `0` | Return-path results (0–10,000) |
| `maxSeconds` | int | `30` | Timeout (1–300) |
| `syn`, `ack`, `fin`, `rst`, `psh`, `urg` | int | — | TCP flag bits (0 or 1, implies `ipProto=6`) |
| `appId` | string | — | L7 app-id for firewall policies |
| `userId` | string | — | L7 user-id for firewall policies |
| `url` | string | — | L7 URL target (prefix/suffix wildcards supported) |

### IP Protocol Numbers

| Protocol | `ipProto` |
|----------|-----------|
| ICMP | `1` |
| TCP | `6` |
| UDP | `17` |

## Path Response Structure

Response: `{ "info": { "paths": [...], "totalHits": { "value": N, "type": "EXACT" | "LOWER_BOUND" } } }`

Each path object:

| Field | Values / Type |
|-------|---------------|
| `forwardingOutcome` | `DELIVERED`, `DELIVERED_TO_INCORRECT_LOCATION`, `BLACKHOLE`, `DROPPED`, `INADMISSIBLE`, `UNREACHABLE`, `LOOP` |
| `securityOutcome` | `PERMITTED`, `DENIED` |
| `hops[]` | Array of hop objects |

Each hop object:

| Field | Description |
|-------|-------------|
| `deviceName` | Device hostname |
| `deviceType` | Device type (router, firewall, switch, etc.) |
| `ingressInterface` | Physical ingress interface |
| `egressInterface` | Physical egress interface (absent on last hop if traffic didn't exit) |
| `behaviors[]` | `L2`, `L3`, `NAT`, `PBR`, `ACL_PERMIT`, `ACL_DENY` |
| `parseError` | `true` if device behaviour model may be unreliable |

## NQE Routing Schema Reference

| Purpose | Field path |
|---|---|
| Device routing container | `d.networkInstances` |
| IPv4 route table | `ni.afts.ipv4Unicast.ipEntries` |
| Route prefix | `e.prefix` |
| Next hops | `e.nextHops` |
| Next-hop IP | `e.nextHops[].ipAddress` |
| Route source protocol | `e.nextHops[].originProtocol` |

Exact prefix lookup pattern:

```json
{
  "query": "foreach d in network.devices foreach ni in d.networkInstances where isPresent(ni.afts) && isPresent(ni.afts.ipv4Unicast) foreach e in ni.afts.ipv4Unicast.ipEntries where toString(e.prefix) == \"10.147.164.0/24\" select { device: d.name, vrf: ni.name, prefix: toString(e.prefix), nextHops: e.nextHops }",
  "queryOptions": { "offset": 0, "limit": 100 }
}
```

## NQE Pitfalls

- Put `limit` in `queryOptions`, not in the NQE query string.
- `e.prefix` is `IpSubnet`, not string. Use `toString(e.prefix)` for comparison.
- Guard with `isPresent(ni.afts) && isPresent(ni.afts.ipv4Unicast)` before iterating.
- `select d` can exceed output-size limits on real devices — select only needed fields.

## Undocumented Endpoints

### IP / Subnet Lookup

Find which device and interface owns an IP address:

```
GET /api/snapshots/{snapshotId}/subnets?address={ip}&minimal=false
```

Useful for identifying the network location of a host before running a path search. Not in the official OpenAPI spec but used by the NDK web backend.

### Interface Diff Between Snapshots

Compare interface state across two snapshot IDs:

```
GET /api/diffs/{snapshotId1}/{snapshotId2}/interfaces
```

Not in the official OpenAPI spec but used by the NDK tooling.

## Authentication & Token Setup

Token file: two lines — access key (line 1), secret key (line 2).

### Reading tokens (PowerShell)

```powershell
$lines = Get-Content "$env:USERPROFILE\.forward_network_etp_token"
$pair = "$($lines[0].Trim()):$($lines[1].Trim())"
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ "Authorization" = "Basic $b64"; "Content-Type" = "application/json" }
```

### Zscaler proxy (ETP)

ETP (`fwd.app`) needs Zscaler: `http://production.zscaler.nimbus.gs.com:443`

```powershell
Invoke-WebRequest -Uri "https://fwd.app/api/version" -Proxy "http://production.zscaler.nimbus.gs.com:443" -ProxyUseDefaultCredentials -UseBasicParsing -TimeoutSec 10
```

### Neteng direct (no proxy)

```powershell
Invoke-WebRequest -Uri "https://prod.ui.fwdnetcluster.url.gs.com/api/version" -UseBasicParsing -TimeoutSec 10
```

### Reusable PowerShell Pattern

```powershell
$proxy = "http://production.zscaler.nimbus.gs.com:443"
Invoke-RestMethod -Uri "https://fwd.app/api/networks" -Headers $headers -Proxy $proxy -ProxyUseDefaultCredentials
$body = @{ query = 'foreach d in network.devices select { Name: d.name }'; queryOptions = @{ offset = 0; limit = 100 } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "https://fwd.app/api/nqe?networkId=213532" -Headers $headers -Method POST -Body $body -ContentType "application/json" -Proxy $proxy -ProxyUseDefaultCredentials
```

### Importable Python Library

```python
import sys; sys.path.insert(0, 'skills/FORWARD_NETWORK/src')
from fwd_api import fwd_api
result = fwd_api('GET', '/networks/104/paths', instance='neteng', params={
    'srcIp': '10.1.1.1', 'dstIp': '10.2.2.2', 'ipProto': 6, 'dstPort': 443,
    'intent': 'PREFER_DELIVERED', 'maxResults': 1, 'maxSeconds': 30,
})
for path in result['info']['paths']:
    for hop in path['hops']:
        print(f"  {hop['deviceName']} {hop.get('ingressInterface','')} -> {hop.get('egressInterface','')}")
```

API base: all paths relative to `https://fwd.app/api/<path>`

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 200 / 201 / 204 | Success |
| 400 | Bad request — check query parameters or request body |
| 401 | Authentication failed — verify token file contents |
| 403 | Forbidden — token lacks permissions |
| 404 | Resource not found — verify networkId / snapshotId / deviceName |
| 409 | Snapshot still processing — retry or use `latestProcessed` |
