"""Read the key ISG OptionMetrics Confluence pages to get dataset names & API details.

Pages to read:
1. ISG Option Metrics Data Loader API (ID=811415159)
2. ISG Option Metrics PrestoDB Integration (ID=925556743)
3. ISG- QUANTUM | NOTES (ID=4872885335)
4. IVYDB Options Feed (ID=339160620)
5. GS IvyDB Implementation (ID=4334923178)
6. GDD ISG CSI Options Data Contract (ID=337595676)
7. Investment Strategy Group | Quantum Dependancy (ID=2318725392)
8. OPRA page in EQUITIES space (ID=6219849137)

Output: workspace/tmp/confluence_isg_pages_content.txt
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "CONFLUENCE" / "src"))

OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "confluence_isg_pages_content.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


def clean_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_relevant_sections(body: str, keywords: list[str], context_chars: int = 500) -> list[str]:
    """Extract text sections around keyword matches."""
    clean = clean_html(body)
    sections = []
    seen_positions = set()
    for kw in keywords:
        for match in re.finditer(re.escape(kw), clean, re.IGNORECASE):
            pos = match.start()
            # Dedup overlapping sections
            bucket = pos // (context_chars // 2)
            if bucket in seen_positions:
                continue
            seen_positions.add(bucket)
            start = max(0, pos - context_chars // 2)
            end = min(len(clean), pos + context_chars)
            sections.append(f"  ...{clean[start:end]}...")
    return sections[:10]  # Cap at 10 sections per page


def main() -> None:
    from client import ConfluenceClient

    client = ConfluenceClient.from_env()

    if not client.is_connected():
        log("ERROR: Confluence PAT expired or not configured.")
        OUT_FILE.write_text("\n".join(results))
        return

    log("Confluence connected ✓")

    pages_to_read = [
        ("811415159", "ISG Option Metrics Data Loader API"),
        ("925556743", "ISG Option Metrics PrestoDB Integration"),
        ("4872885335", "ISG- QUANTUM | NOTES"),
        ("339160620", "IVYDB Options Feed"),
        ("4334923178", "GS IvyDB Implementation"),
        ("337595676", "GDD ISG CSI Options Data Contract"),
        ("2318725392", "Investment Strategy Group | Quantum Dependancy"),
        ("6219849137", "OPRA (EQUITIES space)"),
        ("1448101188", "Ivy (FDS space)"),
        ("5097685559", "Access/Entitlements need for ISG"),
    ]

    keywords = [
        "open interest", "OI", "greeks", "delta", "gamma", "vega",
        "strike", "SPX", "option", "dataset", "table", "schema",
        "PrestoDB", "Presto", "Quantum", "API", "endpoint",
        "entitlement", "access", "permission",
        "IvyDB", "OptionMetrics", "IVYUS", "IVYDB",
        "per-strike", "chain", "expiry", "expiration",
        "Marquee", "TSDB", "Chunk Store",
    ]

    for page_id, desc in pages_to_read:
        section(f"PAGE: {desc} (ID={page_id})")
        try:
            page = client.get_page_by_id(page_id)
            if page and "body" in page:
                body = page["body"]
                full_text = clean_html(body)

                # Print first 2000 chars for overview
                log(f"  Title: {page.get('title', '?')}")
                log(f"  Space: {page.get('_meta', {}).get('space', '?')}")
                log(f"  Length: {len(full_text)} chars")
                log("")
                log("  === FULL TEXT (first 3000 chars) ===")
                log(full_text[:3000])
                log("")

                # Also show keyword-relevant sections if page is long
                if len(full_text) > 3000:
                    log("  === KEYWORD MATCHES (deeper in page) ===")
                    sections = extract_relevant_sections(body, keywords, 400)
                    for s in sections:
                        log(s)
            else:
                log(f"  Could not read page body")
        except Exception as e:
            log(f"  ERROR: {str(e)[:200]}")

    # Write results
    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\nResults saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
