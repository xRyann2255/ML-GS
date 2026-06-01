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
