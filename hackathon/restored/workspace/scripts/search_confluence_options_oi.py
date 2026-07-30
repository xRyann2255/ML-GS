"""Search Confluence + EngHub for ISG OptionMetrics dataset names.

Searches:
1. Confluence CQL — "OptionMetrics", "IvyDB", "options open interest",
   "ISG options", "gamma exposure", "OPRA" in MARQUEE/EQT/EQS/ISG spaces
2. Known Confluence pages about Marquee datasets (IDs from prior research)

Output: workspace/tmp/confluence_optionmetrics_search.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "CONFLUENCE" / "src"))

OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "confluence_optionmetrics_search.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


def main() -> None:
    from client import ConfluenceClient

    client = ConfluenceClient.from_env()

    if not client.is_connected():
        log("ERROR: Confluence PAT expired or not configured.")
        log("Generate at: https://confluence.work.gs.com/plugins/personalaccesstokens/usertokens.action")
        OUT_FILE.write_text("\n".join(results))
        return

    log("Confluence connected ✓")

    # -----------------------------------------------------------------------
    # Search queries — find pages about options OI data, OptionMetrics, IvyDB
    # -----------------------------------------------------------------------
    search_queries = [
        # Direct OptionMetrics / IvyDB references
        'type=page AND text~"OptionMetrics"',
        'type=page AND text~"IvyDB"',
        'type=page AND text~"ISG" AND text~"option"',

        # Options open interest in Marquee/EQT spaces
        'type=page AND space=MARQUEE AND text~"open interest"',
        'type=page AND space=EQT AND text~"open interest"',
        'type=page AND space=EQS AND text~"open interest"',

        # Gamma / GEX references
        'type=page AND text~"gamma exposure" AND text~"SPX"',
        'type=page AND text~"GEX" AND text~"option"',
        'type=page AND text~"dealer gamma"',

        # Options data in Marquee
        'type=page AND space=MARQUEE AND text~"options" AND text~"dataset"',
        'type=page AND space=MARQUEE AND text~"OPRA"',

        # ISG data services
        'type=page AND text~"ISG" AND text~"data" AND text~"options"',
        'type=page AND text~"ISG" AND text~"OptionMetrics"',

        # Quantum / data catalog for options
        'type=page AND text~"Quantum" AND text~"options"',
        'type=page AND text~"data catalog" AND text~"options"',

        # Per-strike data patterns
        'type=page AND text~"per-strike" AND text~"open interest"',
        'type=page AND text~"strike" AND text~"OI" AND text~"SPX"',

        # Options volume data
        'type=page AND space=MARQUEE AND text~"options volume"',
        'type=page AND space=EQT AND text~"options" AND text~"greeks"',

        # CBOE options data
        'type=page AND text~"CBOE" AND text~"open interest"',
        'type=page AND text~"CBOE" AND text~"options data"',

        # Broad options dataset search
        'type=page AND space=MARQUEE AND title~"option"',
        'type=page AND space=EQT AND title~"option" AND title~"data"',
    ]

    section("CONFLUENCE SEARCH RESULTS")

    seen_ids = set()
    all_hits = []

    for query in search_queries:
        try:
            result = client.search(query)
            if result.get("success") and result.get("count", 0) > 0:
                log(f"\n--- Query: {query}")
                log(f"    Hits: {result['count']}")
                for page in result.get("pages", [])[:8]:
                    pid = page.get("id", "?")
                    title = page.get("title", "?")
                    url = page.get("url", "")
                    space = page.get("_meta", {}).get("space", "?")
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        all_hits.append(page)
                        log(f"    [{space}] {title}")
                        log(f"         ID={pid}  URL={url}")
        except Exception as e:
            log(f"    ERROR on query '{query[:50]}...': {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # Read the known "Data Vertical: Equity Volatility" page (ID 582304966)
    # which we already know lists EDRVS datasets
    # -----------------------------------------------------------------------
    section("KNOWN MARQUEE DATA PAGES — Reading for Options OI References")

    known_pages = [
        ("582304966", "Data Vertical: Data Services Equity Volatility"),
        ("373812842", "Data Product: GS Equity Variance Swap Levels"),
    ]

    for page_id, desc in known_pages:
        log(f"\n--- Page {page_id}: {desc}")
        try:
            page = client.get_page_by_id(page_id)
            if page and "body" in page:
                body = page["body"]
                # Search for OI/options/OptionMetrics references in body
                keywords = ["open interest", "OptionMetrics", "IvyDB", "OPRA",
                           "per-strike", "greeks", "gamma", "options chain",
                           "option chain", "ISG", "OI"]
                for kw in keywords:
                    if kw.lower() in body.lower():
                        # Extract context around the keyword
                        idx = body.lower().find(kw.lower())
                        snippet = body[max(0, idx-100):idx+200]
                        # Clean HTML
                        import re
                        snippet = re.sub(r'<[^>]+>', ' ', snippet)
                        snippet = ' '.join(snippet.split())[:200]
                        log(f"    Found '{kw}': ...{snippet}...")
            else:
                log(f"    Could not read page (no body)")
        except Exception as e:
            log(f"    ERROR reading page {page_id}: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # Look for child pages under the Data Vertical page
    # -----------------------------------------------------------------------
    section("CHILD PAGES OF MARQUEE DATA VERTICAL")

    try:
        children = client.get_child_pages("582304966")
        if children:
            for child in children[:20]:
                title = child.get("title", "?")
                pid = child.get("id", "?")
                log(f"    {title} (ID={pid})")
    except Exception as e:
        log(f"    ERROR: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    section("SUMMARY")
    log(f"  Total unique pages found: {len(all_hits)}")
    log("")
    log("  TOP CANDIDATES (pages most likely to contain OI dataset info):")
    for page in all_hits[:15]:
        title = page.get("title", "?")
        space = page.get("_meta", {}).get("space", "?")
        pid = page.get("id", "?")
        log(f"    [{space}] {title} (ID={pid})")

    # Write results
    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\n  Results saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
