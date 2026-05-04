#!/usr/bin/env bash
# latex/build.sh — one-shot build for the quant textbook PDF.
# Runs pdflatex twice (+ bibtex) so TOC and citations resolve.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p out

# Stage the local references.bib alongside the aux file so bibtex, which
# runs in out/, reads our copy instead of an unrelated bundled
# references.bib that lives somewhere in MiKTeX's TEXMF tree. Without
# this, MiKTeX's kpsewhich picks up the bundled copy first and reports
# "I didn't find a database entry" for perfectly valid entries.
cp references.bib out/references.bib

PDFLATEX_OPTS="-halt-on-error -interaction=nonstopmode -file-line-error -output-directory=out"

echo "[1/4] pdflatex pass 1..."
pdflatex $PDFLATEX_OPTS main.tex > out/pass1.log 2>&1 || {
  echo "FAIL: pdflatex pass 1 failed. See out/pass1.log" >&2
  tail -40 out/pass1.log >&2
  exit 1
}

echo "[2/4] bibtex..."
(cd out && bibtex main > bibtex.log 2>&1) || {
  echo "WARN: bibtex reported issues (may be OK if no citations yet). See out/bibtex.log" >&2
  cat out/bibtex.log >&2 || true
}

echo "[3/4] pdflatex pass 2..."
pdflatex $PDFLATEX_OPTS main.tex > out/pass2.log 2>&1 || {
  echo "FAIL: pdflatex pass 2 failed. See out/pass2.log" >&2
  tail -40 out/pass2.log >&2
  exit 1
}

echo "[4/4] pdflatex pass 3 (resolve refs)..."
pdflatex $PDFLATEX_OPTS main.tex > out/pass3.log 2>&1 || {
  echo "FAIL: pdflatex pass 3 failed. See out/pass3.log" >&2
  tail -40 out/pass3.log >&2
  exit 1
}

if [[ -f out/main.pdf ]]; then
  cp out/main.pdf main.pdf
  PAGES=$(pdfinfo main.pdf 2>/dev/null | awk '/^Pages:/ {print $2}')
  SIZE=$(stat -c%s main.pdf 2>/dev/null || stat -f%z main.pdf)
  echo "SUCCESS: main.pdf built (${PAGES:-?} pages, ${SIZE} bytes)"
else
  echo "FAIL: main.pdf not produced" >&2
  exit 1
fi
