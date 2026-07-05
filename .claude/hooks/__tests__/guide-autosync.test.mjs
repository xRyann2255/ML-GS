import { test } from 'node:test'
import assert from 'node:assert'
import { spawnSync, execSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

import hook from '../guide-autosync.js'
const { computeSignature, parseMarker, decide, buildReason } = hook

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), '..', 'guide-autosync.js')

// --- unit ---

test('computeSignature is order-independent and content-sensitive', () => {
  const a = computeSignature([{ name: 'a.tex', content: 'A' }, { name: 'b.tex', content: 'B' }])
  const b = computeSignature([{ name: 'b.tex', content: 'B' }, { name: 'a.tex', content: 'A' }])
  const c = computeSignature([{ name: 'a.tex', content: 'A2' }, { name: 'b.tex', content: 'B' }])
  assert.equal(a, b)
  assert.notEqual(a, c)
})

test('parseMarker handles legacy bare-hex, JSON, and junk', () => {
  const hex = 'a'.repeat(64)
  assert.deepEqual(parseMarker(hex), { 'vol-learning-guide': hex })
  assert.deepEqual(parseMarker('{"x":"y"}'), { x: 'y' })
  assert.deepEqual(parseMarker(''), {})
  assert.deepEqual(parseMarker('not json'), {})
})

test('decide seeds unknown clean guides without firing', () => {
  const { fire, marker } = decide([{ name: 'g1', sig: 's1', dirty: false }], {})
  assert.deepEqual(fire, [])
  assert.deepEqual(marker, { g1: 's1' })
})

test('decide fires only for known, clean, changed guides', () => {
  const states = [
    { name: 'changed-clean', sig: 'new', dirty: false },
    { name: 'changed-dirty', sig: 'new', dirty: true },
    { name: 'unchanged', sig: 'same', dirty: false },
  ]
  const prev = { 'changed-clean': 'old', 'changed-dirty': 'old', unchanged: 'same' }
  const { fire, marker } = decide(states, prev)
  assert.deepEqual(fire, ['changed-clean'])
  assert.equal(marker['changed-clean'], 'new')
  assert.equal(marker['changed-dirty'], 'old') // untouched: fires later once committed
})

test('decide skips unreadable guides and does not seed dirty unknowns', () => {
  const { fire, marker } = decide([
    { name: 'missing', sig: null, dirty: true },
    { name: 'dirty-unknown', sig: 's', dirty: true },
  ], {})
  assert.deepEqual(fire, [])
  assert.deepEqual(marker, {})
})

test('buildReason names every fired guide and both sync steps', () => {
  const r = buildReason(['vol-learning-guide', 'vol-project-ref'])
  assert.match(r, /vol-learning-guide, vol-project-ref/)
  assert.match(r, /convert-chapter-markdown/)
  assert.match(r, /sync-docs/)
})

// --- integration (temp git repo) ---

function git(root, args) {
  execSync(`git -c user.email=t@t -c user.name=t ${args}`, { cwd: root, stdio: 'pipe' })
}

function makeRepo() {
  const root = mkdtempSync(join(tmpdir(), 'autosync-'))
  for (const g of ['vol-learning-guide', 'vol-project-ref']) {
    mkdirSync(join(root, 'guides', g, 'chapters'), { recursive: true })
  }
  writeFileSync(join(root, 'guides', 'vol-learning-guide', 'chapters', '01-a.tex'), 'v1')
  writeFileSync(join(root, 'guides', 'vol-project-ref', 'chapters', 'ch01-b.tex'), 'v1')
  git(root, 'init -q')
  git(root, 'add -A')
  git(root, 'commit -q -m init')
  return root
}

function runHook(root, payload = {}) {
  return spawnSync(process.execPath, [SCRIPT], {
    input: JSON.stringify(payload), encoding: 'utf8',
    env: { ...process.env, CLAUDE_PROJECT_DIR: root },
  })
}

const markerPath = root => join(root, '.claude', '.guide-sync-marker')

test('integration: seed silently -> dirty quiet -> committed fires once -> quiet', () => {
  const root = makeRepo()

  let r = runHook(root) // fresh: seeds both, no fire
  assert.equal(r.status, 0)
  assert.equal(r.stdout, '')
  const seeded = JSON.parse(readFileSync(markerPath(root), 'utf8'))
  assert.ok(seeded['vol-learning-guide'] && seeded['vol-project-ref'])

  writeFileSync(join(root, 'guides', 'vol-project-ref', 'chapters', 'ch01-b.tex'), 'v2')
  r = runHook(root) // dirty edit: no fire
  assert.equal(r.stdout, '')

  git(root, 'add -A'); git(root, 'commit -q -m change')
  r = runHook(root) // committed: fires for vol-project-ref only
  const out = JSON.parse(r.stdout)
  assert.equal(out.decision, 'block')
  assert.match(out.reason, /vol-project-ref/)
  assert.doesNotMatch(out.reason, /vol-learning-guide/)

  r = runHook(root) // loop safety: immediate rerun is quiet
  assert.equal(r.stdout, '')

  writeFileSync(join(root, 'guides', 'vol-learning-guide', 'chapters', '01-a.tex'), 'v2')
  git(root, 'add -A'); git(root, 'commit -q -m change2')
  r = runHook(root, { stop_hook_active: true }) // suppressed during hook continuation
  assert.equal(r.stdout, '')
  r = runHook(root)
  assert.match(JSON.parse(r.stdout).reason, /vol-learning-guide/)

  rmSync(root, { recursive: true, force: true })
})

test('integration: legacy bare-hex marker fires vol-learning-guide, seeds vol-project-ref', () => {
  const root = makeRepo()
  mkdirSync(join(root, '.claude'), { recursive: true })
  writeFileSync(markerPath(root), 'a'.repeat(64)) // stale legacy signature
  const r = runHook(root)
  const out = JSON.parse(r.stdout)
  assert.equal(out.decision, 'block')
  assert.match(out.reason, /in: vol-learning-guide\./) // changed list names only vol-learning-guide
  assert.doesNotMatch(out.reason, /vol-project-ref/)
  const marker = JSON.parse(readFileSync(markerPath(root), 'utf8'))
  assert.ok(marker['vol-project-ref']) // seeded, not fired
  rmSync(root, { recursive: true, force: true })
})
