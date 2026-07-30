"""Shared GitLab PAT authentication via git credential fill.

Usage:
    from gitlab_auth import get_gitlab_pat, get_gitlab_headers, gitlab_api
"""

import json
import os
import ssl
import subprocess
import sys
import urllib.request


GITLAB_BASE = "https://gitlab.aws.site.gs.com"


def get_gitlab_pat(host="gitlab.aws.site.gs.com"):
    """Retrieve GitLab PAT from Windows Credential Manager via git credential fill."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input=f"protocol=https\nhost={host}\n\n",
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def get_gitlab_headers(host="gitlab.aws.site.gs.com"):
    """Get HTTP headers with PRIVATE-TOKEN for GitLab API requests."""
    pat = get_gitlab_pat(host)
    if not pat:
        print(f"ERROR: No GitLab PAT found for {host}. "
              "Store via: git credential approve", file=sys.stderr)
        sys.exit(1)
    return {"PRIVATE-TOKEN": pat, "Content-Type": "application/json"}


def _ssl_ctx():
    ctx = ssl.create_default_context()
    return ctx


def gitlab_api(path, method="GET", body=None, headers=None, base=GITLAB_BASE,
               timeout=30):
    """Make a GitLab API request.  Returns parsed JSON (or str for text responses)."""
    if headers is None:
        headers = get_gitlab_headers()
    url = f"{base}/api/v4{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8") if isinstance(body, dict) else body
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
