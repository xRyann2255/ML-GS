---
created: 2026-04-22
updated: 2026-04-22
tags: [ref]
status: active
---

# Web Server Authentication (Python BaseHTTPRequestHandler)

Reference for adding authentication to a Python HTTP server on GSINet.
Based on the implementation in `workspace/create_eod_dashboard.py`.

---

## Architecture Overview

Three-tier auth cascade (checked in order):

1. **Session cookie** — `eod_session` cookie maps to a server-side dict
2. **Localhost auto-auth** — requests from `127.0.0.1` / `::1` / `::ffff:127.0.0.1` auto-authenticate as the server owner
3. **GSId/GSSSO cookie** — GSINet browsers send `GSId` (v02) or `GSSSO` (v04) cookies to any `.gs.com` domain; parse to extract kerberos username
4. **OIDC redirect** (optional) — redirect to PingFederate for login if `OIDC_CLIENT_ID` env var is set
5. **SSO popup login** — open `https://authn.web.gs.com/desktopsso/Login` in a popup window; SSO does SPNEGO + sets `GSSSO` cookie on `.gs.com`; popup auto-closes after 1.5s and page redirects back to dashboard

---

## Required Imports

```python
import base64
import json
import secrets
import socket
import socketserver
from html import escape
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
```

---

## Global State

```python
_auth_sessions: dict[str, str] = {}        # token -> username
_oidc_states: dict[str, str] = {}           # state -> original_path
_server_owner: str = os.environ.get("USERNAME", os.environ.get("USER", "")).lower()
_LOCALHOST_ADDRS = frozenset(("127.0.0.1", "::1", "::ffff:127.0.0.1"))
```

---

## Session Token Generation

```python
def _generate_session_token() -> str:
    return secrets.token_urlsafe(32)
```

---

## GSId Cookie Parsing

GSINet browsers send cookies named **`GSId`** (current) and **`GSIdGUID`** to `.gs.com` domains.
Legacy cookie name is **`GSSSO`**.

### Cookie binary format

The cookie value = **2-char version prefix** + **base64-encoded binary payload**.

Two known versions:

| Version | Cookie name | Header size | TLV format |
|---------|------------|-------------|------------|
| `02`    | GSId       | 11 bytes    | `\x00\x00\x00` + 2 metadata bytes + length(1) + value |
| `04`    | GSSSO      | 20 bytes    | tag(1) + `\x00\x00\x00` + length(1) + value + `\x00` |

### Fields in order (both versions)

| Field | Tag (v04 only) | Content |
|-------|---------------|---------|
| 1     | `0x01`        | Kerberos username (ASCII, e.g. `nunesa`) |
| 2     | `0x02`        | Client IP address (ASCII, e.g. `10.11.150.23`) |
| 3     | `0x05`        | Timestamp? (4 bytes) |
| 4     | `0x06`        | Timestamp? (4 bytes) |
| 5     | `0x0b`        | GUID (32-char hex string) |
| 6     | `0x10`        | Signature (128 bytes) |

### Extraction function

IMPORTANT: The raw username field may contain a kerberos realm (e.g. `nunesa@GS.COM`) or
domain prefix (`GS\nunesa`). The parser MUST validate the extracted bytes are a valid
principal (alphanumeric + `._-@\/`) and strip the realm/domain to return just the
short username in lowercase. Without validation, binary garbage can pass `.decode('ascii')`
and be stored as the username.

```python
def _extract_gsid_username(cookie_value: str) -> str | None:
    if not cookie_value or len(cookie_value) < 10:
        return None
    try:
        payload = base64.b64decode(cookie_value[2:])
    except Exception:
        return None

    def _valid_username(raw: bytes) -> str | None:
        try:
            name = raw.decode('ascii')
        except Exception:
            return None
        if not name or not all(c.isalnum() or c in "._-@\\/" for c in name):
            return None
        if '@' in name:
            name = name.split('@')[0]
        if '\\' in name:
            name = name.split('\\')[-1]
        return name.lower() if name else None

    # Strategy 1: v04 — look for tag 0x01 marker
    marker = b'\x01\x00\x00\x00'
    idx = payload.find(marker)
    if idx >= 15:
        length_pos = idx + 4
        if length_pos < len(payload):
            length = payload[length_pos]
            vs = length_pos + 1
            if 0 < length <= 64 and vs + length <= len(payload):
                result = _valid_username(payload[vs:vs + length])
                if result:
                    return result

    # Strategy 2: v02 — first \x00\x00\x00 after offset 5, skip 2, read field
    sep = b'\x00\x00\x00'
    idx = payload.find(sep, 5)
    if idx >= 0:
        field_start = idx + 3 + 2
        if field_start < len(payload):
            length = payload[field_start]
            vs = field_start + 1
            if 0 < length <= 64 and vs + length <= len(payload):
                result = _valid_username(payload[vs:vs + length])
                if result:
                    return result
    return None
```

---

## Handler Auth Methods

### `_get_session_user` — check for existing session

```python
def _get_session_user(self) -> str | None:
    cookie_header = self.headers.get("Cookie", "")
    sc = SimpleCookie()
    try:
        sc.load(cookie_header)
    except Exception:
        return None
    morsel = sc.get("eod_session")
    if morsel:
        return _auth_sessions.get(morsel.value)
    return None
```

### `_require_auth` — main auth gate

Returns username string if authenticated, `None` if response was already sent (redirect/401).

Sets `self._pending_set_cookie` when creating a new session — caller must call `_flush_set_cookie()` before `end_headers()`.

```python
def _require_auth(self) -> str | None:
    user = self._get_session_user()
    if user:
        return user

    client_ip = self.client_address[0]

    # 1. Localhost auto-auth
    if client_ip in _LOCALHOST_ADDRS:
        token = _generate_session_token()
        _auth_sessions[token] = _server_owner
        self._pending_set_cookie = f"eod_session={token}; Path=/; HttpOnly; SameSite=Lax"
        return _server_owner

    # 2. GSId cookie
    cookie_header = self.headers.get("Cookie", "")
    sc = SimpleCookie()
    try:
        sc.load(cookie_header)
    except Exception:
        sc = SimpleCookie()
    gsid_morsel = sc.get("GSId") or sc.get("GSSSO")
    if gsid_morsel:
        gsid_user = _extract_gsid_username(gsid_morsel.value) or "remote"
        token = _generate_session_token()
        _auth_sessions[token] = gsid_user
        self._pending_set_cookie = f"eod_session={token}; Path=/; HttpOnly; SameSite=Lax"
        return gsid_user

    # 3. OIDC redirect (optional)
    if _OIDC_CLIENT_ID:
        # ... redirect to PingFederate ...
        return None

    # 4. 401
    self.send_response(401)
    # ...
    return None
```

### `_flush_set_cookie` — deferred header injection

Because `_require_auth` runs before `send_response`, we can't emit `Set-Cookie` there. Instead, store it and flush it after `send_response()`:

```python
def _flush_set_cookie(self):
    cookie = getattr(self, "_pending_set_cookie", None)
    if cookie:
        self.send_header("Set-Cookie", cookie)
        self._pending_set_cookie = None
```

**Usage pattern in `do_GET`:**

```python
def do_GET(self):
    user = self._require_auth()
    if user is None:
        return  # redirect or 401 already sent

    is_owner = (user == _server_owner)
    # ... build response ...
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self._flush_set_cookie()   # <-- MUST call before end_headers
    self.end_headers()
    self.wfile.write(html.encode("utf-8"))
```

---

## OIDC (PingFederate) — Optional Fallback

Only activates when `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` environment variables are set.

### Endpoints (GSINet PingFederate)

- Issuer: `https://id.web.gs.com`
- Authorization: `https://id.web.gs.com/as/authorization.oauth2`
- Token: `https://id.web.gs.com/as/token.oauth2`
- Discovery: `https://id.web.gs.com/.well-known/openid-configuration`

### Flow

1. Generate random `state`, save `_oidc_states[state] = original_path`
2. Redirect user to authorization endpoint with `client_id`, `response_type=code`, `scope=openid gssso`, `redirect_uri`, `state`, `nonce`
3. User authenticates at PingFederate
4. PingFederate redirects to `/oidc/callback?code=...&state=...`
5. Exchange code for tokens at token endpoint (POST, form-encoded)
6. Decode JWT access_token payload (base64url, no verification needed over TLS)
7. Extract `username` (or `sub`) claim
8. Create session, redirect to original path

### OIDC callback handler

Route `/oidc/callback` MUST be handled **before** the `_require_auth()` check (otherwise it would redirect to login in a loop).

---

## Dual-Stack Server (IPv4 + IPv6)

To make the server accessible via both `localhost` (IPv4) and FQDN (which may resolve to IPv6):

```python
class _DualStackServer(socketserver.ThreadingTCPServer):
    address_family = socket.AF_INET6
    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()

def _create_dual_stack_server(port, handler_class):
    try:
        return _DualStackServer(("::", port), handler_class)
    except OSError:
        import http.server
        return http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_class)
```

Key: `IPV6_V6ONLY = 0` makes the IPv6 socket also accept IPv4 connections, so a single socket handles both.

---

## Lessons Learned / Gotchas

- **GSSSO is NOT SPNEGO/Negotiate.** It's a proprietary opaque cookie. Don't try `sspi.ServerAuth('Negotiate')` — it's the wrong protocol.
- **Cookie name is `GSId`**, not `GSSSO` (legacy). Always check `GSId` first, fallback to `GSSSO`.
- **Cookie binary has a 2-char prefix** before the base64 payload. Must `b64decode(cookie[2:])`, not the whole string.
- **`_pending_set_cookie` pattern**: `BaseHTTPRequestHandler.send_response()` must be called before `send_header()`. Since `_require_auth()` runs before we know the response code, we store the cookie and flush it later.
- **Localhost detection must include `::ffff:127.0.0.1`** — on dual-stack servers, IPv4 localhost appears as IPv4-mapped IPv6.
- **`ThreadingTCPServer`** is required (not plain `TCPServer`) because SSE streaming blocks the handler thread.
- **OIDC requires client registration** — needs `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` from PingFederate admin. Without it, GSId cookie is the primary remote auth mechanism.
- **Authorization levels**: use `is_owner = (user == _server_owner)` to gate write operations (refresh, etc.) while allowing read-only access for authenticated remote users.
- **GSId username field may contain realm** (e.g. `nunesa@GS.COM`) — must validate + strip realm, not just `.decode('ascii')`. Binary data can pass ascii decode but is not a valid username.

---

## Audit Log

Generic event logging covering logins and refreshes. Persisted to `workspace/tmp/audit-log.json`.

### Event schema

```json
{"user": "nunesa", "time": "2026-04-10 11:24:59", "ip": "::1", "action": "Login", "detail": "localhost"}
```

- **action**: `Login` or `Refresh`
- **detail**: auth method for logins (`localhost`, `GSId`, `OIDC`) or refresh type (`Everything`, `Emails only`, `Procmon only`)

### Recording function

```python
def _record_event(user: str, ip: str, action: str, detail: str = ""):
    _audit_log.append({"user": user, "time": ..., "ip": ip, "action": action, "detail": detail})
    _save_audit_log()
```

### Refresh types

Three refresh modes via `/api/refresh?type=all|emails|procmon`:
- **all** (Everything): extract emails + procmon (full refresh)
- **emails** (Emails only): extract emails, keep existing procmon from today's snapshot
- **procmon** (Procmon only): fetch procmon, keep existing email data from today's snapshot

UI: dropdown button with 3 options (Everything / Emails only / Procmon only).
For partial refreshes, the handler loads today's existing snapshot and merges unchanged sections.

---

## SSO Popup Login Flow (no OIDC registration needed)

When no GSId/GSSSO cookie is present and OIDC is not configured, serve an HTML page that:

1. Opens `https://authn.web.gs.com/desktopsso/Login` in a **popup window** (`window.open`)
2. The SSO endpoint does SPNEGO negotiation (transparent with Kerberos ticket) and sets `GSSSO` cookie on `.gs.com`
3. After **1.5 seconds**, the popup auto-closes and the main page redirects to the dashboard
4. On the next request, the browser sends the `GSSSO` cookie → server extracts username → dashboard loads

**Why popup, not iframe:** Modern browsers block third-party cookies set in iframes (cross-origin). A popup is a top-level browsing context, so cookies are stored normally.

**Why not direct redirect:** The SSO endpoint returns HTTP 200 with a "Login Successful" HTML page — it does NOT redirect back. There's no `target` parameter support.

**Fallback:** If popup is blocked, show manual links: "click here to log in" + "reload the dashboard".

```python
# In _require_auth(), after OIDC check:
sso_url = "https://authn.web.gs.com/desktopsso/Login"
# Serve HTML page with:
#   window.open(SSO, 'gs_sso', 'width=480,height=360,...')
#   setTimeout → popup.close() + window.location.replace(return_url) after 1.5s
#   setInterval → detect if user closed popup manually → redirect
```
