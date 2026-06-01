# Deep Research Distill v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `deep-research-distill` workflow so it researches the current state of the art, downloads the relevant open-access papers into `reference/project-papers/` (deduped, recovering open versions of paywalled journals), ranks sources peer-review-first, and writes a fully source-traced brief.

**Architecture:** Single workflow script `.claude/workflows/deep-research-distill.js` (Scope → Harvest → Verify → **Acquire** → Distill). Pure helper functions are developed test-first in a companion Node test module and mirrored verbatim into the workflow behind marker comments, guarded by a drift test. Orchestration changes (schemas, prompts, the new phase) are verified by a syntax parse-check, since the script can only execute inside the Workflow runtime.

**Tech Stack:** Plain JavaScript (Workflow runtime — no `import`, no `Date.now()`, globals `agent`/`parallel`/`phase`/`log`/`args`). Node 22 built-in test runner (`node --test`) and `node --check` for the companion helper module and parse validation. `curl` for downloads.

**Spec:** `docs/superpowers/specs/2026-06-01-deep-research-distill-v2-design.md`

---

## File Structure

- **Modify:** `.claude/workflows/deep-research-distill.js` — the workflow (all behavior changes).
- **Create:** `.claude/workflows/__tests__/dr-distill-helpers.test.mjs` — canonical home of the pure helper block (between marker comments) + its unit tests + a drift-guard test asserting the workflow's mirrored copy is byte-identical.

The helper block is delimited in BOTH files by these exact marker lines:

```
// >>> DR-DISTILL HELPERS (mirror of __tests__/dr-distill-helpers.test.mjs) >>>
... helper functions ...
// <<< DR-DISTILL HELPERS <<<
```

The test module is the source of truth; Task 7 transplants the finished block into the workflow.

---

## Task 1: Scaffold the helper test module + `deriveYear`

**Files:**
- Create: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing test**

Create the file with the marker block (containing only `deriveYear` for now) and its tests:

```js
import { test } from 'node:test'
import assert from 'node:assert'

// >>> DR-DISTILL HELPERS (mirror of __tests__/dr-distill-helpers.test.mjs) >>>
// Pure, dependency-free helpers shared with .claude/workflows/deep-research-distill.js.
// EDIT HERE ONLY. Task 7 mirrors this block verbatim into the workflow.

function deriveYear(slug, fallback) {
  const m = String(slug || '').match(/(20\d{2})/)
  const year = m ? m[1] : (fallback || '2025')
  const prevYear = String(Number(year) - 1)
  return { year, prevYear }
}
// <<< DR-DISTILL HELPERS <<<

test('deriveYear parses a YYYY-MM-DD slug prefix', () => {
  assert.deepStrictEqual(deriveYear('2026-05-31-what-beats-har', '2099'), { year: '2026', prevYear: '2025' })
})

test('deriveYear falls back when no year present', () => {
  assert.deepStrictEqual(deriveYear('research', '2026'), { year: '2026', prevYear: '2025' })
})

test('deriveYear handles an older dated slug', () => {
  assert.deepStrictEqual(deriveYear('2024-01-01-topic', '2026'), { year: '2024', prevYear: '2023' })
})
```

- [ ] **Step 2: Run test to verify it passes**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS, 3 tests passing. (We write helper + test together here because the helper is trivial; subsequent tasks follow strict red-green.)

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: scaffold dr-distill helper module with deriveYear

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Tier-weight helpers (`tierWeight`, `scoreSource`, `harvestTierWeight`)

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing tests**

Add these tests below the existing tests:

```js
test('tierWeight ranks peer-reviewed > preprint > practitioner', () => {
  assert.strictEqual(tierWeight('peer-reviewed'), 1.0)
  assert.strictEqual(tierWeight('preprint'), 0.8)
  assert.strictEqual(tierWeight('practitioner'), 0.5)
  assert.strictEqual(tierWeight('unknown'), 0.6)
})

test('scoreSource multiplies relevance by credibility tier', () => {
  assert.strictEqual(scoreSource(5, 'peer-reviewed'), 5)
  assert.strictEqual(scoreSource(5, 'practitioner'), 2.5)
  assert.strictEqual(scoreSource(undefined, 'peer-reviewed'), 0)
})

test('harvestTierWeight prioritises primary sources by harvest type', () => {
  assert.strictEqual(harvestTierWeight('paper'), 1.0)
  assert.strictEqual(harvestTierWeight('repo'), 0.8)
  assert.strictEqual(harvestTierWeight('blog'), 0.5)
  assert.strictEqual(harvestTierWeight('other'), 0.5)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL with `ReferenceError: tierWeight is not defined`.

- [ ] **Step 3: Add the helpers inside the marker block**

Insert after `deriveYear` (still inside the `// >>> ... >>>` / `// <<< ... <<<` block):

```js
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS, all tests passing.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: add credibility tier-weight helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Filename generation (`slugifyWords`, `firstAuthorLast`, `paperSlugName`)

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing tests**

Add below existing tests:

```js
test('firstAuthorLast extracts the lowercased surname of the first author', () => {
  assert.strictEqual(firstAuthorLast('Fulvio Corsi'), 'corsi')
  assert.strictEqual(firstAuthorLast('Bollerslev, Tim; Patton, Andrew'), 'bollerslev')
  assert.strictEqual(firstAuthorLast('Chen and Robert'), 'chen')
  assert.strictEqual(firstAuthorLast(''), 'unknown')
})

test('slugifyWords lowercases, strips stopwords/punctuation, caps word count', () => {
  assert.strictEqual(
    slugifyWords('A Simple Approximate Long-Memory Model of Realized Volatility', 4),
    'simple-approximate-long-memory'
  )
})

test('paperSlugName builds firstauthor-year-shorttitle.pdf', () => {
  assert.strictEqual(
    paperSlugName('Fulvio Corsi', '2009', 'A Simple Approximate Long-Memory Model of Realized Volatility'),
    'corsi-2009-simple-approximate-long-memory.pdf'
  )
})

test('paperSlugName degrades gracefully on missing fields', () => {
  assert.strictEqual(paperSlugName('', '', ''), 'unknown-nd-paper.pdf')
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL with `ReferenceError: firstAuthorLast is not defined`.

- [ ] **Step 3: Add the helpers inside the marker block**

```js
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: add paper filename-slug helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Dedup helpers (`extractArxivId`, `normalizeTitle`, `authorYearFromFilename`, `authorYearKey`, `isAlreadyHave`)

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing tests**

```js
test('extractArxivId pulls the id from a url or text', () => {
  assert.strictEqual(extractArxivId('https://arxiv.org/abs/2406.08041'), '2406.08041')
  assert.strictEqual(extractArxivId('arXiv 2505.11163v2'), '2505.11163')
  assert.strictEqual(extractArxivId('no id here'), null)
})

test('normalizeTitle collapses to lowercase alphanumeric words', () => {
  assert.strictEqual(normalizeTitle('HARd to Beat: Rolling Windows!'), 'hard to beat rolling windows')
})

test('authorYearFromFilename reads the author-year prefix', () => {
  assert.strictEqual(authorYearFromFilename('corsi-2009-har-realized-volatility.pdf'), 'corsi-2009')
  assert.strictEqual(authorYearFromFilename('README.md'), null)
})

test('authorYearKey builds a surname-year key from metadata', () => {
  assert.strictEqual(authorYearKey('Fulvio Corsi', '2009'), 'corsi-2009')
})

test('isAlreadyHave matches by arxiv id', () => {
  const have = [{ filename: 'x.pdf', id: '2406.08041', title: 'HARd to Beat' }]
  assert.strictEqual(isAlreadyHave({ url: 'https://arxiv.org/abs/2406.08041', title: 'Different', authors: 'X', year: '2024' }, have), true)
})

test('isAlreadyHave matches by normalized title', () => {
  const have = [{ filename: 'x.pdf', id: '', title: 'HARd to Beat' }]
  assert.strictEqual(isAlreadyHave({ url: '', title: 'HARd to beat!', authors: 'X', year: '2024' }, have), true)
})

test('isAlreadyHave matches by filename author-year prefix', () => {
  const have = [{ filename: 'corsi-2009-har-realized-volatility.pdf', id: '', title: 'Something else' }]
  assert.strictEqual(isAlreadyHave({ url: '', title: 'Unrelated', authors: 'Fulvio Corsi', year: '2009' }, have), true)
})

test('isAlreadyHave returns false for a genuinely new paper', () => {
  const have = [{ filename: 'corsi-2009-har.pdf', id: '2406.08041', title: 'HARd to Beat' }]
  assert.strictEqual(isAlreadyHave({ url: 'https://arxiv.org/abs/2604.02743', title: 'Rough Heston RV', authors: 'New Author', year: '2026' }, have), false)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL with `ReferenceError: extractArxivId is not defined`.

- [ ] **Step 3: Add the helpers inside the marker block**

```js
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: add paper-dedup matching helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Acquisition helpers (`arxivPdfUrl`, `looksLikePdf`, `dateBiasedQueries`)

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing tests**

```js
test('arxivPdfUrl normalizes an abs/id to a pdf url', () => {
  assert.strictEqual(arxivPdfUrl('https://arxiv.org/abs/2406.08041'), 'https://arxiv.org/pdf/2406.08041')
  assert.strictEqual(arxivPdfUrl('2505.11163'), 'https://arxiv.org/pdf/2505.11163')
  assert.strictEqual(arxivPdfUrl('https://academic.oup.com/jfec/article/22/2/492'), null)
})

test('looksLikePdf detects the %PDF header only', () => {
  assert.strictEqual(looksLikePdf('%PDF-1.7\n...'), true)
  assert.strictEqual(looksLikePdf('<!DOCTYPE html>'), false)
  assert.strictEqual(looksLikePdf(null), false)
})

test('dateBiasedQueries appends year-qualified variants and dedups', () => {
  const out = dateBiasedQueries(['HAR QLIKE'], '2026', '2025')
  assert.ok(out.includes('HAR QLIKE'))
  assert.ok(out.includes('HAR QLIKE 2026'))
  assert.ok(out.includes('HAR QLIKE 2025 2026'))
  assert.strictEqual(new Set(out).size, out.length)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL with `ReferenceError: arxivPdfUrl is not defined`.

- [ ] **Step 3: Add the helpers inside the marker block**

```js
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: add acquisition + date-bias query helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: README-row builders (`buildReadmeRow`, `buildStillNeededLine`)

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs`

- [ ] **Step 1: Write the failing tests**

```js
test('buildReadmeRow renders a markdown table row matching the index format', () => {
  assert.strictEqual(
    buildReadmeRow(20, 'Rough-Heston RV (2026) -- arXiv 2604.02743', 'newauthor-2026-rough-heston-rv.pdf', 'Recommended'),
    '| 20 | Rough-Heston RV (2026) -- arXiv 2604.02743 | `newauthor-2026-rough-heston-rv.pdf` | Recommended |'
  )
})

test('buildReadmeRow bolds Essential status', () => {
  assert.strictEqual(
    buildReadmeRow(21, 'Foundational Paper', 'x-2020-y.pdf', 'Essential'),
    '| 21 | Foundational Paper | `x-2020-y.pdf` | **Essential** |'
  )
})

test('buildStillNeededLine renders a bullet', () => {
  assert.strictEqual(
    buildStillNeededLine('Liu, Patton & Sheppard (2015) -- J. Econometrics'),
    '- Liu, Patton & Sheppard (2015) -- J. Econometrics'
  )
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL with `ReferenceError: buildReadmeRow is not defined`.

- [ ] **Step 3: Add the helpers inside the marker block**

```js
function buildReadmeRow(num, paperLabel, filename, status) {
  const st = status === 'Essential' ? '**Essential**' : 'Recommended'
  return `| ${num} | ${paperLabel} | \`${filename}\` | ${st} |`
}

function buildStillNeededLine(paperLabel) {
  return `- ${paperLabel}`
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS, full suite green.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "test: add README index row builders

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Mirror the helper block into the workflow + drift guard

**Files:**
- Modify: `.claude/workflows/__tests__/dr-distill-helpers.test.mjs` (add the guard test)
- Modify: `.claude/workflows/deep-research-distill.js` (insert the mirrored block)

- [ ] **Step 1: Write the failing drift-guard test**

Add to the bottom of the test module, and add the three `node:` imports at the very top of the file (below the existing `node:test`/`node:assert` imports):

```js
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
```

```js
function extractHelperBlock(text) {
  const start = text.indexOf('// >>> DR-DISTILL HELPERS')
  const end = text.indexOf('// <<< DR-DISTILL HELPERS')
  if (start === -1 || end === -1) return null
  return text.slice(start, end).trim()
}

test('workflow helper block is byte-identical to the tested canonical block', () => {
  const here = dirname(fileURLToPath(import.meta.url))
  const workflowPath = join(here, '..', 'deep-research-distill.js')
  const testSrc = readFileSync(fileURLToPath(import.meta.url), 'utf8')
  const wfSrc = readFileSync(workflowPath, 'utf8')
  const canonical = extractHelperBlock(testSrc)
  const mirrored = extractHelperBlock(wfSrc)
  assert.ok(canonical, 'canonical helper block not found in test file')
  assert.ok(mirrored, 'helper block not found in workflow file')
  assert.strictEqual(mirrored, canonical)
})
```

- [ ] **Step 2: Run the guard to verify it fails**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: FAIL on the new test with "helper block not found in workflow file" (the workflow has no block yet).

- [ ] **Step 3: Insert the mirrored block into the workflow**

In `.claude/workflows/deep-research-distill.js`, find this exact text (lines ~24-34):

```js
const SLUG = (isObj && A.slug) || 'research'
const DEPTH = (isObj && A.depth) || 'standard'   // 'standard' (~15 verified sources) | 'deep' (~25)
const TOP_N = DEPTH === 'deep' ? 25 : 15
const OUT = `notes/deep-research/${SLUG}.md`

const CONTEXT = `
```

Replace it with (paste the helper block **verbatim** from the test module — every line between and including the `// >>>` and `// <<<` markers must match exactly, or the guard test fails):

```js
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
```

- [ ] **Step 4: Run the guard + full suite to verify they pass**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS, all tests including the drift guard.

- [ ] **Step 5: Parse-check the workflow**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit code 0 (valid ES module syntax including top-level await).

- [ ] **Step 6: Commit**

```bash
git add .claude/workflows/deep-research-distill.js .claude/workflows/__tests__/dr-distill-helpers.test.mjs
git commit -m "feat: mirror tested pure helpers into deep-research-distill workflow

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Scope phase — SOTA lens, existing-papers inventory, mandatory frontier facet

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: no unit test possible (depends on Workflow runtime + LLM). Verified by parse-check + the drift guard staying green.

- [ ] **Step 1: Add the SOTA research lens to CONTEXT**

Find:

```js
THE QUESTION TO RESEARCH:
"""${Q}"""
`
```

Replace with:

```js
RESEARCH LENS: Prioritise the CURRENT STATE OF THE ART and the methodologies in ACTIVE USE TODAY. Favour the most recent credible work (target year ${YEAR}; ${PREV_YEAR}-${YEAR} window) and treat older work as baselines/context unless it is seminal.

THE QUESTION TO RESEARCH:
"""${Q}"""
`
```

- [ ] **Step 2: Add `alreadyHave` to `PLAN_SCHEMA`**

Find:

```js
    alreadyKnown: { type: 'array', items: { type: 'string' }, description: 'what THIS repo already covers (from notes/ and reference/bibliography.md), so harvest targets the gaps' },
```

Replace with:

```js
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
```

- [ ] **Step 3: Add `alreadyHave` to the `PLAN_SCHEMA` required list**

Find:

```js
  required: ['interpretation', 'alreadyKnown', 'facets', 'seminalTargets'],
```

Replace with:

```js
  required: ['interpretation', 'alreadyKnown', 'alreadyHave', 'facets', 'seminalTargets'],
```

- [ ] **Step 4: Update the Scope agent prompt (inventory + frontier facet + SOTA)**

Find:

```js
1. Read the local corpus to learn what we ALREADY know: Glob/Read across notes/ (esp. volatility.md, research-journal.md, notes/features/*.md) and reference/bibliography.md. Summarize what's already covered so the harvest doesn't waste effort re-finding it.
2. Decompose the question into 5-8 search FACETS spanning three source types: 'academic' (arXiv, SSRN, journals, Google Scholar style), 'code' (GitHub repos, Papers-with-Code, Kaggle), and 'web' (practitioner blogs, docs, talks). Give each facet 3-5 concrete search queries and what a good hit looks like.
3. Name specific seminal papers/authors/repos to hunt for by name.

Be concrete and finance-vol-aware. Return the plan.`,
```

Replace with:

```js
1. Read the local corpus to learn what we ALREADY know: Glob/Read across notes/ (esp. volatility.md, research-journal.md, notes/features/*.md) and reference/bibliography.md. Summarize what's already covered so the harvest doesn't waste effort re-finding it.
2. INVENTORY what we already HOLD as PDFs: Glob 'reference/project-papers/*.pdf' and Read 'reference/project-papers/README.md'. For EVERY pdf, return an alreadyHave entry { filename, id (the arXiv id like 2406.08041 if it appears in the filename or README, else ""), title (from the README row if present, else inferred from the filename) }. This list is used downstream to guarantee we never re-download a paper we already have.
3. Decompose the question into 5-8 search FACETS spanning three source types: 'academic' (arXiv, SSRN, journals, Google Scholar style), 'code' (GitHub repos, Papers-with-Code, Kaggle), and 'web' (practitioner blogs, docs, talks). Give each facet 3-5 concrete search queries and what a good hit looks like. You MUST include one dedicated 'frontier' facet (sourceType 'academic') aimed at the NEWEST preprints / working papers from the last ~18 months that define the current state of the art.
4. Name specific seminal papers/authors/repos to hunt for by name, AND the newest method families currently considered state-of-the-art for this question.

Lead with the current state of the art and the methodologies in active use today. Be concrete and finance-vol-aware. Return the plan.`,
```

- [ ] **Step 5: Surface the inventory count in the log line**

Find:

```js
log(`Scoped into ${plan.facets.length} facets; ${plan.alreadyKnown.length} things already in repo`)
```

Replace with:

```js
log(`Scoped into ${plan.facets.length} facets; ${plan.alreadyKnown.length} things already known; ${plan.alreadyHave.length} PDFs already held`)
```

- [ ] **Step 6: Parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 7: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(scope): SOTA lens, held-paper inventory, mandatory frontier facet

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Harvest phase — date-biased queries + skip already-held papers

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: verified by parse-check.

- [ ] **Step 1: Inject date-biased queries and the held-paper guard into the harvest prompt**

Find:

```js
What a good hit looks like: ${f.lookFor}
Run these searches (and reasonable variants): ${JSON.stringify(f.queries)}
Also try to surface these named targets if relevant: ${JSON.stringify(plan.seminalTargets)}
```

Replace with:

```js
What a good hit looks like: ${f.lookFor}
Run these searches (and reasonable variants): ${JSON.stringify(dateBiasedQueries(f.queries, YEAR, PREV_YEAR))}
Also try to surface these named targets if relevant: ${JSON.stringify(plan.seminalTargets)}
Bias HARD toward the current state of the art and the most recent credible work (${PREV_YEAR}-${YEAR}); older work is baseline/context only.
We ALREADY HOLD these papers — do NOT propose them for download (you may still cite them as known baselines): ${JSON.stringify(plan.alreadyHave.map(h => h.title))}
```

- [ ] **Step 2: Parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(harvest): date-biased queries and skip already-held papers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Verify phase — claim location + peer-review-first selection

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: verified by parse-check. (The `scoreSource`/`harvestTierWeight` helpers it now calls are already unit-tested.)

- [ ] **Step 1: Add `claimLocation` to `VERIFY_SCHEMA` properties**

Find:

```js
    claimChecked: { type: 'string', description: 'the most load-bearing claim you tried to confirm' },
```

Replace with:

```js
    claimChecked: { type: 'string', description: 'the most load-bearing claim you tried to confirm' },
    claimLocation: { type: 'string', description: 'where in the source the claim lives: e.g. "Table 4", "§4.1", "abstract", "p.12" — empty if not locatable' },
```

- [ ] **Step 2: Add `claimLocation` to the `VERIFY_SCHEMA` required list**

Find:

```js
  required: ['url', 'title', 'claimChecked', 'grounded', 'accessConfirmed', 'credibility', 'keep', 'verifierNote'],
```

Replace with:

```js
  required: ['url', 'title', 'claimChecked', 'claimLocation', 'grounded', 'accessConfirmed', 'credibility', 'keep', 'verifierNote'],
```

- [ ] **Step 3: Ask the verifier to record the claim location**

Find:

```js
Re-fetch the URL (WebFetch). Check: (a) does the source actually contain the load-bearing claim / numbers reported? (b) is it really accessible, or abstract-only / paywalled / dead? (c) how credible is it (peer-reviewed > preprint > practitioner blog)? If the harvested claim is overstated or unsupported by what you can actually read, set grounded=false and give the correction. Only set keep=true for sources that materially help answer the question AND whose key claim you could ground (or that are clearly credible primary sources worth citing with a caveat).`,
```

Replace with:

```js
Re-fetch the URL (WebFetch). Check: (a) does the source actually contain the load-bearing claim / numbers reported, and WHERE (record claimLocation: the exact table/section/page where the number lives, so the brief can cite it precisely)? (b) is it really accessible, or abstract-only / paywalled / dead? (c) how credible is it (peer-reviewed > preprint > practitioner blog)? If the harvested claim is overstated or unsupported by what you can actually read, set grounded=false and give the correction. Only set keep=true for sources that materially help answer the question AND whose key claim you could ground (or that are clearly credible primary sources worth citing with a caveat).`,
```

- [ ] **Step 4: Make pre-verify selection peer-review-first (by harvest type)**

Find:

```js
const toVerify = allSources.sort((a, b) => (b.relevance || 0) - (a.relevance || 0)).slice(0, TOP_N)
```

Replace with:

```js
const provisional = s => (s.relevance || 0) * harvestTierWeight(s.type)
const toVerify = allSources.sort((a, b) => provisional(b) - provisional(a)).slice(0, TOP_N)
```

- [ ] **Step 5: Order the kept dossier by credibility-weighted score**

Find:

```js
const dossier = toVerify.map(s => {
  const v = verdictByUrl.get((s.url || '').toLowerCase().replace(/\/+$/, ''))
  return { source: s, verdict: v || null }
}).filter(x => !x.verdict || x.verdict.keep)
log(`Verified ${verified.length}; ${dossier.length} sources kept for the dossier`)
```

Replace with:

```js
const dossier = toVerify.map(s => {
  const v = verdictByUrl.get((s.url || '').toLowerCase().replace(/\/+$/, ''))
  return { source: s, verdict: v || null }
}).filter(x => !x.verdict || x.verdict.keep)
  .sort((a, b) =>
    scoreSource(b.source.relevance, b.verdict && b.verdict.credibility) -
    scoreSource(a.source.relevance, a.verdict && a.verdict.credibility))
log(`Verified ${verified.length}; ${dossier.length} sources kept for the dossier (peer-review-first)`)
```

- [ ] **Step 6: Parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 7: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(verify): capture claim location + peer-review-first ranking

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: New Acquire phase — download open-access PDFs + update README

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: verified by parse-check. The download agent uses the already-tested helpers (`paperSlugName`, `isAlreadyHave`, `arxivPdfUrl`, `looksLikePdf`) for its naming/dedup/validation logic.

- [ ] **Step 1: Insert the Acquire phase between Verify and Distill**

Find:

```js
log(`Verified ${verified.length}; ${dossier.length} sources kept for the dossier (peer-review-first)`)

// =====================================================================
// PHASE 4 — DISTILL: synthesize the answer and write it into the repo
// =====================================================================
phase('Distill')
```

Replace with:

```js
log(`Verified ${verified.length}; ${dossier.length} sources kept for the dossier (peer-review-first)`)

// =====================================================================
// PHASE 4 — ACQUIRE: download the relevant open-access papers into the repo
// =====================================================================
phase('Acquire')

// Only primary sources (papers/preprints) are download candidates; never blogs/docs/datasets.
// Drop anything we already hold (id / title / author-year match against the Scope inventory).
const acquireTargets = dossier
  .map(d => d.source)
  .filter(s => s.type === 'paper' || s.type === 'preprint')
  .filter(s => !isAlreadyHave(s, plan.alreadyHave))

const ACQUIRE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    downloaded: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          filename: { type: 'string' },
          fromUrl: { type: 'string', description: 'the actual open-access PDF url downloaded' },
          title: { type: 'string' },
          category: { type: 'string', description: 'README section A-E it was filed under' },
          status: { type: 'string', enum: ['Essential', 'Recommended'] },
        },
        required: ['filename', 'fromUrl', 'title'],
      },
    },
    openAccessRecovered: { type: 'array', items: { type: 'string' }, description: 'paywalled papers for which an open version was found: "title — open url used"' },
    alreadyPresent: { type: 'array', items: { type: 'string' }, description: 'candidates skipped because already in the folder' },
    paywalledStillNeeded: { type: 'array', items: { type: 'string' }, description: 'no open route found; added to README "Papers Still Needed"' },
    failed: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: { title: { type: 'string' }, reason: { type: 'string' } },
        required: ['title', 'reason'],
      },
    },
    readmeUpdated: { type: 'boolean' },
  },
  required: ['downloaded', 'openAccessRecovered', 'alreadyPresent', 'paywalledStillNeeded', 'failed', 'readmeUpdated'],
}

let acquire = { downloaded: [], openAccessRecovered: [], alreadyPresent: [], paywalledStillNeeded: [], failed: [], readmeUpdated: false }

if (acquireTargets.length === 0) {
  log('Acquire: no new primary sources to download (all already held or none qualified).')
} else {
  acquire = await agent(
    `${CONTEXT}

You are ACQUIRING the relevant papers and filing them into the repo. Work on the Windows box from the repo root.

CANDIDATES (verified primary sources NOT already held; download as many as you can get open-access):
${JSON.stringify(acquireTargets.map(s => ({ title: s.title, url: s.url, year: s.year, authors: s.authors, venue: s.venue, type: s.type, access: s.access, codeLink: s.codeLink })), null, 1)}

ALREADY HELD (never re-download these): ${JSON.stringify(plan.alreadyHave.map(h => ({ filename: h.filename, id: h.id, title: h.title })))}

For EACH candidate:
1. DEDUP first. Glob 'reference/project-papers/*.pdf'. If a file with the same arXiv id or the same first-author+year already exists, record it under alreadyPresent and SKIP.
2. RESOLVE an open-access PDF url:
   - arXiv: convert any abs/id to https://arxiv.org/pdf/<id> .
   - Direct open publisher / working-paper PDFs are fine.
   - If the only source is PAYWALLED (journal DOI, locked SSRN), ACTIVELY HUNT for an open equivalent via WebSearch/WebFetch: the arXiv / SSRN / RePEc / NBER working-paper version, the author's homepage PDF, or a Semantic Scholar / OpenReview open PDF. If you find one, use it and add the paper to openAccessRecovered ("title — open url used").
   - If NO open route exists, add it to paywalledStillNeeded and SKIP the download.
3. NAME the file 'firstauthor-year-shorttitle.pdf' (lowercase, hyphenated, ~3-4 title words, stopwords dropped), matching the existing convention in reference/project-papers/.
4. DOWNLOAD with: curl -L -s -o "reference/project-papers/<name>" "<pdf-url>"
5. VALIDATE: confirm the file exists, is more than ~10 KB, and begins with the bytes "%PDF" (e.g. head -c 4). If not a real PDF, delete it and record under failed { title, reason }.
6. On success, record under downloaded { filename, fromUrl, title, category (which README section A-E it belongs to: A foundational/HAR, B ML-core, C deep-learning/foundation, D multivariate/graph, E rough-vol), status ('Essential' only if clearly foundational, else 'Recommended') }.

THEN UPDATE 'reference/project-papers/README.md' with the Edit tool (idempotent — never add a filename that already appears):
- For each downloaded paper, append a new numbered row to the matching category table, format EXACTLY:
  | <next #> | <Author(s) (Year), "Title" -- venue> | \`<filename>\` | <**Essential** or Recommended> |
- For each paywalledStillNeeded paper, append a bullet under "## Papers Still Needed (paywalled)":
  - <Author(s) (Year), "Title" -- venue>
Set readmeUpdated=true if you edited the README.

DO NOT git add or git commit anything — leave all changes staged in the working tree for the user to review. Return the manifest.`,
    { label: 'acquire:download', phase: 'Acquire', schema: ACQUIRE_SCHEMA }
  )
}

log(`Acquire: ${acquire.downloaded.length} downloaded, ${acquire.openAccessRecovered.length} open-recovered, ${acquire.alreadyPresent.length} already-present, ${acquire.paywalledStillNeeded.length} still paywalled, ${acquire.failed.length} failed`)

// =====================================================================
// PHASE 5 — DISTILL: synthesize the answer and write it into the repo
// =====================================================================
phase('Distill')
```

- [ ] **Step 2: Parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(acquire): download open-access papers + auto-update README

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Distill phase — full traceability, new sections, manifest in return value

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: verified by parse-check.

- [ ] **Step 1: Carry `claimLocation` into the distill input**

Find:

```js
    method: d.source.method, data: d.source.data, reportedResults: d.source.reportedResults,
    codeLink: d.source.codeLink, access: d.source.access,
    credibility: d.verdict && d.verdict.credibility, grounded: d.verdict ? d.verdict.grounded : null,
    correction: d.verdict && d.verdict.correction, verifierNote: d.verdict && d.verdict.verifierNote,
```

Replace with:

```js
    method: d.source.method, data: d.source.data, reportedResults: d.source.reportedResults,
    codeLink: d.source.codeLink, access: d.source.access,
    credibility: d.verdict && d.verdict.credibility, grounded: d.verdict ? d.verdict.grounded : null,
    claimLocation: d.verdict && d.verdict.claimLocation,
    correction: d.verdict && d.verdict.correction, verifierNote: d.verdict && d.verdict.verifierNote,
```

- [ ] **Step 2: Pass the acquire manifest + traceability rule + new sections into the distill prompt**

Find:

```js
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
```

Replace with:

```js
const distilled = await agent(
  `${CONTEXT}

You are writing the DISTILLED RESEARCH BRIEF and saving it into the repo.

Already-in-repo (avoid re-deriving; mark the delta): ${JSON.stringify(plan.alreadyKnown)}

VERIFIED SOURCE DOSSIER (only verified/kept sources; 'grounded:false' or 'correction' means treat the original claim with care; 'claimLocation' is where the number lives in the source):
${distillInput}

PAPERS ACQUIRED THIS RUN (download manifest — report it faithfully, do not invent):
${JSON.stringify(acquire, null, 1)}

HARD RULE — FULL TRACEABILITY: every number, claim, and methodology statement MUST carry an explicit inline source reference: author-year + link, plus the claimLocation anchor (table/section/page) when available, e.g. "(Corsi 2009, §3, arxiv.org/...)". If a figure cannot be traced to fetched text in the dossier, DO NOT include it. Practitioner sources must be tagged context-only.

Write a tight markdown brief — the user hates fluff and hedging — with this structure:

# Deep Research: ${Q}

**Date:** ${SLUG} · **Sources:** N kept of harvested · **Lens:** state of the art, ${PREV_YEAR}-${YEAR}

## Direct Answer
(3-6 sentences. LEAD with the current state of the art and the methodologies in active use. State confidence and the single biggest caveat — especially that cited studies' asset universe/sample differs from ours.)

## Key Insights
(5-9 bullets, quantitative where the sources give numbers — bps QLIKE deltas, Sharpe, benchmark comparisons. Each bullet carries its inline source ref + claimLocation, and a credibility tag: [peer-reviewed] / [preprint] / [practitioner].)

## What's New Since Our Last Sweep
(the freshest ${PREV_YEAR}-${YEAR} sources and what they add beyond the repo's existing notes — the current frontier.)

## Evidence Table
| Claim / finding | Source | Year | Credibility | Grounded? | Location | Reported result |
(one row per material claim, with the verbatim-ish reported result, the claimLocation anchor, and a link)

## Papers Acquired
(report the manifest: downloaded PDFs with their filenames; any paywalled paper recovered via an open-access version; what remains paywalled/still-needed. State counts plainly.)

## Code to Study (on the GS machine, H:\\)
(ranked GitHub repos; "repo — url — what's reusable, does it have a HAR baseline")

## Contradictions & Open Threads
(where sources disagree; what we'd need to compute on OUR data to resolve it — frame as a testable experiment with a QLIKE/DM criterion)

## New vs Already Known
(one paragraph: what this adds beyond what notes/ already had)

After composing it, WRITE the full brief to '${OUT}' using the Write tool (create the notes/deep-research/ directory if needed). Then return the structured summary, with filePath='${OUT}' and written=true if the Write succeeded. If you cannot write the file, set written=false and put the full markdown in directAnswer so it isn't lost. DO NOT git commit.`,
  { label: 'distill:brief', phase: 'Distill', schema: DISTILL_SCHEMA }
)
```

- [ ] **Step 3: Add the acquire manifest to the workflow return value**

Find:

```js
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
```

Replace with:

```js
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
  downloaded: acquire.downloaded.map(d => d.filename),
  openAccessRecovered: acquire.openAccessRecovered,
  alreadyPresent: acquire.alreadyPresent,
  paywalledStillNeeded: acquire.paywalledStillNeeded,
  readmeUpdated: acquire.readmeUpdated,
}
```

- [ ] **Step 4: Parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(distill): full source traceability + Acquired/What's-New sections + manifest in return

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Update `meta` (phases + description) and final validation

**Files:**
- Modify: `.claude/workflows/deep-research-distill.js`

> Orchestration task: verified by parse-check + full helper suite.

- [ ] **Step 1: Add the Acquire phase to `meta.phases` and refresh the description**

Find:

```js
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
```

Replace with:

```js
export const meta = {
  name: 'deep-research-distill',
  description: 'One question in: sweep the internet for the state of the art (arXiv/SSRN papers, GitHub repos, practitioner web), adversarially verify, DOWNLOAD the relevant open-access papers into reference/project-papers/, and distill a fully source-traced brief into the repo',
  whenToUse: 'When you want to deeply research one question on the current state of the art, harvest + DOWNLOAD the relevant papers (deduped against what we already hold, recovering open versions of paywalled journals), and persist a verified, distilled brief into notes/deep-research/. Pass args="the question" or args={question, slug}.',
  phases: [
    { title: 'Scope', detail: 'read the local corpus, inventory held PDFs, decompose into source-typed facets incl. a frontier facet' },
    { title: 'Harvest', detail: 'parallel agents sweep arXiv/SSRN, GitHub, and practitioner web per facet, date-biased to recent work' },
    { title: 'Verify', detail: 'adversarially ground the top claims against their sources; record claim location; dedup; rate credibility' },
    { title: 'Acquire', detail: 'download open-access PDFs (recovering open versions of paywalled journals) and auto-update the README index' },
    { title: 'Distill', detail: 'synthesize the SOTA answer + fully-traced evidence table + acquired-papers manifest and write it into the repo' },
  ],
}
```

- [ ] **Step 2: Final parse-check**

Run (PowerShell):

```powershell
Copy-Item .claude/workflows/deep-research-distill.js "$env:TEMP/drd-check.mjs" -Force; node --check "$env:TEMP/drd-check.mjs"
```

Expected: no output, exit 0.

- [ ] **Step 3: Run the full helper suite (incl. drift guard)**

Run: `node --test .claude/workflows/__tests__/dr-distill-helpers.test.mjs`
Expected: PASS, all tests green (confirms the workflow's mirrored helper block still matches).

- [ ] **Step 4: Manual smoke-review checklist**

Read `.claude/workflows/deep-research-distill.js` top to bottom and confirm:
- `YEAR`/`PREV_YEAR` are defined before first use (in CONTEXT, harvest, distill).
- `acquire` is defined before the Distill prompt references it.
- The five phases appear in order: Scope, Harvest, Verify, Acquire, Distill.
- No `git add`/`git commit` instruction appears in any agent prompt.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/deep-research-distill.js
git commit -m "feat(meta): register Acquire phase + SOTA/download description

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notes for the implementer

- **Why no end-to-end test:** the workflow only runs inside the Workflow runtime (globals `agent`/`parallel`/`phase`/`log`/`args`; no module imports). The pure logic is fully unit-tested and mirrored under a drift guard; orchestration is validated by `node --check` on an `.mjs` copy (ESM mode allows the top-level `await` the script uses). A real end-to-end check is a live `Workflow` run on a question — see below.
- **Live verification (after Task 13, optional, costs tokens):** run the workflow via the `Workflow` tool with `args={question:"<a question>", slug:"2026-06-01-<topic>"}` and confirm: ≥1 new open-access PDF lands in `reference/project-papers/` with a correct `author-year-shorttitle.pdf` name and no duplicate; the README gains correctly-placed rows; the brief includes the "What's New" and "Papers Acquired" sections with inline source+location refs; nothing is committed automatically.
- **DRY:** all pure logic lives once in the marker block; never hand-edit the workflow copy — edit the test module and re-run Task 7's transplant + guard.
