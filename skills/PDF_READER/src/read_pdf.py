"""
read_pdf.py — Extract text from a PDF file.

Usage (CLI):
    python read_pdf.py <path.pdf> [--pages 1,2,3] [--out <output.txt>] [--json]

Usage (library):
    from read_pdf import read_pdf, read_pdf_pages
    text = read_pdf("report.pdf")
    pages = read_pdf_pages("report.pdf", pages=[1, 2])
"""

from __future__ import annotations

import argparse
import atexit
import io
import json
import os
import sys
from pathlib import Path
from typing import List, Optional


def read_pdf(
    path: str | Path,
    *,
    pages: Optional[List[int]] = None,
) -> str:
    """Return concatenated text from a PDF.

    Args:
        path:  Path to the PDF file.
        pages: 1-based page numbers to extract. ``None`` = all pages.

    Returns:
        Extracted text (pages separated by ``\\n\\n``).
    """
    results = read_pdf_pages(path, pages=pages)
    return "\n\n".join(r["text"] for r in results)


def read_pdf_pages(
    path: str | Path,
    *,
    pages: Optional[List[int]] = None,
) -> List[dict]:
    """Return per-page text as a list of dicts.

    Each dict: ``{"page": <1-based>, "chars": <int>, "text": <str>}``
    """
    from pypdf import PdfReader  # lazy import — fail fast with clear message

    reader = PdfReader(str(path))
    total = len(reader.pages)

    if pages is None:
        indices = range(total)
    else:
        indices = [p - 1 for p in pages if 1 <= p <= total]

    results: List[dict] = []
    for i in indices:
        text = reader.pages[i].extract_text() or ""
        results.append({"page": i + 1, "chars": len(text), "text": text})
    return results


def pdf_metadata(path: str | Path) -> dict:
    """Return basic PDF metadata (page count, title, author, etc.)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    meta = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "title": getattr(meta, "title", None),
        "author": getattr(meta, "author", None),
        "subject": getattr(meta, "subject", None),
        "creator": getattr(meta, "creator", None),
    }


# ------------------------------------------------------------------ #
#  CLI                                                                 #
# ------------------------------------------------------------------ #

def _apply_args_file(positional_keys=None):
    """If --args-file in argv, load JSON and rebuild argv as CLI flags."""
    if "--args-file" not in sys.argv:
        return
    idx = sys.argv.index("--args-file")
    path = sys.argv[idx + 1]
    with open(path, "r", encoding="utf-8") as f:
        af = json.load(f)
    argv = [sys.argv[0]]
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


def _cli() -> None:
    _apply_args_file(["pdf", "pdf_path"])
    parser = argparse.ArgumentParser(description="Extract text from a PDF file.")
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument(
        "--pages",
        default=None,
        help="Comma-separated 1-based page numbers (default: all)",
    )
    parser.add_argument("--out", default=None, help="Write output to file instead of stdout")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON (per-page)")
    parser.add_argument("--meta", action="store_true", help="Print PDF metadata and exit")
    parser.add_argument("--out-file", default=None, metavar="PATH",
                        help="Write output to this file (alias for --out)")
    args = parser.parse_args()
    if args.out_file and not args.out:
        args.out = args.out_file

    path = Path(args.pdf)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    if args.meta:
        print(json.dumps(pdf_metadata(path), indent=2))
        return

    page_list: Optional[List[int]] = None
    if args.pages:
        page_list = [int(p.strip()) for p in args.pages.split(",")]

    if args.as_json:
        result = read_pdf_pages(path, pages=page_list)
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        output = read_pdf(path, pages=page_list)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out} ({len(output)} chars)")
    else:
        sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    _cli()
