---
name: CONFLUENCE
description: "REST client for GS internal Confluence — search, read, create, and update pages."
---

# CONFLUENCE — Confluence REST Client

> **Purpose:** Search, read, create, and update Confluence pages, comments, labels, and attachments on GS internal Confluence.

**Out of scope:** Confluence administration; space creation/deletion; plugin management; auth via Kerberos/SPNEGO (only PAT works).

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `CONFLUENCE` |
| **Scope** | Search, read, create, and update Confluence pages/comments/labels/attachments |
| **Inputs** | CQL queries, page IDs, space keys, page content (storage-format HTML) |
| **Tool** | `skills/CONFLUENCE/src/client.py` |
| **Outputs** | Page content, search results, create/update confirmations |
| **Auth** | **PAT only** — Personal Access Token via `CONFLUENCE_PAT` env var. Kerberos/SPNEGO/GSSSO do NOT work. |
| **Authority** | Read + write — creates/updates pages, uploads attachments |

---

## When to Use

- User asks to search, read, or update a Confluence page.
- Need to pull documentation from a Confluence space.
- Need to create or append to a page programmatically.
- CQL search for pages by space, label, text, or ancestor.

---

## Memory Loading Policy

| Task | Load |
|------|------|
| Any Confluence operation | **Nothing** — SKILL.md has full client API inline |
| Auth failing (401, PAT expired) | `memory/_dormant/ref/confluence-auth.md` (P2) |

> A separate API reference memory file is **not needed** — this SKILL.md has the full client API inline.

---

## Prerequisites

- `CONFLUENCE_PAT` set in `workspace/config/.env` — **gitignored, never committed; create it by copying `workspace/config/.env.template`** (generate the token at `https://confluence.work.gs.com/plugins/personalaccesstokens/usertokens.action`).
- `CONFLUENCE_URL` set to `https://confluence.work.gs.com/`.
- `python-dotenv` installed (`pip install python-dotenv`) — required for `from_env()` to load `.env` file. Without it, env vars must be exported manually.
- **Do NOT attempt GSSSO/SPNEGO fallback** — REST API rejects all Kerberos-based auth (returns 401).

---

## Pre-flight Checklist

Before any operation, verify:

- [ ] `CONFLUENCE_PAT` is set and not expired — if `client.is_connected()` returns `False`, tell the user to regenerate the PAT.
- [ ] `CONFLUENCE_URL` is set to `https://confluence.work.gs.com/`.
- [ ] Target space key is uppercase (`SLT`, not `slt`).
- [ ] CQL query is syntactically valid (test with `search()` before `search_all()`).

---

## Quick Start

```python
import sys
from pathlib import Path

# Add skill src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "CONFLUENCE" / "src"))
from client import ConfluenceClient

client = ConfluenceClient.from_env()

assert client.is_connected()
results = client.search('type=page AND space=SLT AND text~"runbook"')
page = client.get_page_by_id("12345678")
client.create_page("SLT", "My Page Title", "<p>Body HTML</p>", parent_id="12345678")
```

---

## Key Methods

| Method | Verb | Use case |
|--------|------|----------|
| `get_page_by_id(id)` | GET | Fetch page by numeric ID |
| `get_page_by_title(space, title)` | GET | Fetch page by space + exact title |
| `search(cql)` | GET | CQL search (single page of results) |
| `search_all(cql)` | GET | CQL search with auto-pagination |
| `get_child_pages(id)` | GET | Immediate children of a page |
| `get_page_tree(id, depth)` | GET | Recursive page tree |
| `get_space_info(key)` | GET | Space metadata |
| `get_page_labels(id)` | GET | Labels on a page |
| `get_page_comments(id)` | GET | Comments on a page |
| `list_attachments(id)` | GET | Attachment list |
| `download_attachment(url, path)` | GET | Download an attachment file |
| `create_page(space, title, body)` | POST | New page |
| `update_page(id, title, body)` | PUT | Update existing (auto-fetches version) |
| `append_to_page(id, content)` | PUT | Append HTML to existing body |
| `add_comment(id, body)` | POST | Add comment |
| `add_labels(id, labels)` | POST | Add labels |
| `remove_label(id, name)` | DELETE | Remove label |
| `upload_attachment(id, path)` | POST | Upload file as attachment |

---

## Response Schemas

Return dicts for key methods (content-first; metadata in `_meta`):

| Method | Returns |
|--------|---------|
| `search(cql)` | `{"success": bool, "count": int, "pages": [hit, ...]}` |
| `search_all(cql)` | `[hit, ...]` (flat list, auto-paginated) |
| `get_page_by_id(id)` | `{"title", "id", "url", "body", "ancestors", "_meta": {...}}` |
| `get_page_by_title(space, title)` | Same as `get_page_by_id` |
| `create_page(...)` | `{"success": bool, "page_id", "new_version", "url"}` |
| `update_page(...)` | `{"success": bool, "page_id", "new_version", "url"}` |

**Search hit shape:** `{"id", "title", "url", "_meta": {"space", "version", "last_updated"}}`

**Page shape:** `{"title", "id", "url", "body" (HTML), "ancestors" [...], "_meta": {"space", "version", "last_updated", "author"}}`

---

## CQL Cheat Sheet

```
type=page AND space=SLT
type=page AND space=SLT AND text~"migration"
type=page AND title~"runbook"
type=page AND label="architecture"
type=page AND lastModified >= "2026-01-01"
type=page AND ancestor=12345678
```

---

## Content-First Policy

Pages are **mutable** — they change over time. The client captures the page version in `_meta` so we know *which snapshot* we analysed.

- **Default output**: `body`, `title`, `id`, `url`, `ancestors`. This is what the user cares about.
- **Metadata** (version number, author, last-updated, space key) lives in `_meta`. **Only surface when user explicitly asks** (e.g. "who wrote this?", "when was it updated?").
- When saving to `tmp/`, always include `_meta` for traceability. When *presenting* to the user, lead with the body.

---

## Post-operation Checklist

- [ ] Confirm `success: True` in response dict.
- [ ] For `create_page` / `update_page`: verify returned `page_id` and `new_version`.
- [ ] For `search_all`: check total count is plausible (not 0 when results expected).
- [ ] For `append_to_page`: verify appended content didn't corrupt existing body.
- [ ] Save large results to `workspace/tmp/`.

---

## Anti-patterns

| Pattern | Why it's wrong | Correct approach |
|---------|---------------|-----------------|
| Hardcoding `page_id` in scripts | IDs change across environments | Use `get_page_by_title(space, title)` to resolve dynamically |
| Using `search()` when expecting many results | Silently truncates at `max_results` (default 25) | Use `search_all()` for exhaustive results |
| Passing raw Markdown as page body | Confluence expects storage-format HTML | Convert to `<p>`, `<table>`, `<ac:structured-macro>` etc. |
| Calling `update_page` without reading first | Risk overwriting concurrent edits | Let `update_page` auto-fetch version (default) |
| Space key in lowercase (`slt`) | 404 — Confluence expects uppercase | Always uppercase: `SLT` |
| CQL with wrong field casing (`Title~"foo"`) | Silent 0 results — CQL fields are case-sensitive | Use lowercase field names: `title~"foo"` |
| Trying GSSSO/Kerberos as PAT fallback | REST API returns `WWW-Authenticate: OAuth` — no Negotiate support | Only PAT works |
| Catching generic `Exception` around API calls | Hides auth errors, timeouts, 404s | Catch `requests.HTTPError` specifically |
| Building CQL with string concatenation | Injection risk, encoding bugs | Use parameterised values with proper escaping |
| Writing throwaway scripts to `tmp/` for API calls | Leaves orphan files; clutters workspace | Invoke the client inline (`python -c`) or import directly in a notebook / REPL |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 with `WWW-Authenticate: OAuth` | PAT missing or expired — regenerate |
| 404 on page or space | Check space key is uppercase; verify page ID exists |
| 429 rate limit | Add `batch_size` limit; monitor `count` growth |
| SSL error on GS endpoints | TLS verification is ON by default. On certificate errors, point the client at the GS CA bundle (set `CONFLUENCE_CA_BUNDLE` to `C:\ProgramData\certificates\cacerts.cer`) — never disable verification. |
| Page titles must be unique per space | Check before creating |
| Body must be valid storage-format HTML | Not Markdown |

---

## Links

- memory/_dormant/ref/confluence-auth.md — PAT generation, .env setup, verification, and auth anti-patterns
