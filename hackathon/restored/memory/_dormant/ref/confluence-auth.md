---
created: 2026-04-13
updated: 2026-04-14
tags: [confluence, auth, pat, api, troubleshooting]
status: dormant
relates:
  - ref/gssso-auth.md
---

# Confluence Auth — PAT Setup & Troubleshooting

Authentication for the GS internal Confluence REST API. **Only PAT works** — Kerberos/SPNEGO/GSSSO are not supported by the REST API.

## PAT Generation

1. Navigate to: `https://confluence.work.gs.com/plugins/personalaccesstokens/usertokens.action`
2. Click **Create token**.
3. Name it something descriptive (e.g. `copilot-confluence`).
4. Set expiry (max 1 year). Track the expiry date — expired PATs fail silently with 401.
5. Copy the token immediately — it's shown only once.

## .env Setup

The `CONFLUENCE` skill client reads auth from `workspace/config/.env` (gitignored — never committed; created from `workspace/config/.env.template`):

```env
CONFLUENCE_PAT=<your-token-here>
CONFLUENCE_URL=https://confluence.work.gs.com/
```

**Critical:** The `.env` file must be UTF-8 **without BOM**. UTF-8 BOM prepends invisible bytes to `CONFLUENCE_PAT`, causing 401 errors that look like an expired token.

To write a BOM-free file from PowerShell:

```powershell
[System.IO.File]::WriteAllText("$pwd\workspace\config\.env", "CONFLUENCE_PAT=<token>`nCONFLUENCE_URL=https://confluence.work.gs.com/`n")
```

Do **not** use `Set-Content` or `Out-File` — both default to UTF-8 with BOM on PowerShell 5.1.

## Verification

Quick check that the PAT works:

```python
from client import ConfluenceClient
client = ConfluenceClient.from_env()
print(client.is_connected())  # True = PAT valid, False = expired or malformed
```

Or via PowerShell:

```powershell
$headers = @{ Authorization = "Bearer $(Get-Content workspace\config\.env | Select-String 'CONFLUENCE_PAT=' | ForEach-Object { $_ -replace 'CONFLUENCE_PAT=',''})" }
Invoke-RestMethod -Uri "https://confluence.work.gs.com/rest/api/content?limit=1" -Headers $headers -Method Get
```

If this returns JSON with `results`, auth is working. If it returns 401, the PAT is expired or BOM-corrupted.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 `WWW-Authenticate: OAuth` | PAT missing, expired, or BOM-corrupted | Regenerate PAT; rewrite `.env` without BOM |
| 401 after token worked yesterday | Token expired (check expiry date) | Regenerate at the PAT management URL |
| `client.is_connected()` returns `False` | `.env` not found or `CONFLUENCE_PAT` key missing | Verify `workspace/config/.env` exists (gitignored — never committed; created from `workspace/config/.env.template`) and contains `CONFLUENCE_PAT` |
| `python-dotenv` import error | Package not installed | `pip install python-dotenv` |
| SSL handshake error | GS internal CA not trusted by Python | Ensure `verify_ssl=False` is set (default in client) |
| `requests.ConnectionError` | Network / VPN issue | Verify connectivity to `confluence.work.gs.com` |

## Auth Anti-Patterns

| Anti-pattern | Why it fails | Correct approach |
|--------------|-------------|-----------------|
| Using GSSSO cookie for REST API | REST API returns `WWW-Authenticate: OAuth`, ignores Negotiate | Only PAT is accepted |
| Storing PAT in script source | Security risk; PAT in version control | Store in `.env` (gitignored) or `~/.confluence_pat` |
| Using `Set-Content` to write `.env` on PS 5.1 | Adds UTF-8 BOM → token corruption | Use `[System.IO.File]::WriteAllText()` |
| Hardcoding `Bearer <token>` in HTTP headers | Token rotates; leaks in logs | Load from env var at runtime via `from_env()` |
| Falling back to anonymous access | All Confluence pages require auth | Always set PAT before any API call |
| Caching PAT in memory across long sessions | PAT may expire mid-session | Re-read from `.env` on each client instantiation |
