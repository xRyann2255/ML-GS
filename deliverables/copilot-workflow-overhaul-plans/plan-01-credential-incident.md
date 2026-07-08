# Plan 01 — Credential Incident & Security Hardening

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §8.
> Dispatch each agent task as a subagent with the context packet provided. Max 6 concurrent subagents.
> TDD is a hard gate (`.github/copilot-instructions.md` Critical Rule 5): the two Python-touching tasks
> (wfo-01-1 lint module, wfo-01-4 TLS flips, wfo-01-5 lint-scope extension) get real red-then-green;
> the doc/config tasks are Rule-5-exempt per the rule's own carve-out.
> Requires: nothing merged before it (first plan of the suite). **Gate A human confirmations H1+H2 are
> the hard precondition — no agent commit that references the secrets until both are confirmed.**

**Goal:** Zero live credentials, PII literals, TLS-off clients, and permission-gate wildcards in the tracked tree — proven by a new `lint_secrets.py` shown red on the pre-fix tree and green after — with both leaked PATs revoked by the user first (kills AW-01, AW-02, AW-03, AW-08, AW-10, AW-32, AW-33).

**Architecture:** Everything extends existing seams. `lint_secrets.py` is a new stdlib-only check appended to `workspace/lint/lint_all.py`'s `LINTS` registry (never rewriting the 14 existing scripts — do-not-rebuild #7). The 8 TLS fixes copy the in-repo-correct `ssl.create_default_context()` pattern from `skills/ETASK/src/etask.py:137` (do-not-rebuild #13). `workspace/config/.env.template` mirrors the adjacent `user.json.template` (do-not-rebuild #14). `skills/CONFLUENCE/src/client.py`'s `from_env()` env-var auth is correct as written and is untouched except the `verify_ssl` defaults (do-not-rebuild #8). All work happens in the **real GS repo** (which has git); the authored-against mirror has no `.git`, so every packet carries the drift check.

**Tech stack:** No new dependencies. New lint is stdlib-only Python (re, subprocess, pathlib), matching the existing suite. Everything else is docs, config, and single-line Python edits.

**Research grounding:** The 2026-07 agentic-workflow audit (sole finding source), findings AW-01/02 (BLOCKER, two live Confluence PATs at `workspace/config/.env:1` fingerprint `NzM2…44ch` and `memory/_dormant/ref/gssso-auth.md:87` fingerprint `MTQ2…44ch`), AW-03 (BLOCKER, wildcard terminal allowlist + whole-H:-drive read grant), AW-08 (HIGH, 8 TLS-verification-off sites across 6 clients), AW-10 (HIGH, skill mandates PAT in tracked un-ignored `.env`), AW-32/AW-33 (MEDIUM, PII in skill examples; plaintext SSO cookie in un-ignored tmp). Freshness recon 2026-07-07: all probed sites STILL-PRESENT, byte-identical. **Expected-outcome prior (overview §4):** 2 live PATs in tree → 0 in tree AND revoked; tokens are dead after H1 even where history retains them until H3/H4. Calibration warning: if any acceptance grep passes suspiciously early, suspect the grep (wrong pathspec or exclusion) before believing the tree is clean — re-run against the fingerprint prefixes without exclusions and inspect each hit by hand.

---

## 1. Global constraints

All of 00-overview §5 (shared conventions: packet schema union, return contract, the 9 HARD rules, git/MR conventions) applies to every task. Plan-specific hard rules:

1. **Never quote actual token values anywhere** — not in commits, MR text, lint output, subagent returns, or this plan. Use only the redacted fingerprints from the overview: `NzM2…44ch` (`.env:1`) and `MTQ2…44ch` (`gssso-auth.md:87`). `lint_secrets.py` masks everything it finds for the same reason.
2. **Gate A ordering:** Tasks H1–H5 open the plan. H1 + H2 must be user-confirmed **before any agent commit referencing the secrets** (i.e., before Wave 2 starts; Wave 1's lint work references only fingerprints and patterns, but hold the entire MR push until H1+H2 regardless). H3/H4 may lag — tokens are already dead after H1 — but record them as open items in the MR description; AW-01 closes fully only when they complete.
3. **Do NOT touch `skills/CONFLUENCE/src/client.py` `from_env()` logic beyond the `verify_ssl` defaults** (`:62` and the `:120` env-var default). The env-read path is correct as written.
4. **Do NOT skip `memory/_dormant/` in `lint_secrets.py`.** Every existing lint skips it by design; that blindness is why the second PAT survived. This one scans it.
5. **Drift check (every packet, verbatim):** verify the cited path:line against the live tree before editing; if it moved, locate by content and note the delta in your return.
6. The 5 ACTIVE research plans in `workspace/plans/` (`bug3-iv-context-fix`, `gnn-gpu-parallel-plan`, `linear-alpha-tuning`, `plan-c-prediction-blending`, `trial-068-conditional-duan`) are read-only; never touch `trials.yaml` or `workspace/configs/`. Never run this plan while a research `/execute` session is live.
7. **Surface note:** Plan 03 has not landed, so `vol.cmd` does not exist yet. Run this plan's Python verification on **S-B** via `./vol exec "python workspace/lint/<script>.py"` (read the `OUTPUT_FILE=` path per HARD rule 3). On S-A the only sanctioned Python vehicle is the existing `lint-workspace` run_task (which runs `lint_all.py`); everything else on S-A is doc/config-only until Plan 03.
8. One MR: branch `chore/wf-overhaul-01-security` off `master`, rebase onto `origin/master` before push, MR title human-generic (no AW-IDs in the title; IDs and the red→green evidence go in the description).

---

## 2. File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `workspace/lint/lint_secrets.py` | Secret-hygiene scanner: PAT-shaped tokens, tracked env files, bearer literals, TLS-off patterns (S1–S4) |
| Create | `workspace/lint/lint_secrets_allowlist.txt` | Suppression file for sanctioned fingerprint mentions (ships empty) |
| Modify | `workspace/lint/lint_all.py` | Append one `LINTS` tuple registering the new check (`:57-156` region) |
| Modify | `.gitignore` | Add `/workspace/config/.env`, `*.env`, `/workspace/tmp/` next to the `:9` `user.json` entry |
| Untrack | `workspace/config/.env` | `git rm --cached` — file stays on disk for `from_env()` |
| Create | `workspace/config/.env.template` | Keys-only template mirroring `user.json.template` |
| Modify | `memory/_dormant/ref/gssso-auth.md` | Replace the `:87` PAT literal with `$env:CONFLUENCE_PAT` |
| Modify | `skills/CONFLUENCE/SKILL.md` | `:50` say .env is gitignored/never committed; `:189` verify-SSL row rewritten |
| Modify | `memory/_dormant/ref/confluence-auth.md` | `:24`, `:66` say .env is gitignored/never committed |
| Modify | `skills/_shared/gitlab_auth.py` | `:48` CERT_NONE → `ssl.create_default_context()` |
| Modify | `skills/PRIME_QUERY/src/prime.py` | `:82` CERT_NONE → verified context |
| Modify | `skills/DIRGET/src/dirget.py` | `:78` AND `:100-102` CERT_NONE → verified contexts |
| Modify | `skills/CONFLUENCE/src/client.py` | `:62` `verify_ssl` default True; `:120` env default `"true"` |
| Modify | `skills/TMD/src/tmd.py` | `:40` `verify=False` removed AND `:75-77` CERT_NONE → verified context |
| Modify | `skills/FORWARD_NETWORK/src/fwd_api.py` | `:91–:97` region `_create_unverified_context` → verified context |
| Modify | `skills/{ETASK,NDS_INFRA,DIRGET,OUTLOOK,SLANG_EDIT,SECDB_POSITION,TMD}/SKILL.md` | Real kerberos IDs / employee PII / book+trade identifiers → placeholders |
| Modify | `workspace/lint/lint_hardcoded_env.py` | Extend scan scope: PII patterns over `skills/**/SKILL.md` |
| Modify | `ml-vol-estimator.code-workspace` | Delete `commandAllowlist` `terminal:["*"]` and `additionalReadAccessPaths:["h:/"]` (`:21-26`) |
| Modify | `skills/GSSSO_AUTH/SKILL.md` | Cookie-hygiene note: gitignored tmp, delete after use |

---

## 3. Interfaces

**Consumes (copied from the overview ledger — never re-derived):**
- Gate A definition — 00-overview §2, row 01 (acceptance commands used verbatim in §7).
- `LINTS` registry entry — `workspace/lint/lint_all.py:57-156`, existing 5-tuple format `(label, script_path, extra_args, is_slow, supports_fix)`; new checks APPEND tuples; existing 14 scripts never rewritten.
- `etask.py:137` `ssl.create_default_context()` — the in-repo-correct model for all 8 TLS fixes.
- `workspace/config/user.json.template` — the model for `.env.template`.
- `subtask_id` format `wfo-<NN>-<M>`; branch format `chore/wf-overhaul-NN-<topic>`.
- S-A / S-B surface definitions (ledger rows 1–2); until Plan 03, S-A is doc/config-only for agents.

**Produces (later plans rely on these):**
- `lint_secrets.py` in `workspace/lint/` — ledger row: scans tracked tree for PAT-shaped base64 tokens (len≥40, mixed-case+digits+`+/=`), `.env` files outside gitignore, bearer-header literals; whitelist file for sanctioned fingerprint mentions in docs. **This plan additionally gives it an S4 disabled-TLS scan class over `skills/**/*.py`** (ledger deviation, reported) so the TLS flips get mandated red-then-green evidence. Plan 04 treats it as one of the four highest-blast-radius red-then-green checks.
- `workspace/lint/lint_secrets_allowlist.txt` — the ledger's "whitelist file", concrete path chosen here (ledger deviation, reported). Format: `<repo-relative-path><TAB><substring>` per line.
- `workspace/config/.env.template` — ledger row: `CONFLUENCE_PAT=` + `CONFLUENCE_URL=` placeholders, mirrors `user.json.template` style.
- `.gitignore` entries `/workspace/config/.env`, `*.env`, `/workspace/tmp/` — Plan 03's args-file contract and Plan 04's pre-commit trigger assume `/workspace/tmp/` is ignored.
- 8/8 TLS clients verifying certs — Plan 04's standing lint gate keeps this green via S4.

---

## 4. HUMAN ACTION tasks (open the plan; each separately gated, nothing bundled)

These five tasks have **no context packet** and are never dispatched to a subagent. Acceptance for each is exactly: **user confirms**. They are separate tasks so that no confirmation is ever inferred from another.

### Task H1: Revoke BOTH Confluence PATs
Revoke the token committed at `workspace/config/.env:1` (fingerprint `NzM2…44ch`) AND the distinct token at `memory/_dormant/ref/gssso-auth.md:87` (fingerprint `MTQ2…44ch`) at the confluence.work.gs.com token settings page. Why an agent cannot do it: Confluence UI action, user credentials.
**Acceptance:** user confirms both tokens revoked. **Gate A limb 1.**

### Task H2: GS security-compliance notification decision
Decide — and if decided yes, execute — the GS security-compliance notification for the exposure (AW-02 is a reportable data-exfiltration event: internal tooling snapshot, credentials, endpoints, PII on an off-perimeter machine). Why an agent cannot do it: firm-policy judgment call.
**Acceptance:** user confirms the decision was made (either way). **Gate A limb 2.**

### Task H3: History purge on the GS remote
After the `git rm --cached` MR lands (Task 2), purge the secrets from GS-remote history (git-filter-repo or BFG + force-push, per repo-admin process). Why an agent cannot do it: repo-admin rights + MR approval. May lag — tokens are dead after H1.
**Acceptance:** user confirms purge complete. AW-01 fully closes only with H3+H4.

### Task H4: Purge the parent ML-GS repo's `origin/presentation` branch
The parent repo's `origin/presentation` branch independently carries the live token in history (orphan snapshot commit + raw audit HTML). Purge or delete that branch on the remote. Why an agent cannot do it: different repo, owner action.
**Acceptance:** user confirms branch purged/deleted.

### Task H5: Disposition of the off-perimeter personal-machine copy
Secure or delete the personal-machine copy of the ml-vol-estimator snapshot per the H2 decision. Why an agent cannot do it: outside the repo entirely.
**Acceptance:** user confirms disposition.

> **GATE A (blocking):** H1 + H2 confirmed **before** any agent MR referencing the secrets is pushed. The orchestrator prompt (§8) makes this the precondition check; if either is unconfirmed, STOP and yield to the user.

---

## 5. Agent tasks

### Task 1: `lint_secrets.py` — new check, shown RED on the pre-fix tree

**Files:** Create `workspace/lint/lint_secrets.py`, `workspace/lint/lint_secrets_allowlist.txt`; Modify `workspace/lint/lint_all.py` (one appended tuple). Test: the module's own `--selftest` plus the pre-fix tree scan.

**This task lands FIRST (Wave 1), before any fix task, so the red run is recorded against the pre-fix tree.** The red output is Gate A evidence and goes in the MR description (with masked tokens only — masking is built into the tool).

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-1"
goal: "Ship workspace/lint/lint_secrets.py (S1 PAT-shaped tokens, S2 tracked/un-ignored env files, S3 bearer literals, S4 TLS-off in skills/**/*.py) registered in lint_all.py LINTS, with --selftest PASSING and the tree scan recorded FAILING on the pre-fix tree."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section — the code lives HERE
  - workspace/lint/lint_all.py          # LINTS tuple shape to mirror (:57-156)
  - workspace/lint/lint_broken_refs.py  # style exemplar for a standalone check script
write_scope:
  - workspace/lint/lint_secrets.py
  - workspace/lint/lint_secrets_allowlist.txt
  - workspace/lint/lint_all.py
acceptance_criteria:
  - "./vol exec \"python workspace/lint/lint_secrets.py --selftest\" -> OUTPUT_FILE shows 'lint_secrets selftest: OK', EXIT_CODE=0"
  - "./vol exec \"python workspace/lint/lint_secrets.py\" -> EXIT_CODE=1 with findings incl. workspace/config/.env [S1+S2], memory/_dormant/ref/gssso-auth.md:87 [S1], and 8 [S4] TLS sites — RED evidence, paste into MR"
  - "grep -n 'lint_secrets' workspace/lint/lint_all.py -> exactly one appended LINTS tuple"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "do NOT skip memory/_dormant/ — it must be in scan scope; never print an unmasked token; never rewrite any existing lint script"
context_summary: |
  First task of the credential-incident plan. Wave-2 tasks fix what this lint finds, so it must land
  and be recorded RED first. The ledger fixes this module's contract (three scan classes + whitelist
  file); this plan adds the S4 TLS class so the Wave-2 TLS flips have red-then-green evidence.
  lint_all.py's LINTS is append-only 5-tuples — mirror the neighbors exactly.
depends_on: []
```

- [ ] **Step 1: Write the failing test.** Create `workspace/lint/lint_secrets.py` containing (a) the module docstring, imports, and constants exactly as in the Step-3 listing, (b) the complete `mask()` and `selftest()` functions from the Step-3 listing, and (c) these four stubs in place of the real detectors:

  ```python
  def looks_like_pat(token: str) -> bool:
      raise NotImplementedError

  def find_pat_tokens(text: str) -> list[tuple[int, str]]:
      raise NotImplementedError

  def find_bearer_literals(text: str) -> list[tuple[int, str]]:
      raise NotImplementedError

  def find_tls_findings(text: str) -> list[tuple[int, str]]:
      raise NotImplementedError
  ```

  The selftest (the test code, verbatim from the final listing) is:

  ```python
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
      print("lint_secrets selftest: OK")
      return 0
  ```

- [ ] **Step 2: Run to confirm red.** `./vol exec "python workspace/lint/lint_secrets.py --selftest"` → read the `OUTPUT_FILE=` path → expect `NotImplementedError` traceback, `EXIT_CODE` non-zero. **RED.**

- [ ] **Step 3: Implement.** Replace the stubs so the complete file is:

  ```python
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


  # selftest() as written in Step 1 goes here, unchanged.


  if __name__ == "__main__":
      sys.exit(main(sys.argv[1:]))
  ```

  Create `workspace/lint/lint_secrets_allowlist.txt`:

  ```
  # lint_secrets_allowlist.txt -- sanctioned suppressions for lint_secrets.py
  # Format: <repo-relative-path><TAB><substring-of-offending-line>
  # Every entry must be followed by a comment line explaining WHY it is sanctioned.
  # Ships EMPTY: the pre-fix tree's findings are real and get FIXED, not allowlisted.
  # If the pre-fix scan surfaces additional true-positive secrets beyond the audit's,
  # STOP and report them to the user -- do not allowlist a real secret.
  ```

  Register in `workspace/lint/lint_all.py`: open the `LINTS` list (`:57-156` — drift check applies), copy the exact shape of the last existing 5-tuple `(label, script_path, extra_args, is_slow, supports_fix)`, and append:

  ```python
      ("secrets", LINT_DIR / "lint_secrets.py", [], False, False),
  ```

  Mirror the live file's path-variable name (`LINT_DIR` or whatever the neighbors use). If the live tuple arity or field order differs from the 5-tuple above, match the live file and record the delta in your return-contract `notes`.

- [ ] **Step 4: Run to green (selftest) and red (tree — expected and recorded).**
  - `./vol exec "python workspace/lint/lint_secrets.py --selftest"` → `lint_secrets selftest: OK`, `EXIT_CODE=0`. **GREEN.**
  - `./vol exec "python workspace/lint/lint_secrets.py"` → `EXIT_CODE=1`; findings MUST include at minimum: `workspace/config/.env:1 [S1]` + `[S2] env file is git-tracked` + `[S2] not matched by .gitignore`, `memory/_dormant/ref/gssso-auth.md:87 [S1]`, and 8 `[S4]` lines across `skills/_shared/gitlab_auth.py`, `skills/PRIME_QUERY/src/prime.py`, `skills/DIRGET/src/dirget.py` (×2), `skills/CONFLUENCE/src/client.py` (×2: `:62` default and `:120` env default), `skills/TMD/src/tmd.py` (×2), `skills/FORWARD_NETWORK/src/fwd_api.py`. **Paste this masked output into the MR description as the Gate A "red pre-fix" evidence.** If a finding named here is absent, the tree drifted — STOP and return `blocked` with the diff. Additional true-positive findings beyond these are reported to the user, not allowlisted.
  - `./vol exec "python workspace/lint/lint_all.py"` → the `secrets` row runs and FAILS (expected until Wave 2 lands; the 3 pre-existing failures also remain until Plan 04 — after this task the registry is 15 wide, so Plan 02 inherits a 3/15 baseline — note both facts in the return).

- [ ] **Step 5: Commit** — `chore(lint): add secrets scanner lint_secrets.py, register in lint_all`

---

### Task 2: Untrack `.env`, gitignore env files + tmp, ship `.env.template`

**Files:** Modify `.gitignore`; untrack `workspace/config/.env` (`git rm --cached`); Create `workspace/config/.env.template`. Config-only — TDD-exempt; verification is the lint + git commands below.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-2"
goal: "workspace/config/.env untracked (file kept on disk), .gitignore gains /workspace/config/.env + *.env + /workspace/tmp/, and .env.template ships — proven by git check-ignore exit 0 and zero tracked .env files."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section
  - .gitignore                              # :9 anchor (/workspace/config/user.json)
  - workspace/config/user.json.template     # style model for .env.template
write_scope:
  - .gitignore
  - workspace/config/.env.template
  # plus the index-only removal: git rm --cached workspace/config/.env (and workspace/tmp/ if tracked)
acceptance_criteria:
  - "git check-ignore workspace/config/.env -> exit 0"
  - "git ls-files | grep -E '(^|/)\\.env$|\\.env$' -> no output (only .env.template remains tracked, which does not match)"
  - "test -f workspace/config/.env -> exit 0 (on-disk file preserved for from_env())"
  - "git check-ignore workspace/tmp/anything.txt -> exit 0"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "NEVER delete or print the on-disk .env contents; index removal only; never git add -A (embedded repo at workspace/docs/enghub/)"
context_summary: |
  Gate A (H1+H2) is confirmed. The .env file's token is revoked but the file must stay on disk because
  skills/CONFLUENCE/src/client.py from_env() reads it (correct code, do-not-rebuild #8). This task
  turns lint_secrets.py's S2 findings green; Task wfo-01-1 already recorded them red.
depends_on: ["wfo-01-1"]
```

- [ ] **Step 1 (no failing test — config task; red evidence is wfo-01-1's recorded S2 findings).** Edit `.gitignore`: locate the existing entry `/workspace/config/user.json` (line 9 — drift check) and insert directly below it:

  ```gitignore
  /workspace/config/.env
  *.env
  /workspace/tmp/
  ```

- [ ] **Step 2: Untrack the secret file (index only — the working-tree file stays):**

  ```
  git rm --cached workspace/config/.env
  ```

  Then check whether anything under `workspace/tmp/` is tracked: `git ls-files workspace/tmp/` — if non-empty, also `git rm -r --cached workspace/tmp/`.

- [ ] **Step 3: Create `workspace/config/.env.template`** (mirrors `user.json.template`'s copy-then-fill convention; the URL is non-secret and matches the documented Confluence base):

  ```
  # workspace/config/.env.template
  # Copy to workspace/config/.env (gitignored -- NEVER commit) and fill in your PAT.
  # Generate a PAT at: confluence.work.gs.com token settings.
  CONFLUENCE_PAT=
  CONFLUENCE_URL=https://confluence.work.gs.com/
  ```

- [ ] **Step 4: Run to green.** All four acceptance commands above, plus `./vol exec "python workspace/lint/lint_secrets.py"` → the three S2 findings and `.env:1` S1 finding are gone (S1 at `gssso-auth.md:87` and the S4s remain until Tasks 3/4 — expected at this stage).
- [ ] **Step 5: Commit** — `chore(config): untrack .env; ignore env files and tmp; add .env.template`

---

### Task 3: Kill the second PAT literal and fix the credential docs

**Files:** Modify `memory/_dormant/ref/gssso-auth.md` (`:87`), `skills/CONFLUENCE/SKILL.md` (`:50`, `:189`), `memory/_dormant/ref/confluence-auth.md` (`:24`, `:66`). Docs-only — TDD-exempt; red evidence is wfo-01-1's recorded `gssso-auth.md:87` S1 finding.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-3"
goal: "gssso-auth.md:87's PAT literal replaced with $env:CONFLUENCE_PAT and the three credential-doc sites state .env is gitignored — proven by zero MTQ2-prefix hits and lint_secrets S1 clean outside .env."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section
  - memory/_dormant/ref/gssso-auth.md
  - skills/CONFLUENCE/SKILL.md
  - memory/_dormant/ref/confluence-auth.md
write_scope:
  - memory/_dormant/ref/gssso-auth.md
  - skills/CONFLUENCE/SKILL.md
  - memory/_dormant/ref/confluence-auth.md
acceptance_criteria:
  - "git grep -n 'MTQ2' -- ':!workspace/plans/copilot-workflow-overhaul/' -> no output"
  - "git grep -n 'verify_ssl=False' -- skills/CONFLUENCE/SKILL.md -> no output"
  - "grep -n 'gitignored' skills/CONFLUENCE/SKILL.md memory/_dormant/ref/confluence-auth.md -> >=3 hits (one per edited site)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "NEVER quote the token value being removed — not in the diff summary, commit, or return; the deletion diff itself is unavoidable and sanctioned"
context_summary: |
  Gate A (H1+H2) confirmed; the token being deleted is already revoked. confluence-auth.md:78 already
  calls hardcoding an anti-pattern — this task makes the offending example follow the repo's own rule.
  Task wfo-01-4 flips the client code defaults; this task only edits docs, including SKILL.md:189
  which currently tells agents to keep verify_ssl=False.
depends_on: ["wfo-01-1"]
```

- [ ] **Step 1: `memory/_dormant/ref/gssso-auth.md:87`** — inside the "Confluence REST API (PAT Authentication)" PowerShell snippet, replace the literal-assignment line with:

  ```powershell
  # PAT comes from the environment -- set CONFLUENCE_PAT in your shell or in
  # workspace/config/.env (gitignored; copy from workspace/config/.env.template).
  $pat = $env:CONFLUENCE_PAT
  ```

- [ ] **Step 2: `skills/CONFLUENCE/SKILL.md:50`** — rewrite the prerequisite line to state: `CONFLUENCE_PAT` set in `workspace/config/.env` — **gitignored, never committed; create it by copying `workspace/config/.env.template`**.

- [ ] **Step 3: `skills/CONFLUENCE/SKILL.md:189`** — replace the troubleshooting row "Keep verify_ssl=False (default) — GS internal certs use custom CA" with: *"TLS verification is ON by default. On certificate errors, point the client at the GS CA bundle (set `CONFLUENCE_CA_BUNDLE` to `C:\ProgramData\certificates\cacerts.cer`) — never disable verification."*

- [ ] **Step 4: `memory/_dormant/ref/confluence-auth.md:24` and `:66`** — both sites document the `workspace/config/.env` path; append to each: *"(gitignored — never committed; created from `workspace/config/.env.template`)"*.

- [ ] **Step 5: Run to green.** The three acceptance commands, plus `./vol exec "python workspace/lint/lint_secrets.py"` → no S1 finding at `gssso-auth.md` (S4s remain until wfo-01-4). Commit — `docs(memory): replace hardcoded pat with env read; document gitignored .env`

---

### Task 4: Flip all 8 TLS-off sites to verified contexts (etask.py:137 pattern)

**Files:** Modify `skills/_shared/gitlab_auth.py`, `skills/PRIME_QUERY/src/prime.py`, `skills/DIRGET/src/dirget.py`, `skills/CONFLUENCE/src/client.py`, `skills/TMD/src/tmd.py`, `skills/FORWARD_NETWORK/src/fwd_api.py`. Python code — **TDD applies**: red = wfo-01-1's recorded 8 S4 findings on the pre-fix tree (characterization of current insecure behavior); green = S4 clean + per-file compile checks.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-4"
goal: "All 8 disabled-TLS sites across 6 skill clients verify certificates via ssl.create_default_context() / verify=True — proven by lint_secrets S4 going 8 findings -> 0 and py_compile passing on all 6 files."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section — site list + recipe HERE
  - skills/ETASK/src/etask.py            # :137 — the correct pattern to copy
  - skills/SYMPHONY/src/symphony.py      # :25-27 — CA-bundle fallback pattern (read-only)
write_scope:
  - skills/_shared/gitlab_auth.py
  - skills/PRIME_QUERY/src/prime.py
  - skills/DIRGET/src/dirget.py
  - skills/CONFLUENCE/src/client.py
  - skills/TMD/src/tmd.py
  - skills/FORWARD_NETWORK/src/fwd_api.py
acceptance_criteria:
  - "./vol exec \"python workspace/lint/lint_secrets.py\" -> zero [S4] lines in OUTPUT_FILE"
  - "./vol exec \"python -m py_compile skills/_shared/gitlab_auth.py skills/PRIME_QUERY/src/prime.py skills/DIRGET/src/dirget.py skills/CONFLUENCE/src/client.py skills/TMD/src/tmd.py skills/FORWARD_NETWORK/src/fwd_api.py\" -> EXIT_CODE=0"
  - "git grep -nE 'CERT_NONE|_create_unverified_context|verify=False|verify = False' -- 'skills/' -> no output"
  - "git grep -n 'CONFLUENCE_VERIFY_SSL' -- skills/CONFLUENCE/src/client.py -> line shows default \"true\""
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "do NOT touch client.py from_env() logic beyond the verify_ssl defaults at :62 and :120; do NOT edit etask.py or symphony.py (read-only exemplars); never add a CERT_NONE fallback"
context_summary: |
  8 sites in 6 files send bearer secrets over unverified TLS (AW-08). etask.py:137 proves
  ssl.create_default_context() works against internal GS hosts (Windows Python loads the machine
  cert store incl. corporate roots). Red evidence was recorded by wfo-01-1's pre-fix S4 scan.
  Doc-side verify_ssl guidance (SKILL.md:189) is wfo-01-3's job, not yours.
depends_on: ["wfo-01-1"]
```

- [ ] **Step 1: Red is already recorded** — wfo-01-1's pre-fix scan shows exactly these 8 S4 findings (re-run `./vol exec "python workspace/lint/lint_secrets.py"` now and confirm the 8 sites below still appear before editing; if any is missing, STOP and return `blocked` with the diff):

  | # | File:line | Current | Change to |
  |---|---|---|---|
  | 1 | `skills/_shared/gitlab_auth.py:48-49` (ctx used at `:63` with PRIVATE-TOKEN) | `CERT_NONE` context | `ctx = ssl.create_default_context()` |
  | 2 | `skills/PRIME_QUERY/src/prime.py:82-83` | `CERT_NONE` context | `ctx = ssl.create_default_context()` |
  | 3 | `skills/DIRGET/src/dirget.py:78-79` | `CERT_NONE` context | `ctx = ssl.create_default_context()` |
  | 4 | `skills/DIRGET/src/dirget.py:100-102` (second block) | `CERT_NONE` context | `ctx = ssl.create_default_context()` |
  | 5 | `skills/CONFLUENCE/src/client.py:62` | `verify_ssl: bool = False` | `verify_ssl: bool = True` |
  | 6 | `skills/CONFLUENCE/src/client.py:120` | `os.environ.get("CONFLUENCE_VERIFY_SSL", "false")` | default `"true"` |
  | 7 | `skills/TMD/src/tmd.py:40` and `:75-77` | `verify=False` + `CERT_NONE` block | drop the kwarg (requests verifies by default); `ssl.create_default_context()` |
  | 8 | `skills/FORWARD_NETWORK/src/fwd_api.py:91-97` region | `ssl._create_unverified_context()` (audit cites `:91` and `:97`; locate by content) | `ssl.create_default_context()` |

  (Rows 7 and 8 each cover the paired sites the audit's verifier added; the S4 scan counts 8+ raw pattern hits — the acceptance bar is **zero remaining**, not an exact count.)

- [ ] **Step 2: Implement.** For every `CERT_NONE` block, the recipe is mechanical — delete the two disabling lines and construct a default context, exactly as `etask.py:137` does:

  ```python
  # BEFORE (pattern at each CERT_NONE site):
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE

  # AFTER (etask.py:137 pattern -- verified working against internal GS hosts):
  ctx = ssl.create_default_context()
  ```

  For `tmd.py:40`, remove `verify=False` from the requests call (requests verifies by default). For `fwd_api.py`, replace `ssl._create_unverified_context()` with `ssl.create_default_context()`. For `client.py`, flip only the two defaults (`:62`, `:120`); `session.verify` wiring at `:80` is untouched. Where a call site later fails against a corporate-CA host, the sanctioned fallback is a CA bundle (`cafile=r"C:\ProgramData\certificates\cacerts.cer"`, per `symphony.py:25-27`'s `REQUESTS_CA_BUNDLE` pattern) — **never a revert to CERT_NONE**. Do not pre-add the cafile speculatively; note the fallback in each file's nearest comment only if a comment already marks the old behavior.

- [ ] **Step 3: Run to green.** All four acceptance commands. The S4 count in `lint_secrets.py` output goes from the recorded pre-fix findings to **0**.
- [ ] **Step 4: Runtime smoke (best-effort, S-B):** `./vol exec "python -c \"import ssl; ctx = ssl.create_default_context(); print(ctx.verify_mode == ssl.CERT_REQUIRED)\""` → `True` (sanity that the platform default is verifying). Live-endpoint calls are NOT part of acceptance (GS hosts unreachable off-box); note this in the return.
- [ ] **Step 5: Commit** — `fix(skills): verify tls certificates in all eight client call sites`

---

### Task 5: Replace real kerberos IDs / PII with placeholders; extend `lint_hardcoded_env.py`

**Files:** Modify `skills/ETASK/SKILL.md`, `skills/NDS_INFRA/SKILL.md`, `skills/DIRGET/SKILL.md`, `skills/OUTLOOK/SKILL.md`, `skills/SLANG_EDIT/SKILL.md`, `skills/SECDB_POSITION/SKILL.md`, `skills/TMD/SKILL.md`, and `workspace/lint/lint_hardcoded_env.py`. The lint extension is Python — **red-then-green applies**: extend the scan first, show it red on the un-fixed SKILL.mds, then replace the PII, then green.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-5"
goal: "Real kerberos IDs, employee emails/PII, and book/trade identifiers in the 7 named SKILL.md example blocks replaced by the plan's placeholder table, enforced by a PII scan class added to lint_hardcoded_env.py shown red-then-green."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section — placeholder table + pattern code HERE
  - workspace/lint/lint_hardcoded_env.py   # the script being extended — read fully first
write_scope:
  - workspace/lint/lint_hardcoded_env.py
  - skills/ETASK/SKILL.md
  - skills/NDS_INFRA/SKILL.md
  - skills/DIRGET/SKILL.md
  - skills/OUTLOOK/SKILL.md
  - skills/SLANG_EDIT/SKILL.md
  - skills/SECDB_POSITION/SKILL.md
  - skills/TMD/SKILL.md
acceptance_criteria:
  - "./vol exec \"python workspace/lint/lint_hardcoded_env.py\" (pre-replacement, post-extension) -> EXIT_CODE=1 with PII findings in >=1 of the 7 SKILL.mds — RED evidence, paste into MR"
  - "./vol exec \"python workspace/lint/lint_hardcoded_env.py\" (post-replacement) -> EXIT_CODE=0"
  - "git grep -cE '\\b[a-z]+\\.[a-z]+@(ny\\.email\\.)?gs\\.com\\b' -- 'skills/*/SKILL.md' -> 0 hits outside the placeholder first.last@gs.com"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "extend lint_hardcoded_env.py's scan scope only — never rewrite its existing check logic (do-not-rebuild #7); never reproduce a removed real identifier in commit/MR/return text"
context_summary: |
  AW-32: write-capable skill examples embed real kerberos IDs, employee emails, device IPs, and
  book/trade identifiers (e.g. NDS_INFRA/SKILL.md:76/91/93). This task swaps them for the fixed
  placeholder table and makes lint_hardcoded_env.py see SKILL.md examples so the rot can't return.
  lint_secrets.py (wfo-01-1) covers tokens/TLS; PII lives here — do not duplicate checks across the two.
depends_on: ["wfo-01-1"]
```

- [ ] **Step 1: Write the failing check (extend the lint FIRST).** Read `workspace/lint/lint_hardcoded_env.py` fully. Following its existing pattern-list and findings-report shape (it is the in-repo exemplar; mirror its style exactly), add a PII scan class and widen its scanned-file set to include `skills/**/SKILL.md`:

  ```python
  # Plan 01 (AW-32): PII in skill example blocks -- scan skills/**/SKILL.md too.
  PII_PATTERNS = [
      (re.compile(r"\b[a-z]+\.[a-z]+@(?:ny\.email\.)?gs\.com\b"),
       "employee email -- use first.last@gs.com"),
      (re.compile(r"\b(?:kerberos|kid|username|user)\s*[=:]\s*['\"]?[a-z]{3,8}\d{0,3}\b"),
       "kerberos id -- use jdoe"),
      (re.compile(r"\b(?:lastIP|last_ip|ip)\s*[=:]\s*['\"]?\d{1,3}(?:\.\d{1,3}){3}\b"),
       "device IP -- use 10.0.0.1"),
      (re.compile(r"\b(?:serial|Serial)\s*[=:]\s*['\"]?[A-Z0-9]{6,}\b"),
       "device serial -- use SN0000000"),
  ]
  PII_PLACEHOLDERS_OK = {"first.last@gs.com", "jdoe", "10.0.0.1", "sn0000000", "examplebook", "t0000000"}
  ```

  A hit whose matched text (lowercased) is in `PII_PLACEHOLDERS_OK` is not a finding. Wire the patterns into the script's existing scan loop for the SKILL.md file set, reporting via its existing findings format. If the script has a `main()`/exit-code convention different from "0 clean / 1 findings", match the live convention and note it.

- [ ] **Step 2: Run to confirm red.** `./vol exec "python workspace/lint/lint_hardcoded_env.py"` → non-zero, PII findings across the 7 named SKILL.mds (NDS_INFRA `:76/:91/:93` at minimum per the audit). **Paste masked/paraphrased finding locations (never the values) into the MR as red evidence.** If zero findings appear, the patterns missed the live values — inspect the 7 files by hand (grep for `@gs.com`, IP-shaped strings, `Serial`, book/trade IDs), tighten the regexes to catch what is actually there, and re-run to red before proceeding.

- [ ] **Step 3: Implement (replace the PII).** In each of the 7 SKILL.mds, replace every real identifier in example tables/blocks using this fixed placeholder table — keep examples syntactically plausible, change nothing else:

  | Real value class | Placeholder |
  |---|---|
  | kerberos ID | `jdoe` |
  | employee email | `first.last@gs.com` |
  | device / last IP | `10.0.0.1` |
  | device serial | `SN0000000` |
  | book identifier | `EXAMPLEBOOK` |
  | trade identifier | `T0000000` |

- [ ] **Step 4: Run to green.** `./vol exec "python workspace/lint/lint_hardcoded_env.py"` → `EXIT_CODE=0`; the git-grep acceptance line → 0 non-placeholder hits.
- [ ] **Step 5: Commit** — `docs(skills): replace real ids with placeholders; lint pii in skill docs`

---

### Task 6: Delete the wildcard terminal allowlist and whole-drive read grant

**Files:** Modify `ml-vol-estimator.code-workspace` (`:21-26`). Config-only — TDD-exempt.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-6"
goal: "github.copilot.chat.commandAllowlist (terminal:['*']) and github.copilot.chat.additionalReadAccessPaths (['h:/']) removed from ml-vol-estimator.code-workspace with the JSON still parsing and all 43 tasks intact."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section
  - ml-vol-estimator.code-workspace
write_scope:
  - ml-vol-estimator.code-workspace
acceptance_criteria:
  - "git grep -c 'commandAllowlist' -- ml-vol-estimator.code-workspace -> 0"
  - "git grep -c 'additionalReadAccessPaths' -- ml-vol-estimator.code-workspace -> 0"
  - "./vol exec \"python -c \\\"import json; d=json.load(open('ml-vol-estimator.code-workspace')); print(len(d['tasks']['tasks']))\\\"\" -> 43"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "delete the two keys ONLY — do not touch the folders array, the 43 tasks, or any other settings key; do not add replacement auto-approve settings"
context_summary: |
  AW-03 (BLOCKER): the committed workspace file encodes auto-approve-every-terminal-command plus
  whole-H:-drive read intent. HYPOTHESIS note: neither key exists in stock VS Code's settings schema
  (stock silently ignores unknown keys), and whether the GS-internal VS Code fork honors them is
  unverified — DELETION IS SAFE EITHER WAY: stock loses nothing; the fork loses only the unsafe
  wildcard. If narrow terminal auto-approval is wanted later, that is a user-level
  chat.tools.terminal.autoApprove decision, explicitly out of this plan's scope.
depends_on: ["wfo-01-1"]
```

- [ ] **Step 1:** Locate the settings block at `:21-26` (drift check) and delete both keys and their values entirely:
  - `"github.copilot.chat.additionalReadAccessPaths": ["h:/"]`
  - `"github.copilot.chat.commandAllowlist": { "terminal": ["*"] }`

  Fix trailing-comma validity of the surrounding JSON.
- [ ] **Step 2: Run to green.** The three acceptance commands (grep ×2 → 0; JSON parse → 43 tasks).
- [ ] **Step 3: Commit** — `chore(config): remove terminal wildcard allowlist and h: read grant`

---

### Task 7: GSSSO cookie hygiene (AW-33)

**Files:** Modify `skills/GSSSO_AUTH/SKILL.md`. Docs-only — TDD-exempt. The gitignore half of AW-33 (`/workspace/tmp/`) is delivered by wfo-01-2; this task adds the delete-after-use discipline.

**Copilot context packet:**

```yaml
subtask_id: "wfo-01-7"
goal: "skills/GSSSO_AUTH/SKILL.md documents that the SSO cookie file lives under the now-gitignored workspace/tmp/ and MUST be deleted at session end — verified by grep for the new Cookie hygiene section."
file_scope:
  - workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md   # this task section
  - skills/GSSSO_AUTH/SKILL.md
write_scope:
  - skills/GSSSO_AUTH/SKILL.md
acceptance_criteria:
  - "grep -n 'Cookie hygiene' skills/GSSSO_AUTH/SKILL.md -> 1 hit"
  - "grep -n 'delete' skills/GSSSO_AUTH/SKILL.md -> >=1 hit inside the new section"
  - "git check-ignore workspace/tmp/gssso_cookie.txt -> exit 0 (delivered by wfo-01-2; re-verify)"
memory_refs: []
constraints:
  - "verify the cited path:line against the live tree before editing; if moved, locate by content and note the delta"
  - "the 5 research plans in workspace/plans/ are read-only; never touch trials.yaml or workspace/configs/ unless this task names them"
  - "do not change where the cookie is written or the skill's auth flow — documentation note only; if the skill writes the cookie OUTSIDE workspace/tmp/, STOP and return blocked with the actual path"
context_summary: |
  AW-33: the GSSSO skill writes a ~24h firm-wide SSO cookie in plaintext to workspace/tmp/, which was
  not gitignored. wfo-01-2 gitignores /workspace/tmp/; this task adds the handling discipline so the
  cookie is treated as a live credential. Locate the cookie-write documentation by content (search
  the SKILL.md for "cookie" / workspace/tmp mentions).
depends_on: ["wfo-01-2"]
```

- [ ] **Step 1:** In `skills/GSSSO_AUTH/SKILL.md`, directly after the section that documents obtaining/writing the SSO cookie (locate by content), insert:

  ```markdown
  ### Cookie hygiene (HARD)

  The GSSSO cookie is a live firm-wide credential valid ~24h. Rules:
  1. It is written ONLY under `workspace/tmp/` (gitignored — never tracked).
  2. **Delete the cookie file as soon as the authenticated call completes**
     (`Remove-Item` on Windows / `rm` on Linux). Do not leave it for the 24h expiry.
  3. Never copy it elsewhere, print its contents, echo it into logs, or commit it.
  ```

- [ ] **Step 2: Run to green.** The three acceptance commands.
- [ ] **Step 3: Commit** — `docs(skills): gssso cookie hygiene - gitignored tmp, delete after use`

---

## 6. Configs / experiments

None. This plan ships no runnable experiment configs — no `workspace/configs/` file is created or modified (constraint 6 forbids it), and no launch commands exist to print.

---

## 7. Acceptance gate → Plan 02 (Gate A, commands verbatim from 00-overview §2)

All of the following, evidence pasted into the MR description:

1. **User confirms H1** (both PATs revoked) **and H2** (GS notification decision made) — confirmed BEFORE any MR referencing the secrets was pushed.
2. `git check-ignore workspace/config/.env` → exits 0.
3. **PAT-prefix grep = 0 tracked hits:** `git grep -n -e "NzM2" -e "MTQ2" -- ':!workspace/plans/copilot-workflow-overhaul/'` → no output. (The pathspec exclusion exists only because this suite's own plan files cite the sanctioned 4-char fingerprints; run the grep once WITHOUT the exclusion too and confirm every remaining hit is a fingerprint mention inside the plan suite, nothing else.)
4. **`lint_secrets.py` shown red pre-fix → green post-fix:** wfo-01-1's recorded pre-fix failure output AND a final `./vol exec "python workspace/lint/lint_secrets.py"` → `lint_secrets: OK (0 findings)`, `EXIT_CODE=0`.
5. **8/8 TLS clients verify certs:** `git grep -nE 'CERT_NONE|_create_unverified_context|verify=False|verify = False' -- 'skills/'` → no output, and `client.py` `CONFLUENCE_VERIFY_SSL` default reads `"true"`.

Additionally (plan-internal, not gate-blocking for Plan 02): `lint_hardcoded_env.py` red→green evidence recorded; H3/H4/H5 status recorded in the MR as open user actions (AW-01 closes fully only when H3+H4 complete).

**What Plan 02 consumes from this plan:** a secrets-clean tree (its always-on rule edits can be committed without touching credential-bearing lines), the `/workspace/tmp/` gitignore entry, and `lint_secrets.py` in the `LINTS` registry as part of the standing lint context Plan 04 later makes fully green.

---

## 8. Orchestrator prompt

```
/execute Implement Plan 01 (Credential incident & security hardening) from workspace/plans/copilot-workflow-overhaul/plan-01-credential-incident.md

Precondition check (Gate A): ask the user to confirm H1 (BOTH Confluence PATs revoked at
confluence.work.gs.com) and H2 (GS security-notification decision made). If either is
unconfirmed, STOP — do not dispatch any task or push anything. Also confirm no research
/execute session is currently live. Record H3/H4/H5 status for the MR description.
Read workspace/plans/copilot-workflow-overhaul/00-overview.md §5 (shared conventions) first.
Surface note: run Python verification via ./vol on S-B (vol.cmd does not exist until Plan 03).
Branch: chore/wf-overhaul-01-security off master.

Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: wfo-01-1                                  # lint_secrets.py — must record RED on the pre-fix tree
  Wave 2 (parallel, max 6): wfo-01-2, wfo-01-3, wfo-01-4, wfo-01-5, wfo-01-6, wfo-01-7
    # disjoint write_scopes; wfo-01-7 depends_on wfo-01-2 — dispatch it after wfo-01-2 returns complete
Each subagent: TDD where code is touched (show red, then green), terminal isolation + cleanup
(kill_terminal EXIT GATE), return the 00-overview §5.2 return contract verbatim.
Retry a blocked/partial subagent once with a refined packet, then escalate with both attempts' evidence.

Integration verification (orchestrator, after all tasks):
  git check-ignore workspace/config/.env                                    -> exit 0
  git grep -n -e "NzM2" -e "MTQ2" -- ':!workspace/plans/copilot-workflow-overhaul/'  -> no output
  ./vol exec "python workspace/lint/lint_secrets.py"                        -> OK (0 findings), EXIT_CODE=0
  ./vol exec "python workspace/lint/lint_hardcoded_env.py"                  -> EXIT_CODE=0
  git grep -nE 'CERT_NONE|_create_unverified_context|verify=False|verify = False' -- 'skills/'  -> no output
Paste wfo-01-1's pre-fix RED output and these GREEN outputs into the MR description
(masked tokens only — never a raw value). Rebase onto origin/master, push, open the MR
(human-generic title; AW-IDs in the description only).
Update workspace/research/weekly-progress.md (Shipped section, one line).
Do NOT start Plan 02.
```
