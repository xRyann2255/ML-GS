// .claude/workflows/__tests__/verify-all-diagrams-helpers.test.mjs
import { test } from 'node:test'
import assert from 'node:assert'

// >>> VERIFY-ALL-DIAGRAMS HELPERS (mirror into .claude/workflows/verify-all-diagrams.js) >>>
// Pure, dependency-free. EDIT HERE ONLY; the workflow mirrors this block verbatim.

// Discovery itself (reading .tex files) is done by an agent in the workflow; these helpers
// deterministically post-process the agent's FLAT figure list.

function groupByGuide(figures) {
  // [{guide, figures:[...]}] in first-seen guide order; figures keep their original order.
  const m = new Map()
  for (const f of figures) {
    if (!m.has(f.guide)) m.set(f.guide, [])
    m.get(f.guide).push(f)
  }
  return Array.from(m.entries()).map(([guide, figs]) => ({ guide, figures: figs }))
}

function locateSubstr(fig) {
  // the --locate substring diag_inspect uses to find a figure's page:
  // a distinctive caption fragment, else the label, else the synthetic id
  if (fig.caption && fig.caption.trim()) {
    return fig.caption.trim().split(/\s+/).filter(Boolean).slice(0, 6).join(' ')
  }
  return fig.label || fig.id
}

function slugify(s, i) {
  // filesystem-safe, index-prefixed crop-dir name for a figure (unique even when ids collide)
  const base = String(s || '').replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 44)
  return `f${String(i).padStart(3, '0')}_${base || 'fig'}`
}
// <<< VERIFY-ALL-DIAGRAMS HELPERS <<<

test('groupByGuide groups by guide, preserving figure order', () => {
  const groups = groupByGuide([
    { guide: 'guides/a', id: '1' },
    { guide: 'guides/b', id: '3' },
    { guide: 'guides/a', id: '2' },
  ])
  assert.equal(groups.length, 2)
  const a = groups.find(g => g.guide === 'guides/a')
  assert.deepEqual(a.figures.map(f => f.id), ['1', '2'])
})

test('locateSubstr prefers a 6-word caption fragment', () => {
  assert.equal(
    locateSubstr({ caption: 'Pipeline architecture with plug points shown here now', label: 'x', id: 'y' }),
    'Pipeline architecture with plug points shown')
})

test('locateSubstr falls back to label then id', () => {
  assert.equal(locateSubstr({ caption: '', label: 'fig:y', id: 'z' }), 'fig:y')
  assert.equal(locateSubstr({ caption: null, label: null, id: 'file.tex:12' }), 'file.tex:12')
})

test('slugify is filesystem-safe and index-prefixed', () => {
  assert.equal(slugify('fig:har/components', 3), 'f003_fig_har_components')
  assert.equal(slugify('', 0), 'f000_fig')
  assert.equal(slugify(null, 7), 'f007_fig')
})

test('slugify stays short and unique-by-index for long/colliding ids', () => {
  const a = slugify('a'.repeat(80), 12)
  assert.ok(a.length <= 50, `slug too long: ${a.length}`)
  // same raw id, different index -> different slug
  assert.notEqual(slugify('fig:dup', 1), slugify('fig:dup', 2))
})
