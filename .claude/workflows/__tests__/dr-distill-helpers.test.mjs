import { test } from 'node:test'
import assert from 'node:assert'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

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

test('deriveYear parses a YYYY-MM-DD slug prefix', () => {
  assert.deepStrictEqual(deriveYear('2026-05-31-what-beats-har', '2099'), { year: '2026', prevYear: '2025' })
})

test('deriveYear falls back when no year present', () => {
  assert.deepStrictEqual(deriveYear('research', '2026'), { year: '2026', prevYear: '2025' })
})

test('deriveYear handles an older dated slug', () => {
  assert.deepStrictEqual(deriveYear('2024-01-01-topic', '2026'), { year: '2024', prevYear: '2023' })
})

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

test('harvestTierWeight covers dataset and docs tiers', () => {
  assert.strictEqual(harvestTierWeight('dataset'), 0.7)
  assert.strictEqual(harvestTierWeight('docs'), 0.6)
})

test('tierWeight returns the 0.6 default for undefined input', () => {
  assert.strictEqual(tierWeight(undefined), 0.6)
})

test('scoreSource with unknown credibility tier uses the 0.6 default', () => {
  assert.strictEqual(scoreSource(5, 'blog'), 3)
})

test('slugifyWords on an all-stopword title yields empty string', () => {
  assert.strictEqual(slugifyWords('The Of And', 4), '')
})

test('isAlreadyHave matches when held entry supplies authorYear directly', () => {
  const held = [{ authorYear: 'corsi-2009', id: '', title: '' }]
  const candidate = { url: '', title: 'Unrelated', authors: 'Fulvio Corsi', year: '2009' }
  assert.strictEqual(isAlreadyHave(candidate, held), true)
})

test('isAlreadyHave matches when candidate arXiv id lives only in codeLink', () => {
  const held = [{ filename: 'x.pdf', id: '2406.08041', title: 'Held' }]
  const candidate = { url: '', codeLink: 'https://github.com/foo (arXiv 2406.08041)', title: 'Different', authors: 'X', year: '2024' }
  assert.strictEqual(isAlreadyHave(candidate, held), true)
})

test('looksLikePdf returns false for non-string truthy inputs', () => {
  assert.strictEqual(looksLikePdf(123), false)
  assert.strictEqual(looksLikePdf({}), false)
})

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
