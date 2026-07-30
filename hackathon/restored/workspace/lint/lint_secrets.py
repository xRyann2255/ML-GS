#!/usr/bin/env python3
"""lint_secrets.py -- secret-hygiene scanner (suite wfo, Plan 01; AW-01/02/08/10/33).

Scans the git-TRACKED tree. memory/_dormant/ is deliberately IN scope: the
2026-07 incident's second token lived at memory/_dormant/ref/gssso-auth.md:87
and every other lint skips _dormant -- this one must not.

Checks:
  S1  PAT-shaped base64 literal: charset [A-Za-z0-9+/=], len >= 40, and
      contains at least one lowercase, one uppercase, one digit
  S2  tracked env files: any tracked path named `.env`/`*.env` fails; also
      fails if `git check-ignore workspace/config/.env` exits non-zero
  S3  bearer/basic authorization header with a literal token (>= 16 b64
      chars containing a digit or '=')
  S4  disabled TLS verification in skills/**/*.py: ssl.CERT_NONE,
      _create_unverified_context, verify=False, verify_ssl default-False,
      CONFLUENCE_VERIFY_SSL default "false"

Findings print tokens MASKED (first 4 chars + length) -- this tool must
never re-leak what it finds.

Allowlist: lint_secrets_allowlist.txt next to this file. Non-comment lines
are `<repo-relative-path>\t<substring>`; a finding is suppressed when its
file matches the path and the offending line contains the substring.

Exit codes: 0 clean, 1 findings, 2 execution error. Stdlib only.
Usage: python workspace/lint/lint_secrets.py [--selftest]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
ALLOWLIST_PATH = SELF.with_name("lint_secrets_allowlist.txt")

B64_TOKEN_RE = re.compile(r"[A-Za-z0-9+/=]{40,}")
BEARER_RE = re.compile(
    r"(?i)\b(?:authorization|bearer|basic)\b[^\r\n]{0,20}?([A-Za-z0-9+/=]{16,})"
)
TLS_PATTERNS = (
    "ssl.CERT_NONE",
    "_create_unverified_context",
    "verify=False",
    "verify = False",
    "verify_ssl: bool = False",
    '"CONFLUENCE_VERIFY_SSL", "false"',
)
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico",
    ".lock", ".svg", ".whl", ".gz", ".zip",
}
# wfo-01-1b: OpenAPI/Swagger spec files shipped alongside skills produce dozens
# of false-positive S1/S3 hits -- URL fragments, HTML-encoded description
# fields, OpenSSH public-key EXAMPLES, and OpenAPI $ref strings all match the
# base64/bearer regexes but contain no credentials. These are declarative
# API contracts, not code. Confirmed cases: skills/CANVAS/src/openapi.json
# (AppDir Gateway 3.0 spec), skills/FORWARD_NETWORK/src/forward_network_api.yaml
# (openssh-key example at :9630 + $ref chains).
SPEC_SUFFIXES = (".json", ".yaml", ".yml")


def is_spec_file(rel: str) -> bool:
    """True if `rel` is an API spec under skills/<name>/src/ (json/yaml/yml)."""
    parts = rel.split("/")
    return (
        len(parts) >= 4
        and parts[0] == "skills"
        and parts[2] == "src"
        and rel.lower().endswith(SPEC_SUFFIXES)
    )


def mask(token: str) -> str:
    return f"{token[:4]}…{len(token)}ch"


def looks_like_pat(token: str) -> bool:
    return (
        len(token) >= 40
        and any(c.islower() for c in token)
        and any(c.isupper() for c in token)
        and any(c.isdigit() for c in token)
    )


def find_pat_tokens(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in B64_TOKEN_RE.finditer(line):
            if looks_like_pat(m.group(0)):
                hits.append((lineno, mask(m.group(0))))
    return hits


def find_bearer_literals(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in BEARER_RE.finditer(line):
            tok = m.group(1)
            if any(c.isdigit() for c in tok) or "=" in tok:
                hits.append((lineno, mask(tok)))
    return hits


def find_tls_findings(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        for pat in TLS_PATTERNS:
            if pat in line:
                hits.append((lineno, pat))
    return hits


def load_allowlist() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if ALLOWLIST_PATH.exists():
        for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
            if raw.strip() and not raw.lstrip().startswith("#") and "\t" in raw:
                path, sub = raw.split("\t", 1)
                entries.append((path.strip(), sub.strip()))
    return entries


def allowed(entries: list[tuple[str, str]], rel: str, line_text: str) -> bool:
    return any(rel == p and s in line_text for p, s in entries)


def scan_file(path: Path, rel: str, allow: list[tuple[str, str]],
              findings: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    lines = text.splitlines()

    def emit(lineno: int, check: str, msg: str) -> None:
        raw = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        if not allowed(allow, rel, raw):
            findings.append(f"{rel}:{lineno}: [{check}] {msg}")

    # wfo-01-1b: skip S1/S3 on OpenAPI spec files under skills/*/src/. S4
    # (TLS disabled) is scoped to skills/**/*.py below, so it's unaffected.
    if is_spec_file(rel):
        return

    for lineno, tok in find_pat_tokens(text):
        emit(lineno, "S1", f"PAT-shaped base64 literal {tok}")
    for lineno, tok in find_bearer_literals(text):
        emit(lineno, "S3", f"authorization header with literal token {tok}")
    if rel.startswith("skills/") and rel.endswith(".py"):
        for lineno, pat in find_tls_findings(text):
            emit(lineno, "S4", f"TLS verification disabled: {pat}")


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"lint_secrets: cannot enumerate tracked files: {exc}")
        return 2
    allow = load_allowlist()
    findings: list[str] = []
    for rel in filter(None, out.split("\0")):
        path = ROOT / rel
        if path.resolve() in (SELF, ALLOWLIST_PATH.resolve()):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name == ".env" or rel.endswith(".env"):
            findings.append(f"{rel}:1: [S2] env file is git-tracked -- git rm --cached it")
        scan_file(path, rel, allow, findings)
    ci = subprocess.run(
        ["git", "check-ignore", "-q", "workspace/config/.env"], cwd=ROOT
    )
    if ci.returncode != 0:
        findings.append(
            "workspace/config/.env:0: [S2] not matched by .gitignore "
            "(git check-ignore exit != 0)"
        )
    if findings:
        print(f"lint_secrets: {len(findings)} finding(s)")
        for f in findings:
            print("  " + f)
        return 1
    print("lint_secrets: OK (0 findings)")
    return 0


def selftest() -> int:
    # fake PAT assembled at runtime so this file never contains a 40+ char literal
    fake_pat = "MTIz" + "NDU2Nzg5" * 5
    assert len(fake_pat) == 44 and looks_like_pat(fake_pat)
    assert find_pat_tokens(f'CONFLUENCE_PAT="{fake_pat}"') == [(1, mask(fake_pat))]
    assert find_pat_tokens("a" * 60) == []                # no upper, no digit
    assert find_pat_tokens("deadbeefcafe" * 4) == []      # hex-ish, no upper/digit mix
    assert find_bearer_literals(f"Authorization: Bearer {fake_pat}") == [(1, mask(fake_pat))]
    assert find_bearer_literals("Authorization: Bearer $env:CONFLUENCE_PAT") == []
    assert find_bearer_literals("Use bearer token authentication for the API") == []
    assert find_bearer_literals("Bearer InternalAuthenticationDocs") == []   # no digit -> not a token
    assert find_tls_findings("ctx.verify_mode = ssl.CERT_NONE") == [(1, "ssl.CERT_NONE")]
    assert find_tls_findings("# ssl.CERT_NONE is forbidden") == []
    assert find_tls_findings("resp = session.get(url, verify=False)") == [(1, "verify=False")]
    assert find_tls_findings("ctx = ssl.create_default_context()") == []
    # wfo-01-1b: OpenAPI spec files under skills/*/src/ produce dozens of
    # false-positive S1 hits (URL fragments, HTML descriptions, SSH-key
    # examples, OpenAPI $refs). scan_file() must skip them.
    assert is_spec_file("skills/foo/src/openapi.json") is True
    assert is_spec_file("skills/CANVAS/src/openapi.json") is True
    assert is_spec_file("skills/FORWARD_NETWORK/src/forward_network_api.yaml") is True
    assert is_spec_file("skills/foo/src/spec.yml") is True
    assert is_spec_file("skills/foo/src/bar.py") is False
    assert is_spec_file("skills/foo/openapi.json") is False   # not under src/
    assert is_spec_file("workspace/config/settings.json") is False
    print("lint_secrets selftest: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
