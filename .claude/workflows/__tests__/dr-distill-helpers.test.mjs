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
