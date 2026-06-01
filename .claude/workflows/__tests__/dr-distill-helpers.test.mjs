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
