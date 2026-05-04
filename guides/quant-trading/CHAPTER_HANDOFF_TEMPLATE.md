# Chapter Handoff — Ch NN: {Title}

**Model to use:** Claude Opus 4.6 (`claude-opus-4-6`). Mandatory per design spec §9.

**Spec:** `docs/superpowers/specs/2026-04-11-quant-textbook-design.md` §7, Ch NN entry.

**Target file:** `latex/chapters/chNN_name.tex`

## The style to match — NLP revision notes

This book is modelled on the NLP revision notes at `example-notes/NLP_NOTES.pdf`. Read the first 8 pages and pages 90–96 of that PDF before writing to see the reference style in action. The format is **textbook / revision-notes hybrid**, not continuous-prose academic monograph:

- **Heavy use of coloured callout boxes** throughout every chapter — the visual identity is "clean serif prose interrupted by prominent coloured boxes," not wall-of-text.
- **Worked numerical examples are first-class content**, often broken into numbered subsections with underbrace-annotated equations. Hard concepts open with a toy example *before* any formalism.
- **Condensed, direct prose.** No motivational fluff, no throat-clearing. Every paragraph earns its place.
- **Prerequisites stated explicitly** at the start of most chapters (a `backgroundbox`).
- **Key results highlighted in boxes** rather than buried in prose.
- **Common mistakes highlighted in red** so they can't be missed.
- **Chapter ends with a summary** — either a bulleted "Key facts to memorise" list or a short prose summary.

## Callout box palette — use these liberally

Defined in `latex/conventions.tex`. Match the NLP notes' box-heavy rhythm: roughly one box per 2–3 pages on average is a reasonable minimum for a content chapter.

- **`\begin{backgroundbox}[Prerequisites]`** (gray). Use at the start of most chapters (not front matter) to list what the reader should know from earlier chapters before proceeding. Short bulleted list is ideal. Optional custom title via the first argument.
- **`\begin{keyfactbox}[Key fact]`** (blue). Formal results worth highlighting and remembering. Use for statements like "The CDS par spread equals the expected discounted loss" or "Impact scales as $\sqrt{Q}$, not $Q$." Not a theorem — a crisp statement. Optional custom title ("Theorem", "Result", "Complexity", "Formula").
- **`\begin{intuitionbox}`** (green). Plain-English restatement of what a formal result *means* after a derivation. When the reader has followed the algebra but isn't sure what was shown, the intuition box is the answer. Use at least once per major result.
- **`\begin{prosperitybox}`** (orange). A worked example using a specific Prosperity product from a prior year of the competition. Use in Parts I–V only (Part VI has its own dedicated playbook). Tie the theory directly to a concrete Prosperity product whenever one exists.
- **`\begin{gsbox}`** (teal). A note on how the technique is actually used on a sell-side Goldman Sachs desk: what the Strat typically writes, which system owns the calculation, what the trader asks for. Use in Parts IV and V, and anywhere the bridge to the production sell-side world is instructive.
- **`\begin{pitfallbox}[Common mistake]`** (red). A wrong intuition that sounds right, a failure mode the reader will otherwise walk into, or a subtle trap. These are the highest-value-per-word boxes in the book. Use them whenever something would cost the reader money or time to figure out the hard way. Optional custom title ("Don't confuse X and Y", "Watch out for Z").
- **`\begin{historybox}`** (purple). Origin story, biographical note, or how a particular model came to dominate practice. Use sparingly — these are for colour, not content. Skippable on a first read.

## Theorem environments (from `conventions.tex`)

- `\begin{definition}...\end{definition}` — term introductions. Use when formally defining a technical term for the first time.
- `\begin{theorem}...\end{theorem}` / `proposition` / `lemma` / `corollary` — formal results with proofs. Proofs in `\begin{proof}...\end{proof}`.
- `\begin{example}...\end{example}` — formally-numbered worked examples (different from a prose worked example; use this for short standalone examples that get referenced elsewhere).
- `\begin{remark}...\end{remark}` — formal asides.

## Non-negotiable writing rules

1. **Zero finance assumed.** Every term defined on first use. No jargon the reader hasn't already seen earlier in the book.
2. **Rigour level B.** Derive results where the derivation teaches; state with citation where it does not. No proofs dropped from the sky; no algebra for its own sake.
3. **Code density A.** At most one clean reference implementation per strategy (~15–30 lines). No backtester code in the PDF. No plotting code.
4. **Intuition-first for hard chapters.** If this chapter is flagged as hard (Ch 5, 8, 15, 22, 29), open with a worked toy numerical example *before* any formalism. Match the "Viterbi worked example" style from `example-notes/NLP_NOTES.pdf` pages 92–95: concrete inputs, step-by-step numbered subsections, underbrace-annotated equations, a final summary table, closing intuition box.
5. **No filler.** Every paragraph must define a term, derive a result, give a worked example, contrast a wrong intuition, or cross-link to another chapter. If a paragraph doesn't do one of those, cut it.
6. **Every symbol declared in `latex/conventions.tex`.** Do not redefine. If you need a new symbol, add it to `conventions.tex` and list it in this handoff's "symbol additions" section.
7. **Cite inline using the `\citeX` macros from `conventions.tex`.** Every factual claim traces to a source in `latex/references.bib`.
8. **Compile clean.** Run `bash latex/build.sh` before declaring the chapter done. No errors. Warnings about undefined citations are acceptable only if you added a new `references.bib` entry that hasn't been committed yet.

## Recommended chapter skeleton

Every content chapter (not front matter) should follow roughly this shape:

1. **Opening motivation** (half a page). What question does this chapter answer? Why does the reader care? Sometimes a one-paragraph concrete scenario works well — "Imagine you're the market maker quoting RAINFOREST_RESIN at 10,000 and..."
2. **`\begin{backgroundbox}[Prerequisites]`** listing the specific earlier-chapter results assumed. Crosslink via `\cref{ch:xxx}`.
3. **Main content**, broken into `\section` and `\subsection` units. Use the callout boxes liberally as you go.
4. **Worked example(s)**: for hard chapters, a fully worked toy example with real numbers — use numbered `\subsection`s for each step.
5. **Reference implementation** (optional, sparing): one short `lstlisting` block of Python if the chapter teaches a strategy. No more than ~30 lines.
6. **Summary / Key facts** at the end — either a `keyfactbox` with the 4–8 most important takeaways, or a bulleted list section titled "Key facts to memorise" in the NLP-notes style.

## Local source materials

Files to read for this chapter (listed in the plan's Task N entry):

- `research/books/<book>.pdf` — pages X–Y for topic T
- `research/papers/<paper>.pdf` — full
- `research/papers/<blog>.md` — full
- `research/writeups/<repo>/README.md` — section S
- `prosperity-wiki/<file>.md` — if Prosperity-relevant

Read files locally; avoid WebFetch unless a specific citation is missing from disk.

## What to produce

The body of `latex/chapters/chNN_name.tex`, starting after the existing `\chapter{...}` and `\label{...}` lines already in the stub. Replace the placeholder `\textit{This chapter is a stub...}` line with the full chapter content.

## Deliverables checklist

- [ ] `latex/chapters/chNN_name.tex` body written (typically 15–30 pages of output for a content chapter).
- [ ] At least one `backgroundbox` near the chapter start (content chapters only, not front matter).
- [ ] Multiple callout boxes throughout — aim for roughly one box per 2–3 pages minimum, distributed across the box palette where appropriate.
- [ ] At least one `keyfactbox` or numbered theorem highlighting each major result.
- [ ] At least one `intuitionbox` restating each major result in plain English.
- [ ] For hard chapters: a concrete toy worked example opens the hard-concept section, *before* formalism.
- [ ] Summary or "Key facts to memorise" at the end.
- [ ] Every symbol used declared in `conventions.tex` (add new ones if needed and note them below).
- [ ] Every citation traces to a real entry in `references.bib` (add new `.bib` entries if needed and note them below).
- [ ] Ran `bash latex/build.sh` — compiles clean.
- [ ] Ran a final self-review: no placeholder sentences, no undefined jargon, hard concepts have toy examples first, boxes are being used at the NLP-notes rhythm (not once per chapter — many per chapter).

## Symbol additions (if any)

*List any new `\newcommand` lines added to `conventions.tex` during writing.*

## References additions (if any)

*List any new `.bib` entries added to `references.bib` during writing.*
