---
created: 2026-04-27
updated: 2026-04-27
tags: [systems, ecs, obs, s3, storage, bucket-policy, elasticsearch]
status: dormant
relates:
  - ref/python-pyslang.md
---

# ECS OBS V2 — Gotchas & Operational Knowledge

## Namespace Isolation

- Different ECS namespaces can have identically-named buckets (e.g., `test`).
- The ES access-log index (`ecs-access-logs-*`) contains entries from ALL namespaces.
- **Always filter by `namespace.keyword`** — never rely on bucket name alone for attribution.
- A `should` + `minimum_should_match: 1` on bucket OR namespace causes false positives when another namespace has a bucket with the same name.
- Our namespace: `ns-cdc7f9c6-6dff-4824-b304-18bd298566a8`.

## Bucket Policy Enforcement (What Works / What Doesn't)

| Condition Type | Works? | Notes |
|---|---|---|
| `StringEquals` + `aws:SourceIp` | **YES** | Proven. Use raw IPv4 string, not CIDR. |
| `IpAddress` + `aws:SourceIp` (CIDR) | NO | ECS does not enforce CIDR reliably. |
| `"Principal": "<username>"` | NO | Non-wildcard Principal not enforced on ECS. |
| `StringEquals` + `aws:username` | NO | Not enforced on ECS OBS. |

- **Working deny pattern:**
  ```json
  {
    "Sid": "DenyHost-<hostname_DOT_encoded>",
    "Effect": "Deny",
    "Principal": "*",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket",
               "s3:ListBucketMultipartUploads", "s3:AbortMultipartUpload", "s3:GetBucketLocation"],
    "Condition": {"StringEquals": {"aws:SourceIp": "<ipv4>"}}
  }
  ```
- Exclude `s3:PutBucketPolicy`, `s3:GetBucketPolicy`, `s3:DeleteBucketPolicy` from deny actions to prevent self-lockout.

## Self-Lockout Recovery

When a bucket policy denies `s3:*` (or policy-management ops) from your IP, you cannot fix it from that machine.

**Recovery procedure:**
1. Resolve OBS credentials locally (from secexpr or the running dashboard's `/api/credential-info`).
2. Connect to a remote host on a different IP via Kerberos/GSSAPI.
3. Transfer `remote_unblock.py` + pipe credentials via stdin.
4. Run the script from the remote host — `delete_bucket_policy` succeeds from the different IP.
5. Clean up credential files on the remote host immediately.

**Tool:** `skills/S3_DASHBOARD/src/remote_unblock.py` — standalone CLI for remote-side execution.

## ES Access Log Fields

Full field list in `ecs-access-logs-*`:

| Field | Description |
|---|---|
| `@timestamp` | Log entry time |
| `clientHost` | Hostname of the S3 client (resolved by ECS) |
| `namespace` | ECS namespace ID |
| `bucket` | Target bucket name |
| `method` | HTTP method (GET, PUT, DELETE, HEAD) |
| `status` | HTTP status code |
| `username` | OBS credential username |
| `object` | Object key |
| `bytesRead` / `bytesWritten` | Transfer sizes |
| `message` | Raw log line — contains source IP as `<src_ip>:<port>` |
| `nodeName` | ECS node that handled the request |
| `accessPort` | ECS access port (9020/9021) |
| `transactionId` | ECS transaction ID |

Note: source IP is embedded in `message` (not a first-class field). `clientHost` is the resolved hostname.
