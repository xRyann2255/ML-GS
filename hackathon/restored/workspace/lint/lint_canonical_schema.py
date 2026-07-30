"""
lint_canonical_schema.py — canonical YAML + instruction-doc completeness vs live
registries (AW-20/G23/G24/G25 lint half).

Rules:
  C1. Every @register_model("<key>") and @register_feature_layer("<key>") in
      src/volforecast/**/*.py appears as a token in BOTH
      workspace/configs/_CANONICAL_EXAMPLE.yaml and
      .github/instructions/yaml-config.instructions.md.
  C2. Every sequences 'source' enum literal in src/volforecast/config.py
      appears in both docs; so do the schema fields in EXTRA_FIELDS.
Registry keys come from REGEX over source text — never import volforecast
(heavy/optional deps; lints must run env-independent).
Whitelist: whitelists/canonical_schema.txt grandfathers pre-Plan-06 gaps.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL = REPO_ROOT / "workspace" / "configs" / "_CANONICAL_EXAMPLE.yaml"
DOC = REPO_ROOT / ".github" / "instructions" / "yaml-config.instructions.md"
WHITELIST = Path(__file__).resolve().parent / "whitelists" / "canonical_schema.txt"
REGISTER = re.compile(r'@register_(?:model|feature_layer)\(\s*"([\w-]+)"\s*\)')
SOURCE_ENUM = re.compile(r'"(parquet[\w]*|daily_lookback)"')
# Fields the audit proved live in config.py but missing from the docs (AW-G24/G25):
EXTRA_FIELDS = ["conditional_duan", "feature_selection", "blend",
                "n_splits", "embargo", "bar_interval", "lookback_days"]


def load_whitelist() -> set[str]:
    if not WHITELIST.is_file():
        return set()
    return {ln.strip() for ln in WHITELIST.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def main() -> int:
    wl = load_whitelist()
    src_dir = REPO_ROOT / "src" / "volforecast"
    keys: set[str] = set()
    for py in sorted(src_dir.rglob("*.py")):
        keys |= set(REGISTER.findall(py.read_text(encoding="utf-8", errors="replace")))
    config_py = (src_dir / "config.py").read_text(encoding="utf-8", errors="replace")
    enum_vals = set(SOURCE_ENUM.findall(config_py))
    if not keys:
        print("  ERROR [parse] zero registry keys extracted — REGISTER regex drifted")
        return 1
    canonical = CANONICAL.read_text(encoding="utf-8", errors="replace")
    doc = DOC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for token in sorted(keys | enum_vals | set(EXTRA_FIELDS)):
        for label, text in (("canonical", canonical), ("instruction-doc", doc)):
            if not re.search(rf"\b{re.escape(token)}\b", text):
                key = f"{label}:{token}"
                if key not in wl:
                    errors.append(f"[schema-gap] '{token}' missing from the {label} "
                                  f"({CANONICAL.name if label == 'canonical' else DOC.name})")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    print(f"PASS: {len(keys)} registry keys + {len(enum_vals)} enum values + "
          f"{len(EXTRA_FIELDS)} schema fields present in both docs "
          f"({len(wl)} grandfathered until Plan 06).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
