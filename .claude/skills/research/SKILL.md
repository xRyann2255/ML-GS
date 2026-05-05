---
name: research
description: Parallel 3-agent research pipeline for the ML vol project. Searches internal notes, reference papers, and web simultaneously, then synthesizes findings.
---

# Research

Run a parallel research pipeline on a given topic, combining internal knowledge, paper references, and web sources.

## Input

The user specifies a research query, e.g.:
- "research QLIKE loss function properties"
- "research Oxford-Man vs VOLARE data availability"
- "research GNN approaches to covariance forecasting"

## Execution

Dispatch three sub-agents in parallel (single message, three Agent tool calls):

### Agent 1 — Internal Search

Prompt:

> Search the ML-GS repository for existing coverage of "[query]". Check:
> - `notes/volatility.md` — the main scoping document
> - `reference/project-papers/README.md` — the paper index
> - Any existing guide chapters in `guides/ml-finance/chapters/` and `guides/quant-trading/chapters/`
> - `notes/` for any other relevant files
>
> Report what we already know about this topic, with file paths and line numbers. Be specific — quote relevant passages. Under 300 words.

### Agent 2 — Paper Search

Prompt:

> Search PDF files in `reference/project-papers/` and `reference/papers/` for content related to "[query]". Read relevant papers and extract:
> - Key methodology details
> - Empirical results and findings
> - Contradictions between papers
> - Specific numbers, tables, or formulas relevant to the query
>
> Report findings with paper names and specific details. Under 400 words.

### Agent 3 — Web Search

Prompt:

> Search the web for recent information (post-2023) about "[query]" in the context of realized volatility forecasting and financial ML. Look for:
> - Recent papers (arXiv, SSRN)
> - Open-source implementations (GitHub repos)
> - Data sources and availability
> - Blog posts or tutorials from practitioners
>
> Focus on actionable information: things we could use, cite, or build on. Under 300 words.

## Synthesis (main agent, after all 3 complete)

Combine the three reports into a single structured brief:

```
## Topic: [query]

### What We Already Have
- [existing coverage in notes/guides]

### From Papers
- [key findings from reference PDFs]

### From Web
- [recent developments, repos, data sources]

### Synthesis
- [how findings connect, contradictions, confidence levels]

### Project Relevance
- [how this affects our direction/methodology choices]

### Suggested Next Steps
- [concrete actions based on findings]
```

Present the brief to the user. Do NOT automatically save it — let the user decide if it should go into notes.
