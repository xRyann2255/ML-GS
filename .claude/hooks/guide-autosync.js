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
