# Research

Source material for the LaTeX study guide. Nothing here is read by the LaTeX build directly — this is the raw input that Claude and I work from when writing chapters.

## Layout

- **`bibliography.md`** — the master annotated reading list produced by the deep-research prompt in `../RESEARCH_PROMPT.md`. This is the canonical index of everything we have decided to use. If a resource is not listed here, it is not considered a source for the PDF.
- **`papers/`** — PDFs of foundational papers (Kyle 1985, Glosten–Milgrom 1985, Almgren–Chriss 2000, Avellaneda–Stoikov 2008, etc.). Filename convention: `Author_Year_ShortTitle.pdf`.
- **`writeups/`** — Prosperity competition post-mortems from past years beyond the Frankfurt Hedgehogs writeup that already lives in `../imc-prosperity-3/`. One folder per team/year.
- **`books/`** — Book chapters or excerpts (PDF). Full books kept out of the repo for size/licensing reasons — link to them from `bibliography.md` instead.
- **`code/`** — Reference implementations, example notebooks, open-source backtesters, reusable snippets. Read-only with respect to the LaTeX build.
- **`notes/`** — My own scratch notes while reading. These feed into the LaTeX chapters later.

## Update rule

Every time a new source is added to `papers/`, `writeups/`, `books/`, or `code/`, add or update the corresponding entry in `bibliography.md` so the index stays authoritative.
