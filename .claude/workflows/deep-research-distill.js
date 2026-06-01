export const meta = {
  name: 'deep-research-distill',
  description: 'One question in: sweep the internet (arXiv/SSRN papers, GitHub repos, practitioner web), adversarially verify, and distill into this repo as a direct answer + key insights + an ingest list',
  whenToUse: 'When you want to deeply research one question by harvesting external sources and persisting a verified, distilled brief into notes/deep-research/. Pass args="the question" or args={question, slug}.',
  phases: [
    { title: 'Scope', detail: 'read the local corpus + decompose the question into source-typed search facets' },
    { title: 'Harvest', detail: 'parallel agents sweep arXiv/SSRN, GitHub, and practitioner web per facet' },
    { title: 'Verify', detail: 'adversarially ground the top claims against their sources; dedup; rate credibility' },
    { title: 'Distill', detail: 'synthesize the direct answer + evidence table + ingest list and write it into the repo' },
  ],
}

// ---- Inputs (args is a string question, or {question, slug, depth}) ----
// Be robust to args arriving as a JSON-encoded string (the harness sometimes stringifies object args).
let A = args
if (typeof A === 'string' && A.trim().startsWith('{')) {
  try { A = JSON.parse(A) } catch (e) { /* not JSON — treat as a plain question string */ }
}
const isObj = A && typeof A === 'object'
const Q = (isObj ? A.question : A) || ''
if (!Q.trim()) {
  throw new Error('deep-research-distill needs a question. Pass args="your question" or args={question:"...", slug:"2026-05-31-topic"}.')
}
const SLUG = (isObj && A.slug) || 'research'
const DEPTH = (isObj && A.depth) || 'standard'   // 'standard' (~15 verified sources) | 'deep' (~25)
const TOP_N = DEPTH === 'deep' ? 25 : 15
const OUT = `notes/deep-research/${SLUG}.md`

// >>> DR-DISTILL HELPERS (mirror of __tests__/dr-distill-helpers.test.mjs) >>>
// Pure, dependency-free helpers shared with .claude/workflows/deep-research-distill.js.
// EDIT HERE ONLY. Task 7 mirrors this block verbatim into the workflow.

function deriveYear(slug, fallback) {
  const m = String(slug || '').match(/(20\d{2})/)
  const year = m ? m[1] : (fallback || '2025')
  const prevYear = String(Number(year) - 1)
  return { year, prevYear }
}

function tierWeight(credibility) {
  switch (credibility) {
    case 'peer-reviewed': return 1.0
    case 'preprint': return 0.8
    case 'practitioner': return 0.5
    default: return 0.6
  }
}

function scoreSource(relevance, credibility) {
  return (Number(relevance) || 0) * tierWeight(credibility)
}

function harvestTierWeight(type) {
  switch (type) {
    case 'paper': return 1.0
    case 'repo': return 0.8
    case 'dataset': return 0.7
    case 'docs': return 0.6
    case 'blog': return 0.5
    default: return 0.5
  }
}

const STOPWORDS = new Set(['a','an','the','of','for','and','or','to','in','on','with','via','using','at','by'])

function slugifyWords(text, maxWords) {
  return String(text || '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(w => w && !STOPWORDS.has(w))
    .slice(0, maxWords)
    .join('-')
}

function firstAuthorLast(authors) {
  const first = String(authors || '').split(/,|;|&|\band\b/)[0].trim()
  const parts = first.split(/\s+/).filter(Boolean)
  const last = parts.length ? parts[parts.length - 1] : ''
  return last.toLowerCase().replace(/[^a-z0-9]/g, '') || 'unknown'
}

function paperSlugName(authors, year, title) {
  const a = firstAuthorLast(authors)
  const y = (String(year || '').match(/20\d{2}/) || ['nd'])[0]
  const t = slugifyWords(title, 4) || 'paper'
  return `${a}-${y}-${t}.pdf`
}

function extractArxivId(text) {
  const m = String(text || '').match(/(\d{4}\.\d{4,5})/)
  return m ? m[1] : null
}

function normalizeTitle(t) {
  return String(t || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

function authorYearFromFilename(filename) {
  const m = String(filename || '').match(/^([a-z0-9]+)-(20\d{2})/i)
  return m ? `${m[1].toLowerCase()}-${m[2]}` : null
}

function authorYearKey(authors, year) {
  const y = (String(year || '').match(/20\d{2}/) || [''])[0]
  return `${firstAuthorLast(authors)}-${y}`
}

function isAlreadyHave(candidate, alreadyHave) {
  const list = Array.isArray(alreadyHave) ? alreadyHave : []
  const candId = extractArxivId(candidate.url) || extractArxivId(candidate.codeLink) || extractArxivId(candidate.title)
  const candTitle = normalizeTitle(candidate.title)
  const candKey = authorYearKey(candidate.authors, candidate.year)
  return list.some(h => {
    if (candId && h.id && extractArxivId(h.id) === candId) return true
    if (candTitle && h.title && normalizeTitle(h.title) === candTitle) return true
    const hKey = h.authorYear || authorYearFromFilename(h.filename)
    if (candKey && hKey && hKey === candKey && /-20\d{2}$/.test(candKey)) return true
    return false
  })
}

function arxivPdfUrl(urlOrId) {
  const id = extractArxivId(urlOrId)
  return id ? `https://arxiv.org/pdf/${id}` : null
}

function looksLikePdf(headerText) {
  return typeof headerText === 'string' && headerText.startsWith('%PDF')
}

function dateBiasedQueries(queries, year, prevYear) {
  const base = Array.isArray(queries) ? queries : []
  const out = [...base]
  for (const q of base) {
    out.push(`${q} ${year}`)
    out.push(`${q} ${prevYear} ${year}`)
  }
  if (base.length) out.push(`latest ${base[0]} state of the art ${year}`)
  return Array.from(new Set(out))
}

function buildReadmeRow(num, paperLabel, filename, status) {
  const st = status === 'Essential' ? '**Essential**' : 'Recommended'
  return `| ${num} | ${paperLabel} | \`${filename}\` | ${st} |`
}

function buildStillNeededLine(paperLabel) {
  return `- ${paperLabel}`
}
// <<< DR-DISTILL HELPERS <<<

const BASELINE_YEAR = '2026'
const { year: YEAR, prevYear: PREV_YEAR } = deriveYear(SLUG, BASELINE_YEAR)

const CONTEXT = `
PROJECT: Goldman Sachs ML internship — forecasting REALIZED VOLATILITY. Research-first repo (notes, papers, LaTeX guides). Modeling/data live on a SEPARATE machine; THIS repo synthesizes knowledge. Evaluation vocabulary: QLIKE (primary), MSE, Diebold-Mariano, Model Confidence Set, purged k-fold CV. Baselines: HAR, HAR-J/CJ, SHAR, HARQ, Realized GARCH, Ridge/Lasso-HAR. The user is a sophisticated quant who wants rigour over hype, quantitative framing (bps QLIKE deltas, Sharpe), honest "where ML wins vs loses", and zero fluff.

RESEARCH LENS: Prioritise the CURRENT STATE OF THE ART and the methodologies in ACTIVE USE TODAY. Favour the most recent credible work (target year ${YEAR}; ${PREV_YEAR}-${YEAR} window) and treat older work as baselines/context unless it is seminal.

THE QUESTION TO RESEARCH:
"""${Q}"""
`

// =====================================================================
// PHASE 1 — SCOPE: read local corpus + plan the external search
// =====================================================================
phase('Scope')

const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    interpretation: { type: 'string', description: 'the question restated and scoped — what a complete answer must cover' },
    alreadyKnown: { type: 'array', items: { type: 'string' }, description: 'what THIS repo already covers (from notes/ and reference/bibliography.md), so harvest targets the gaps' },
    alreadyHave: {
      type: 'array',
      description: 'every PDF already in reference/project-papers/ (so harvest/acquire never duplicate)',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          filename: { type: 'string' },
          id: { type: 'string', description: 'arXiv id if derivable from filename/README, else empty' },
          title: { type: 'string' },
        },
        required: ['filename', 'title'],
      },
    },
    facets: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          key: { type: 'string' },
          sourceType: { type: 'string', enum: ['academic', 'code', 'web'] },
          queries: { type: 'array', items: { type: 'string' }, description: '3-5 concrete search queries for this facet' },
          lookFor: { type: 'string', description: 'what a good find for this facet looks like (effect sizes, repos with HAR baselines, etc.)' },
        },
        required: ['key', 'sourceType', 'queries', 'lookFor'],
      },
    },
    seminalTargets: { type: 'array', items: { type: 'string' }, description: 'specific known papers/authors/repos to hunt for by name' },
  },
  required: ['interpretation', 'alreadyKnown', 'alreadyHave', 'facets', 'seminalTargets'],
}

const plan = await agent(
  `${CONTEXT}

You are SCOPING this research question before the external sweep.

1. Read the local corpus to learn what we ALREADY know: Glob/Read across notes/ (esp. volatility.md, research-journal.md, notes/features/*.md) and reference/bibliography.md. Summarize what's already covered so the harvest doesn't waste effort re-finding it.
2. INVENTORY what we already HOLD as PDFs: Glob 'reference/project-papers/*.pdf' and Read 'reference/project-papers/README.md'. For EVERY pdf, return an alreadyHave entry { filename, id (the arXiv id like 2406.08041 if it appears in the filename or README, else ""), title (from the README row if present, else inferred from the filename) }. This list is used downstream to guarantee we never re-download a paper we already have.
3. Decompose the question into 5-8 search FACETS spanning three source types: 'academic' (arXiv, SSRN, journals, Google Scholar style), 'code' (GitHub repos, Papers-with-Code, Kaggle), and 'web' (practitioner blogs, docs, talks). Give each facet 3-5 concrete search queries and what a good hit looks like. You MUST include one dedicated 'frontier' facet (sourceType 'academic') aimed at the NEWEST preprints / working papers from the last ~18 months that define the current state of the art.
4. Name specific seminal papers/authors/repos to hunt for by name, AND the newest method families currently considered state-of-the-art for this question.

Lead with the current state of the art and the methodologies in active use today. Be concrete and finance-vol-aware. Return the plan.`,
  { label: 'scope:plan', phase: 'Scope', agentType: 'Explore', schema: PLAN_SCHEMA }
)

log(`Scoped into ${plan.facets.length} facets; ${plan.alreadyKnown.length} things already known; ${plan.alreadyHave.length} PDFs already held`)

// =====================================================================
// PHASE 2 — HARVEST: parallel internet sweep, one agent per facet
// =====================================================================
phase('Harvest')

const HARVEST_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    facet: { type: 'string' },
    sources: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          title: { type: 'string' },
          url: { type: 'string', description: 'the real URL you fetched/found' },
          type: { type: 'string', enum: ['paper', 'repo', 'blog', 'dataset', 'docs', 'other'] },
          year: { type: 'string' },
          authors: { type: 'string' },
          venue: { type: 'string', description: 'journal/conf/arXiv/GitHub org, if known' },
          keyClaims: { type: 'array', items: { type: 'string' }, description: 'specific findings/results, with numbers where stated' },
          method: { type: 'string' },
          data: { type: 'string', description: 'asset universe, frequency, sample period if stated' },
          reportedResults: { type: 'string', description: 'QLIKE/MSE/MAE/Sharpe deltas or benchmark comparisons, verbatim where possible' },
          codeLink: { type: 'string', description: 'GitHub/code URL if any' },
          access: { type: 'string', enum: ['open', 'abstract-only', 'paywalled', 'unknown'] },
          relevance: { type: 'number', description: '1-5 relevance to the question' },
          snippetEvidence: { type: 'string', description: 'the actual fetched text the key claim is drawn from — used for verification' },
        },
        required: ['title', 'url', 'type', 'keyClaims', 'access', 'relevance', 'snippetEvidence'],
      },
    },
    deadEnds: { type: 'array', items: { type: 'string' }, description: 'queries that returned nothing useful' },
  },
  required: ['facet', 'sources', 'deadEnds'],
}

const harvest = (await parallel(plan.facets.map(f => () =>
  agent(
    `${CONTEXT}

You are HARVESTING the internet for ONE facet of this question.
FACET: ${f.key}  (source type: ${f.sourceType})
What a good hit looks like: ${f.lookFor}
Run these searches (and reasonable variants): ${JSON.stringify(f.queries)}
Also try to surface these named targets if relevant: ${JSON.stringify(plan.seminalTargets)}

Use WebSearch to find sources, then WebFetch the most promising ones to read them. For 'code' facets, fetch GitHub repo pages / READMEs / raw files and capture whether the repo has a runnable HAR baseline, what data it uses, and the code link. For 'academic', capture effect sizes, data context, and method. For each source you keep, you MUST include snippetEvidence: the actual fetched text the key claim came from — do NOT report a claim you didn't see in fetched text. Mark access honestly (open / abstract-only / paywalled). Aim for 4-10 high-relevance sources; skip low-signal hits. Return only what you actually fetched.`,
    { label: `harvest:${f.key}`.slice(0, 40), phase: 'Harvest', agentType: 'Explore', schema: HARVEST_SCHEMA }
  )
))).filter(Boolean)

// Barrier is correct here: dedup across ALL harvesters before the (expensive) verify pass.
const seen = new Set()
const allSources = harvest.flatMap(h => h.sources).filter(s => {
  const k = (s.url || s.title || '').toLowerCase().replace(/\/+$/, '')
  if (!k || seen.has(k)) return false
  seen.add(k)
  return true
})
const toVerify = allSources.sort((a, b) => (b.relevance || 0) - (a.relevance || 0)).slice(0, TOP_N)
log(`Harvested ${allSources.length} unique sources across ${harvest.length} facets; verifying top ${toVerify.length}`)

// =====================================================================
// PHASE 3 — VERIFY: adversarially ground the top claims (parallel)
// =====================================================================
phase('Verify')

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    url: { type: 'string' },
    title: { type: 'string' },
    claimChecked: { type: 'string', description: 'the most load-bearing claim you tried to confirm' },
    grounded: { type: 'boolean', description: 'does the source actually support the claim (as fetched)?' },
    accessConfirmed: { type: 'string', enum: ['open', 'abstract-only', 'paywalled', 'dead-link'] },
    credibility: { type: 'string', enum: ['peer-reviewed', 'preprint', 'practitioner', 'unknown'] },
    correction: { type: 'string', description: 'if the harvested claim was wrong/overstated, the corrected version; else empty' },
    keep: { type: 'boolean', description: 'keep this source in the distilled dossier?' },
    verifierNote: { type: 'string' },
  },
  required: ['url', 'title', 'claimChecked', 'grounded', 'accessConfirmed', 'credibility', 'keep', 'verifierNote'],
}

const verified = (await parallel(toVerify.map(s => () =>
  agent(
    `${CONTEXT}

ADVERSARIALLY VERIFY one harvested source. Default to skepticism.
SOURCE: ${JSON.stringify({ title: s.title, url: s.url, type: s.type, keyClaims: s.keyClaims, reportedResults: s.reportedResults, access: s.access, snippetEvidence: s.snippetEvidence }, null, 1)}

Re-fetch the URL (WebFetch). Check: (a) does the source actually contain the load-bearing claim / numbers reported? (b) is it really accessible, or abstract-only / paywalled / dead? (c) how credible is it (peer-reviewed > preprint > practitioner blog)? If the harvested claim is overstated or unsupported by what you can actually read, set grounded=false and give the correction. Only set keep=true for sources that materially help answer the question AND whose key claim you could ground (or that are clearly credible primary sources worth citing with a caveat).`,
    { label: `verify:${(s.title || s.url || '').slice(0, 30)}`, phase: 'Verify', agentType: 'Explore', schema: VERIFY_SCHEMA }
  )
))).filter(Boolean)

const verdictByUrl = new Map(verified.map(v => [(v.url || '').toLowerCase().replace(/\/+$/, ''), v]))
const dossier = toVerify.map(s => {
  const v = verdictByUrl.get((s.url || '').toLowerCase().replace(/\/+$/, ''))
  return { source: s, verdict: v || null }
}).filter(x => !x.verdict || x.verdict.keep)
log(`Verified ${verified.length}; ${dossier.length} sources kept for the dossier`)

// =====================================================================
// PHASE 4 — DISTILL: synthesize the answer and write it into the repo
// =====================================================================
phase('Distill')

const DISTILL_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    filePath: { type: 'string' },
    written: { type: 'boolean' },
    directAnswer: { type: 'string', description: 'the headline answer to the question, 3-6 sentences, with confidence and the biggest caveat' },
    topPapers: { type: 'array', items: { type: 'string' }, description: 'papers worth adding to reference/, as "Title (year) — url — why"' },
    topRepos: { type: 'array', items: { type: 'string' }, description: 'GitHub repos worth studying on the GS machine, as "repo — url — why"' },
    contradictions: { type: 'array', items: { type: 'string' }, description: 'where sources disagree, and the open question it leaves' },
    newVsKnown: { type: 'string', description: 'one line: what is NEW here vs what the repo already had' },
  },
  required: ['filePath', 'written', 'directAnswer', 'topPapers', 'topRepos', 'contradictions', 'newVsKnown'],
}

const distillInput = JSON.stringify(
  dossier.map(d => ({
    title: d.source.title, url: d.source.url, type: d.source.type, year: d.source.year,
    authors: d.source.authors, venue: d.source.venue, keyClaims: d.source.keyClaims,
    method: d.source.method, data: d.source.data, reportedResults: d.source.reportedResults,
    codeLink: d.source.codeLink, access: d.source.access,
    credibility: d.verdict && d.verdict.credibility, grounded: d.verdict ? d.verdict.grounded : null,
    correction: d.verdict && d.verdict.correction, verifierNote: d.verdict && d.verdict.verifierNote,
  })), null, 1
)

const distilled = await agent(
  `${CONTEXT}

You are writing the DISTILLED RESEARCH BRIEF and saving it into the repo.

Already-in-repo (avoid re-deriving; mark the delta): ${JSON.stringify(plan.alreadyKnown)}

VERIFIED SOURCE DOSSIER (only verified/kept sources; 'grounded:false' or 'correction' means treat the original claim with care):
${distillInput}

Write a tight markdown brief — the user hates fluff and hedging — with this structure:

# Deep Research: ${Q}

**Date:** 2026 internship session · **Sources:** N kept of harvested

## Direct Answer
(3-6 sentences. Lead with the answer. State confidence and the single biggest caveat — especially that cited studies' asset universe/sample differs from ours.)

## Key Insights
(5-9 bullets, quantitative where the sources give numbers — bps QLIKE deltas, Sharpe, benchmark comparisons. Each insight tagged with credibility: [peer-reviewed] / [preprint] / [practitioner].)

## Evidence Table
| Claim / finding | Source | Year | Credibility | Grounded? | Reported result |
(one row per material claim, with the verbatim-ish reported result and a link)

## Papers to Ingest (reference/project-papers/)
(ranked; "Title (year) — url — why it matters for us")

## Code to Study (on the GS machine, H:\\)
(ranked GitHub repos; "repo — url — what's reusable, does it have a HAR baseline")

## Contradictions & Open Threads
(where sources disagree; what we'd need to compute on OUR data to resolve it — frame as a testable experiment with a QLIKE/DM criterion)

## New vs Already Known
(one paragraph: what this adds beyond what notes/ already had)

After composing it, WRITE the full brief to '${OUT}' using the Write tool (create the notes/deep-research/ directory if needed). Then return the structured summary, with filePath='${OUT}' and written=true if the Write succeeded. If you cannot write the file, set written=false and put the full markdown in directAnswer so it isn't lost.`,
  { label: 'distill:brief', phase: 'Distill', schema: DISTILL_SCHEMA }
)

return {
  question: Q,
  outputFile: distilled.filePath,
  written: distilled.written,
  directAnswer: distilled.directAnswer,
  sourcesKept: dossier.length,
  sourcesHarvested: allSources.length,
  topPapers: distilled.topPapers,
  topRepos: distilled.topRepos,
  contradictions: distilled.contradictions,
  newVsKnown: distilled.newVsKnown,
}
