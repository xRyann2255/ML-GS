"""Symphony chat reader via GS Bot Framework API Bridge 2.0.

Commands: search, info, messages
Output: workspace/tmp/symphony-<command>.json + stdout summary

READ-ONLY — no write operations.
"""

import argparse
import atexit
import html
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Encoding fix for Windows terminals ───────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── GS CA bundle (must be set before importing gs_auth / requests) ──────
CA_BUNDLE = r"C:\ProgramData\certificates\cacerts.cer"
if os.path.exists(CA_BUNDLE):
    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE
    os.environ["SSL_CERT_FILE"] = CA_BUNDLE

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from gs_auth import get_token_from_desktopsso, get_req_session_from_token

# ── Constants ────────────────────────────────────────────────────────────
BASE = "https://bot.framework.symphony.site.gs.com"
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_TMP = SCRIPT_DIR.parent.parent.parent / "workspace" / "tmp"


# ── Helpers ──────────────────────────────────────────────────────────────

def get_session():
    """Authenticate via GSSSO and return a requests session."""
    print("Authenticating via GS SSO...", file=sys.stderr)
    sso_token = get_token_from_desktopsso()
    session = get_req_session_from_token(sso_token)
    session.verify = CA_BUNDLE if os.path.exists(CA_BUNDLE) else False
    print("SSO session OK", file=sys.stderr)
    return session


def strip_messageml(messageml: str) -> str:
    """Strip MessageML tags and return plain text."""
    text = re.sub(r"<[^>]+>", " ", messageml)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def epoch_to_str(epoch_ms) -> str:
    """Convert epoch milliseconds to human-readable UTC string."""
    dt = datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def write_output(command: str, data):
    """Write JSON output to workspace/tmp/symphony-<command>.json."""
    WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    out_path = WORKSPACE_TMP / f"symphony-{command}.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nOutput written to: {out_path}", file=sys.stderr)


# ── Commands ─────────────────────────────────────────────────────────────

def cmd_search(session, args):
    """Search for Symphony rooms by name."""
    resp = session.post(
        f"{BASE}/pod/v3/room/search",
        json={"query": args.query},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    rooms = data.get("rooms", [])

    print(f"Found {len(rooms)} room(s) matching '{args.query}':\n")
    for room in rooms:
        attrs = room.get("roomAttributes", {})
        sys_info = room.get("roomSystemInfo", {})
        name = attrs.get("name", "?")
        stream_id = sys_info.get("id", "?")
        desc = attrs.get("description", "")[:120]
        print(f"  {name}")
        print(f"    Stream ID: {stream_id}")
        if desc:
            print(f"    Description: {desc}")
        print()

    write_output("search", data)


def cmd_info(session, args):
    """Get room info and members."""
    # Room info
    resp = session.get(
        f"{BASE}/pod/v3/room/{args.stream_id}/info",
        timeout=15,
    )
    resp.raise_for_status()
    room_info = resp.json()

    attrs = room_info.get("roomAttributes", {})
    print(f"Room: {attrs.get('name', '?')}")
    print(f"  Description: {attrs.get('description', 'N/A')}")
    print(f"  Created: {room_info.get('roomSystemInfo', {}).get('creationDate', '?')}")

    # Members
    members_resp = session.get(
        f"{BASE}/pod/v2/room/{args.stream_id}/membership/list",
        timeout=15,
    )
    members = []
    if members_resp.status_code == 200:
        members = members_resp.json() if isinstance(members_resp.json(), list) else []
        print(f"  Members: {len(members)}")
        for m in members[:20]:
            uid = m.get("id", "?")
            owner = m.get("owner", False)
            print(f"    UID: {uid} {'(owner)' if owner else ''}")

    result = {"room_info": room_info, "members": members}
    write_output("info", result)


def cmd_messages(session, args):
    """Fetch latest messages from a stream."""
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (args.minutes * 60 * 1000)

    resp = session.get(
        f"{BASE}/agent/v4/stream/{args.stream_id}/message",
        params={"since": since_ms, "limit": args.limit},
        timeout=20,
    )
    resp.raise_for_status()
    messages = resp.json()

    if not isinstance(messages, list):
        messages = []

    print(f"Got {len(messages)} message(s) (last {args.minutes} min):\n")
    for msg in messages:
        ts = msg.get("timestamp", "?")
        ts_str = epoch_to_str(ts) if ts != "?" else "?"
        user = msg.get("user", {})
        sender = user.get("displayName", user.get("userId", "?"))
        content = strip_messageml(msg.get("message", ""))
        print(f"  [{ts_str}] {sender}: {content[:300]}")

    write_output("messages", messages)


# ── CLI ──────────────────────────────────────────────────────────────────

def _apply_args_file(positional_keys=None, parent_keys=None):
    """If --args-file in argv, load JSON and rebuild argv as CLI flags."""
    if "--args-file" not in sys.argv:
        return
    idx = sys.argv.index("--args-file")
    path = sys.argv[idx + 1]
    with open(path, "r", encoding="utf-8") as f:
        af = json.load(f)
    argv = [sys.argv[0]]
    # Parent-level flags must appear before subcommand positional
    for pk in (parent_keys or []):
        if pk in af:
            v = af.pop(pk)
            flag = f"--{pk.replace('_', '-')}"
            if isinstance(v, bool):
                if v:
                    argv.append(flag)
            elif v is not None:
                argv.extend([flag, str(v)])
    for pk in (positional_keys or []):
        if pk in af:
            v = af.pop(pk)
            if isinstance(v, list):
                argv.extend(str(x) for x in v)
            elif v is not None:
                argv.append(str(v))
    for k, v in af.items():
        if k == "args_file":
            continue
        flag = f"--{k.replace('_', '-')}"
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        elif isinstance(v, list):
            for item in v:
                argv.extend([flag, str(item)])
        elif v is not None:
            argv.extend([flag, str(v)])
    sys.argv = argv


def _setup_out_file(out_path):
    """If out_path is set, tee stdout to a file (flushed on exit)."""
    if not out_path:
        return
    buf = io.StringIO()
    real = sys.stdout
    class _Tee:
        def write(self, s): real.write(s); buf.write(s)
        def flush(self): real.flush()
    sys.stdout = _Tee()
    def _flush():
        sys.stdout = real
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
    atexit.register(_flush)


def main():
    _apply_args_file(["command"], parent_keys=["out_file"])
    parser = argparse.ArgumentParser(
        description="Symphony chat reader via GS Bot Framework API Bridge",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search rooms by name")
    p_search.add_argument("--query", required=True, help="Room name search string")

    # info
    p_info = sub.add_parser("info", help="Get room info and members")
    p_info.add_argument("--stream-id", required=True, help="Symphony stream ID")

    # messages
    p_msgs = sub.add_parser("messages", help="Fetch latest messages")
    p_msgs.add_argument("--stream-id", required=True, help="Symphony stream ID")
    p_msgs.add_argument("--minutes", type=int, default=15, help="Look-back window in minutes (default: 15)")
    p_msgs.add_argument("--limit", type=int, default=50, help="Max messages to return (default: 50)")

    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file")
    args = parser.parse_args()
    _setup_out_file(args.out_file)
    session = get_session()

    handlers = {
        "search": cmd_search,
        "info": cmd_info,
        "messages": cmd_messages,
    }
    handlers[args.command](session, args)


if __name__ == "__main__":
    main()
