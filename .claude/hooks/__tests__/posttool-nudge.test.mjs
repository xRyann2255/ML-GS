import { test } from 'node:test'
import assert from 'node:assert'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

import hook from '../posttool-nudge.js'
const { mirrorFor, chapterNudge, commitNudge } = hook

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), '..', 'posttool-nudge.js')

const VLG_MD = ['ch06-har-model.md', 'ch12-rashomon-interpretable-trees.md', 'ch12b-deep-learning-vol.md', 'INDEX.md']

test('mirrorFor maps vol-learning-guide bare-numbered chapters', () => {
  assert.equal(mirrorFor('vol-learning-guide', '06-har-model.tex', VLG_MD), 'ch06-har-model.md')
})

test('mirrorFor resolves the ch12/ch12b collision by slug', () => {
  assert.equal(mirrorFor('vol-learning-guide', '12-deep-learning-vol.tex', VLG_MD), 'ch12b-deep-learning-vol.md')
  assert.equal(mirrorFor('vol-learning-guide', '12-rashomon-interpretable-trees.tex', VLG_MD), 'ch12-rashomon-interpretable-trees.md')
})

test('mirrorFor falls back to chNN-slug.md when no mirror exists yet', () => {
  assert.equal(mirrorFor('vol-learning-guide', '20-new-chapter.tex', VLG_MD), 'ch20-new-chapter.md')
})

test('mirrorFor maps vol-project-ref chapters 1:1', () => {
  assert.equal(mirrorFor('vol-project-ref', 'ch03-har-core.tex', []), 'ch03-har-core.md')
})

test('mirrorFor ignores underscore-prefixed and non-tex files', () => {
  assert.equal(mirrorFor('vol-learning-guide', '_ch16_nobom.tex', VLG_MD), null)
  assert.equal(mirrorFor('vol-learning-guide', 'notes.txt', VLG_MD), null)
})

test('chapterNudge matches chapter tex paths on Edit/Write, both slash styles', () => {
  const list = () => VLG_MD
  assert.match(chapterNudge('Edit', 'C:\\repo\\guides\\vol-learning-guide\\chapters\\06-har-model.tex', list), /ch06-har-model\.md/)
  assert.match(chapterNudge('Write', 'guides/vol-project-ref/chapters/ch03-har-core.tex', list), /ch03-har-core\.md/)
  assert.equal(chapterNudge('Bash', 'guides/vol-project-ref/chapters/ch03-har-core.tex', list), null)
  assert.equal(chapterNudge('Edit', 'guides/vol-project-ref/preamble.tex', list), null)
})

test('commitNudge fires on git commit from Bash or PowerShell only', () => {
  assert.ok(commitNudge('Bash', 'git add -A && git commit -m "x"'))
  assert.ok(commitNudge('PowerShell', 'git commit -m "y"'))
  assert.equal(commitNudge('Bash', 'git status'), null)
  assert.equal(commitNudge('Edit', 'git commit'), null)
})

test('end-to-end: emits additionalContext JSON for a chapter edit', () => {
  const root = mkdtempSync(join(tmpdir(), 'nudge-'))
  mkdirSync(join(root, 'guides', 'vol-learning-guide', 'markdown'), { recursive: true })
  writeFileSync(join(root, 'guides', 'vol-learning-guide', 'markdown', 'ch12b-deep-learning-vol.md'), '')
  const payload = { tool_name: 'Edit', tool_input: { file_path: join(root, 'guides', 'vol-learning-guide', 'chapters', '12-deep-learning-vol.tex') } }
  const r = spawnSync(process.execPath, [SCRIPT], { input: JSON.stringify(payload), encoding: 'utf8', env: { ...process.env, CLAUDE_PROJECT_DIR: root } })
  assert.equal(r.status, 0)
  const out = JSON.parse(r.stdout)
  assert.equal(out.hookSpecificOutput.hookEventName, 'PostToolUse')
  assert.match(out.hookSpecificOutput.additionalContext, /ch12b-deep-learning-vol\.md/)
  rmSync(root, { recursive: true, force: true })
})

test('end-to-end: silent (no stdout, exit 0) for unrelated tools and junk stdin', () => {
  let r = spawnSync(process.execPath, [SCRIPT], { input: JSON.stringify({ tool_name: 'Read', tool_input: { file_path: 'x' } }), encoding: 'utf8' })
  assert.equal(r.status, 0)
  assert.equal(r.stdout, '')
  r = spawnSync(process.execPath, [SCRIPT], { input: 'not json', encoding: 'utf8' })
  assert.equal(r.status, 0)
  assert.equal(r.stdout, '')
})
