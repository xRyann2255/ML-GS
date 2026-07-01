---
created: 2026-03-04
updated: 2026-03-04
tags: [setup, auth, gssso, kerberos, cookies, gs-internal]
status: active
---

# GSSSO Authentication

GSSSO is the standard GS cookie-based authentication mechanism. Many internal APIs (Genesis/Nimbus, EngHub, etc.) require a `GSSSO` cookie rather than raw Kerberos/SPNEGO.

## How It Works

1. Get a Kerberos ticket (`kinit`)
2. Hit the desktop SSO endpoint with SPNEGO negotiate — it returns a `GSSSO` cookie
3. Pass that cookie to downstream APIs

## Getting the Cookie

### Prerequisite

A valid Kerberos ticket. Check with `klist -s`. If missing, the user must run `kinit`.

### Obtain GSSSO

```bash
# One-liner: get GSSSO cookie value
GSSSO=$(curl -s --negotiate -u : -L -c - "https://authn.web.gs.com/desktopsso/Login" 2>/dev/null | grep GSSSO | awk '{print $NF}')
```

### Use with an API

```bash
curl -s -b "GSSSO=${GSSSO}" "https://some-api.gs.com/endpoint"
```

### Full pattern (check ticket → get cookie → call API)

```bash
# 1. Check for Kerberos ticket
if ! klist -s 2>/dev/null; then
    echo "No Kerberos ticket. Run 'kinit' first." >&2
    exit 1
fi

# 2. Get GSSSO cookie
GSSSO=$(curl -s --negotiate -u : -L -c - \
    "https://authn.web.gs.com/desktopsso/Login" 2>/dev/null \
    | grep GSSSO | awk '{print $NF}')

if [ -z "${GSSSO}" ]; then
    echo "Failed to obtain GSSSO cookie." >&2
    exit 1
fi

# 3. Call API
curl -s -b "GSSSO=${GSSSO}" "https://your-api.gs.com/path"
```

## Details

| Field | Value |
| --- | --- |
| SSO endpoint | `https://authn.web.gs.com/desktopsso/Login` |
| Auth method | SPNEGO (Kerberos negotiate) to get the cookie |
| Cookie name | `GSSSO` |
| Cookie domain | `.gs.com` |
| Lifetime | Tied to the Kerberos ticket (~24h by default) |

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Empty GSSSO value | Kerberos ticket expired or missing — run `kinit` |
| `401 Unauthorized` on SSO endpoint | Kerberos ticket invalid — run `kdestroy && kinit` |
| API still returns 401 with GSSSO | Cookie may have expired — re-obtain it |

## Confluence REST API (PAT Authentication)

Confluence does **NOT** accept GSSSO. It uses SAML/PingFederate for web and OAuth realm for REST API.

### Personal Access Token (PAT)

Use a PAT token with `Authorization: Bearer` header:

```powershell
$pat = "MTQ2NDczMzE3MTA2Oq++ir1u9jpyXDLZJgwMMsWAZNoV"
$headers = @{ "Authorization" = "Bearer $pat"; "Accept" = "application/json" }
$url = "https://confluence.work.gs.com/rest/api/content/{pageId}?expand=body.storage,children.page"
$r = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing
$page = $r.Content | ConvertFrom-Json
$html = $page.body.storage.value  # HTML content
$children = $page.children.page.results  # child pages (id, title)
```

### Useful Confluence REST Endpoints

| Endpoint | Purpose |
|---|---|
| `/rest/api/content/{id}?expand=body.storage` | Page content as HTML |
| `/rest/api/content/{id}?expand=children.page` | Child pages |
| `/rest/api/content/{id}?expand=body.storage,children.page` | Both at once |
| `/rest/api/content/search?cql=...` | CQL search |
