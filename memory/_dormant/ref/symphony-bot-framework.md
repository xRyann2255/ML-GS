---
created: 2026-04-14
updated: 2026-04-14
tags: [symphony, chat, bot-framework, api, gs-internal, messaging]
status: active
relates:
  - ref/gssso-auth.md
  - ref/devtools.md
---

# Symphony Bot Framework API Bridge

The GS Bot Framework API Bridge 2.0 translates GSSSO auth into Symphony credentials. No RSA keys, no bot service account, no corporate proxy needed.

## Endpoints

| Env | Base URL | Status |
|-----|----------|--------|
| **PROD** | `https://bot.framework.symphony.site.gs.com` | Working |
| **QA** | `https://bot.framework.symphony-qa.site.gs.com` | SKEY errors — use PROD |

Reference: [Confluence — Symphony Bot Framework (API Bridge 2.0)](https://confluence.work.gs.com/pages/viewpage.action?pageId=322341440)

## Authentication

```python
import os
CA_BUNDLE = r"C:\ProgramData\certificates\cacerts.cer"
if os.path.exists(CA_BUNDLE):
    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE
    os.environ["SSL_CERT_FILE"] = CA_BUNDLE

from gs_auth import get_token_from_desktopsso, get_req_session_from_token
sso_token = get_token_from_desktopsso(verify=False)
session = get_req_session_from_token(sso_token)
session.verify = CA_BUNDLE if os.path.exists(CA_BUNDLE) else False
```

- Import is `gs_auth`, **not** `goldmansachs.gs_auth`.
- Set CA bundle env vars **before** importing `gs_auth`.

## API Endpoints

| Operation | Method | Path | Notes |
|-----------|--------|------|-------|
| Search rooms | POST | `/pod/v3/room/search` | Body: `{"query": "room name"}` |
| Room info | GET | `/pod/v3/room/{streamId}/info` | |
| Stream info | GET | `/pod/v2/streams/{streamId}/info` | |
| Room members | GET | `/pod/v2/room/{streamId}/membership/list` | |
| List messages | GET | `/agent/v4/stream/{streamId}/message?since={epochMs}&limit=N` | See gotcha below |
| List bot streams | POST | `/pod/v1/streams/list` | Body: `{"streamTypes": [{"type": "ROOM"}]}` |
| Healthcheck | GET | `/healthcheck` | |

## Critical Gotcha: Message Fetching

The `/agent/v4/stream/{id}/message` endpoint returns messages **after** `since` in **chronological** order, capped by `limit`. Setting `since` to midnight with `limit=50` returns the **earliest** 50 messages, not the most recent.

**Always set `since` to ~15 minutes before current UTC time:**

```python
import time
now_ms = int(time.time() * 1000)
since_ms = now_ms - (15 * 60 * 1000)
```

## MessageML Parsing

Messages arrive as MessageML (XHTML-like). Strip to plain text:

```python
import re, html
text = re.sub(r"<[^>]+>", " ", messageml)
text = html.unescape(re.sub(r"\s+", " ", text).strip())
```

## Guardrails

- **Read-only by default.** Sending messages requires explicit human approval.
- AI-generated content must include `⚠️ AI-Generated`.
- Never log or display GSSSO tokens.

## Source

Learned from `https://gitlab.aws.site.gs.com/eq-tech/sts-engineering/sts-ai-agent` — `.github/skills/symphony/`.
