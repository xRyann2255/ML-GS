# Claude Code Hook Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repo's automatic hooks actually work (the PostToolUse nudges are dead code today), extend the guide-autosync Stop hook to cover `vol-project-ref` in addition to `vol-learning-guide`, and put the whole hook system under test and shared version-controlled settings.

**Architecture:** Two small CommonJS Node scripts in `.claude/hooks/` — `posttool-nudge.js` (PostToolUse: chapter-mirror + progress-log nudges via `hookSpecificOutput.additionalContext`, replacing three bash one-liners that grep a `$TOOL_INPUT` env var Claude Code never sets) and a rewritten `guide-autosync.js` (Stop: per-guide SHA-256 signatures in a JSON marker, fires `decision:"block"` per committed source change). Hook wiring moves from `settings.local.json` to a tracked `.claude/settings.json` using `${CLAUDE_PROJECT_DIR}` paths. Both scripts export pure helpers and are tested with `node:test` (`.test.mjs`), matching `.claude/workflows/__tests__/` conventions.

**Tech Stack:** Node v24 (CJS hook scripts, ESM tests via `node --test`), git, Claude Code hooks (PostToolUse / Stop events, stdin JSON input).

## Global Constraints

- Hook scripts must never break a session: wrap everything, any error → `exit 0`, no output.
- Hook input arrives as **JSON on stdin** (`tool_name`, `tool_input`, `stop_hook_active`, …). There is **no** `$TOOL_INPUT` env var.
- PostToolUse feedback to the model must be emitted as `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"..."}}` on stdout; plain stdout is invisible to the model.
- Stop feedback uses top-level `{"decision":"block","reason":"..."}`.
- Root resolution: `process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, '..', '..')` — no hardcoded absolute paths.
- Loop safety: the Stop hook updates its marker **when it fires**, so the sync output (markdown/PDF, which never touches `chapters/*.tex`) cannot re-trigger it. Honor `stop_hook_active`.
- Marker migration: a guide **absent** from the marker is seeded silently as already-synced (prevents a spurious full regen+push on fresh clones and on first run after this change). Legacy bare-hex marker = vol-learning-guide's signature.
- Chapter filename quirks: vol-learning-guide sources are `NN-slug.tex` mirrored as `chNN-slug.md`, with a collision (`12-deep-learning-vol.tex` → `ch12b-deep-learning-vol.md`, `12-rashomon-interpretable-trees.tex` → `ch12-rashomon-interpretable-trees.md`) — resolve by slug against the actual `markdown/` listing. vol-project-ref is a 1:1 rename (`chNN-slug.tex` → `chNN-slug.md`). Files starting with `_` are ignored (e.g. `_ch16_nobom.tex`).
- Hook scripts are CJS (`.js`, `require`), with `module.exports` of helpers and a `require.main === module` guard so tests can import them without side effects.
- Tests: `node --test .claude/hooks/__tests__/`, style matching `.claude/workflows/__tests__/*.test.mjs` (node:test + node:assert).
- Commits: conventional style (`feat(tooling): ...`), each ending with the Co-Authored-By / Claude-Session footer.

---

### Task 1: `posttool-nudge.js` — working PostToolUse nudges

**Files:**
- Create: `.claude/hooks/posttool-nudge.js`
- Test: `.claude/hooks/__tests__/posttool-nudge.test.mjs`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `module.exports = { mirrorFor, chapterNudge, commitNudge }`
  - `mirrorFor(guideName: string, texBasename: string, markdownFiles: string[]): string|null`
  - `chapterNudge(toolName: string, filePath: string, listMarkdown: (guide: string) => string[]): string|null`
  - `commitNudge(toolName: string, command: string): string|null`
  - CLI behavior: reads PostToolUse JSON on stdin; prints `hookSpecificOutput` JSON when a nudge applies, nothing otherwise; always exits 0.

- [ ] **Step 1: Write the failing test**

Create `.claude/hooks/__tests__/posttool-nudge.test.mjs`:

```js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test .claude/hooks/__tests__/posttool-nudge.test.mjs`
Expected: FAIL — `Cannot find module '../posttool-nudge.js'`

- [ ] **Step 3: Write the implementation**

Create `.claude/hooks/posttool-nudge.js`:

```js
#!/usr/bin/env node
// PostToolUse hook: turn tool events into agent-visible nudges.
//
// Replaces the old bash one-liners in settings.local.json, which were dead
// code: they grepped a $TOOL_INPUT env var that Claude Code never sets (hook
// input is JSON on stdin), and their plain stdout would not have reached the
// model anyway (only hookSpecificOutput.additionalContext is shown to Claude
// for PostToolUse).
//
// Nudges:
//   - Edit/Write on guides/<guide>/chapters/*.tex -> update the markdown mirror
//   - Bash/PowerShell running a git commit        -> update the progress log
//
// Never throws; any error exits 0 silently.

const fs = require('fs')
const path = require('path')

const ROOT = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, '..', '..')

// vol-learning-guide sources are bare-numbered (06-har-model.tex -> ch06-har-model.md,
// with number collisions like 12-*.tex -> ch12b-*.md); vol-project-ref is a 1:1 rename.
const BARE_NUMBERED = new Set(['vol-learning-guide'])
const GUIDE_RE = /guides\/(vol-learning-guide|vol-project-ref)\/chapters\/([^/]+\.tex)$/

function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') }

function mirrorFor(guideName, texBasename, markdownFiles) {
  if (texBasename.startsWith('_') || !texBasename.endsWith('.tex')) return null
  const stem = texBasename.slice(0, -4)
  if (!BARE_NUMBERED.has(guideName)) return `${stem}.md`
  const m = stem.match(/^(\d+)-(.+)$/)
  if (!m) return null
  const [, num, slug] = m
  const bySlug = (markdownFiles || []).find(f => new RegExp(`^ch\\d+[a-z]?-${escapeRe(slug)}\\.md$`).test(f))
  return bySlug || `ch${num}-${slug}.md`
}

function chapterNudge(toolName, filePath, listMarkdown) {
  if (toolName !== 'Edit' && toolName !== 'Write') return null
  const m = String(filePath || '').replace(/\\/g, '/').match(GUIDE_RE)
  if (!m) return null
  const [, guide, tex] = m
  const md = mirrorFor(guide, tex, listMarkdown(guide))
  if (!md) return null
  return `Chapter source guides/${guide}/chapters/${tex} was modified. Before finishing, update its markdown mirror guides/${guide}/markdown/${md} to match (convert-chapter-markdown skill).`
}

function commitNudge(toolName, command) {
  if (toolName !== 'Bash' && toolName !== 'PowerShell') return null
  if (!/\bgit\b[^\n]*\bcommit\b/.test(String(command || ''))) return null
  return 'A git commit was just made. If this wraps up a piece of work, update the daily progress log (progress-log skill) before finishing.'
}

function listMarkdown(guideName) {
  try { return fs.readdirSync(path.join(ROOT, 'guides', guideName, 'markdown')) } catch (e) { return [] }
}

function main() {
  let payload = {}
  try { payload = JSON.parse(fs.readFileSync(0, 'utf8') || '{}') } catch (e) {}
  const input = payload.tool_input || {}
  const msg = chapterNudge(payload.tool_name, input.file_path, listMarkdown) ||
              commitNudge(payload.tool_name, input.command)
  if (msg) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: 'PostToolUse', additionalContext: msg },
    }))
  }
}

module.exports = { mirrorFor, chapterNudge, commitNudge }
if (require.main === module) { try { main() } catch (e) {} process.exit(0) }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test .claude/hooks/__tests__/posttool-nudge.test.mjs`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/posttool-nudge.js .claude/hooks/__tests__/posttool-nudge.test.mjs
git commit -m "feat(tooling): working PostToolUse nudge hook (replaces dead \$TOOL_INPUT one-liners)"
```

---

### Task 2: `guide-autosync.js` v2 — multi-guide, portable, tested

**Files:**
- Modify: `.claude/hooks/guide-autosync.js` (full rewrite)
- Test: `.claude/hooks/__tests__/guide-autosync.test.mjs`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `module.exports = { computeSignature, parseMarker, decide, buildReason, GUIDES }`
  - `GUIDES: string[]` — `['vol-learning-guide', 'vol-project-ref']`
  - `computeSignature(files: Array<{name: string, content: string|Buffer}>): string` — sha256 hex, order-independent
  - `parseMarker(text: string): Record<string, string>` — JSON map; legacy bare hex → `{ 'vol-learning-guide': hex }`; junk → `{}`
  - `decide(states: Array<{name: string, sig: string|null, dirty: boolean}>, marker: Record<string,string>): { fire: string[], marker: Record<string,string> }`
  - `buildReason(fire: string[]): string`
  - CLI behavior: reads Stop JSON on stdin; writes updated JSON marker; prints `{"decision":"block","reason":...}` when any guide fires; always exits 0.

- [ ] **Step 1: Write the failing test**

Create `.claude/hooks/__tests__/guide-autosync.test.mjs`:

```js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test .claude/hooks/__tests__/guide-autosync.test.mjs`
Expected: FAIL — the current script has no `module.exports` (import resolves to `{}`, destructured helpers are `undefined`)

- [ ] **Step 3: Rewrite the implementation**

Replace the full contents of `.claude/hooks/guide-autosync.js` with:

```js
#!/usr/bin/env node
// Stop hook: auto-sync guide markdown mirrors + docs-only branch when a
// guide's chapter SOURCE has changed since the last sync.
//
// Covers every guide in GUIDES (vol-learning-guide, vol-project-ref).
//
// Design (loop-safe, fires once per committed source change):
//   - per-guide signature = sha256 over chapters/*.tex names+contents
//     (sorted, "_"-prefixed files excluded)
//   - marker file stores a JSON map { guideName: lastSyncedSignature };
//     legacy format (bare hex) is read as vol-learning-guide's signature
//   - a guide FIRES only when its signature differs from the marker AND its
//     chapters dir is committed (clean); firing updates its marker entry so
//     the sync output (markdown/PDF, which never touches chapter source)
//     cannot re-trigger it
//   - a guide ABSENT from the marker is seeded silently as already-synced
//     when clean (prevents a spurious full regen+push on fresh clones and
//     newly covered guides)
//   - honors stop_hook_active; never throws (any error -> exit 0)

const fs = require('fs')
const path = require('path')
const crypto = require('crypto')
const { execSync } = require('child_process')

const ROOT = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, '..', '..')
const MARKER = path.join(ROOT, '.claude', '.guide-sync-marker')

const GUIDES = ['vol-learning-guide', 'vol-project-ref']

function computeSignature(files) {
  const h = crypto.createHash('sha256')
  for (const f of [...files].sort((a, b) => (a.name < b.name ? -1 : 1))) {
    h.update(f.name)
    h.update(f.content)
  }
  return h.digest('hex')
}

function parseMarker(text) {
  const t = String(text || '').trim()
  if (!t) return {}
  if (/^[0-9a-f]{64}$/i.test(t)) return { 'vol-learning-guide': t } // legacy single-guide format
  try {
    const obj = JSON.parse(t)
    return obj && typeof obj === 'object' && !Array.isArray(obj) ? obj : {}
  } catch (e) { return {} }
}

function decide(states, marker) {
  const next = { ...marker }
  const fire = []
  for (const s of states) {
    if (s.sig == null || s.dirty) continue // unreadable or mid-edit: wait
    if (!(s.name in next)) { next[s.name] = s.sig; continue } // seed as already-synced
    if (next[s.name] !== s.sig) { next[s.name] = s.sig; fire.push(s.name) }
  }
  return { fire, marker: next }
}

function buildReason(fire) {
  const dirs = fire.map(g => `guides/${g}/markdown/`).join(' and ')
  return [
    `[auto-sync] Chapter source changed since the last docs sync in: ${fire.join(', ')}.`,
    'Run both steps now, automatically, WITHOUT asking the user (they pre-authorized this, including the push):',
    `1) Regenerate the markdown mirrors for the changed chapters in ${dirs} (convert-chapter-markdown skill), and commit them.`,
    '2) Run the sync-docs skill once: ensure changes are on main, then sync the docs-only branch and push both main and docs-only.',
    'After syncing, give a one-line confirmation of what was synced. If you intentionally do not want to sync, say so briefly.',
  ].join(' ')
}

function readChapterFiles(dir) {
  const names = fs.readdirSync(dir).filter(f => f.endsWith('.tex') && !f.startsWith('_')).sort()
  return names.map(name => ({ name, content: fs.readFileSync(path.join(dir, name)) }))
}

function isDirty(root, guide) {
  const out = execSync(`git status --porcelain -- "guides/${guide}/chapters"`, { cwd: root, encoding: 'utf8' })
  return out.trim().length > 0
}

function main() {
  let payload = {}
  try { payload = JSON.parse(fs.readFileSync(0, 'utf8') || '{}') } catch (e) {}
  if (payload.stop_hook_active) return // already in a hook-driven continuation

  const states = GUIDES.map(name => {
    let sig = null
    let dirty = true
    try {
      const files = readChapterFiles(path.join(ROOT, 'guides', name, 'chapters'))
      if (files.length) {
        sig = computeSignature(files)
        dirty = isDirty(ROOT, name)
      }
    } catch (e) {}
    return { name, sig, dirty }
  })

  let marker = {}
  try { marker = parseMarker(fs.readFileSync(MARKER, 'utf8')) } catch (e) {}

  const { fire, marker: next } = decide(states, marker)
  if (JSON.stringify(next) !== JSON.stringify(marker)) {
    try {
      fs.mkdirSync(path.dirname(MARKER), { recursive: true })
      fs.writeFileSync(MARKER, JSON.stringify(next, null, 2))
    } catch (e) {}
  }
  if (fire.length) {
    process.stdout.write(JSON.stringify({ decision: 'block', reason: buildReason(fire) }))
  }
}

module.exports = { computeSignature, parseMarker, decide, buildReason, GUIDES }
if (require.main === module) { try { main() } catch (e) {} process.exit(0) }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test .claude/hooks/__tests__/`
Expected: PASS (all posttool-nudge and guide-autosync tests)

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/guide-autosync.js .claude/hooks/__tests__/guide-autosync.test.mjs
git commit -m "feat(tooling): extend guide-autosync Stop hook to vol-project-ref (JSON marker, portable root, tests)"
```

---

### Task 3: Shared settings, trimmed local settings, docs

**Files:**
- Create: `.claude/settings.json`
- Modify: `.claude/settings.local.json` (replace contents)
- Create: `.claude/hooks/README.md`
- Create: `docs/superpowers/plans/2026-07-05-hook-improvements.md` (this plan — commit it here)

**Interfaces:**
- Consumes: `posttool-nudge.js` (Task 1) and `guide-autosync.js` (Task 2) at the exact paths `.claude/hooks/<name>.js`.
- Produces: hook wiring in tracked shared settings; `settings.local.json` keeps only machine-local permission mode.

- [ ] **Step 1: Create `.claude/settings.json`**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PROJECT_DIR}/.claude/hooks/posttool-nudge.js\"",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PROJECT_DIR}/.claude/hooks/guide-autosync.js\"",
            "timeout": 30,
            "statusMessage": "Checking if guide docs need syncing..."
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Replace `.claude/settings.local.json` contents**

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
```

- [ ] **Step 3: Create `.claude/hooks/README.md`**

```markdown
# Claude Code hooks

Two Node hook scripts, wired in `.claude/settings.json` (shared, tracked).
`settings.local.json` holds only the machine-local permission mode.

Both scripts read the hook event as JSON on **stdin** (Claude Code sets no
`$TOOL_INPUT` env var — bash one-liners grepping it never fire), resolve the
repo root from `CLAUDE_PROJECT_DIR` with an `__dirname` fallback, and exit 0
on any error so they can never break a session.

## posttool-nudge.js — PostToolUse (`Edit|Write|Bash|PowerShell`)

Emits `hookSpecificOutput.additionalContext` (the only PostToolUse channel
the model actually sees) to nudge the agent to:

- update `guides/<guide>/markdown/<mirror>.md` after an Edit/Write to
  `guides/<guide>/chapters/*.tex` (vol-learning-guide `NN-slug.tex` →
  `chNN-slug.md`, number collisions resolved by slug against the real
  markdown listing; vol-project-ref is a 1:1 rename; `_*.tex` ignored)
- run the progress-log skill after a `git commit`

## guide-autosync.js — Stop

Per-guide sha256 signature over `chapters/*.tex` for **vol-learning-guide
and vol-project-ref**, compared against `.claude/.guide-sync-marker`
(gitignored JSON map `{guide: lastSyncedSignature}`; legacy bare-hex means
vol-learning-guide). When a guide's committed source (clean chapters dir)
differs from the marker, the hook blocks the Stop with instructions to
regenerate the mirrors and run sync-docs. Loop safety: the marker entry is
updated at fire time, and the sync output never touches chapter source.
Guides absent from the marker are seeded silently as already-synced, so
fresh clones don't trigger a pointless full regen+push.

## Tests

    node --test .claude/hooks/__tests__/
```

- [ ] **Step 4: Verify settings are valid JSON and tests still pass**

Run: `node -e "JSON.parse(require('fs').readFileSync('.claude/settings.json','utf8')); JSON.parse(require('fs').readFileSync('.claude/settings.local.json','utf8')); console.log('settings OK')" && node --test .claude/hooks/__tests__/`
Expected: `settings OK` then all tests PASS

- [ ] **Step 5: Commit**

```bash
git add .claude/settings.json .claude/settings.local.json .claude/hooks/README.md docs/superpowers/plans/2026-07-05-hook-improvements.md
git commit -m "chore(tooling): move hooks to shared settings.json, document hook system"
```

---

### Task 4: Real-repo smoke, marker migration, push

**Files:**
- Modify: `.claude/.guide-sync-marker` (machine-local, gitignored — migrated by running the hook)

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: migrated JSON marker on this machine; `main` pushed to origin.

- [ ] **Step 1: Smoke-run posttool-nudge against the real repo**

Run: `echo '{"tool_name":"Edit","tool_input":{"file_path":"guides/vol-project-ref/chapters/ch03-har-core.tex"}}' | node .claude/hooks/posttool-nudge.js`
Expected: JSON with `additionalContext` naming `guides/vol-project-ref/markdown/ch03-har-core.md`

- [ ] **Step 2: Smoke-run guide-autosync against the real repo (this also migrates the live marker)**

Run: `CLAUDE_PROJECT_DIR="$(pwd)" node .claude/hooks/guide-autosync.js < /dev/null; echo "exit=$?"; cat .claude/.guide-sync-marker`
Expected: `exit=0`; marker is now a JSON map containing both guide names.

Decision rule for the output:
- **No block output** → vol-learning-guide is in sync and vol-project-ref was seeded. Done.
- **Block output naming a guide** → the source changed since the last sync on this machine. Check whether the markdown mirrors were already regenerated with the latest chapter commits (`git log --oneline -5 -- guides/<guide>/chapters guides/<guide>/markdown`). If mirrors are current, the marker update is the correct migration and nothing more is needed. If mirrors lag the source, actually perform the sync the hook asked for (convert-chapter-markdown for changed chapters, then sync-docs) before continuing.

- [ ] **Step 3: Full verification run**

Run: `node --test .claude/hooks/__tests__/`
Expected: all tests PASS, exit 0

- [ ] **Step 4: Push**

```bash
git push origin main
```
Expected: `main` updated on origin; working tree clean afterwards (`git status`).
