#!/usr/bin/env node
// Stop hook: auto-sync the vol-learning-guide markdown mirrors + docs-only branch
// when the chapter SOURCE has changed since the last sync.
//
// Design (loop-safe, fires once per committed source change):
//   - signature = sha256 of all guides/vol-learning-guide/chapters/*.tex contents
//   - marker file stores the last-synced signature
//   - fires (blocks the Stop, instructing Claude to run the two skills) only when
//     signature != marker AND the chapter source is committed (clean working tree).
//   - updates the marker to the current signature WHEN it fires, so the markdown/
//     PDF/docs the sync produces (which do not change source) never re-trigger it.
//   - honors stop_hook_active to avoid re-entrancy; never throws (any error -> exit 0).

const fs = require('fs')
const path = require('path')
const crypto = require('crypto')
const { execSync } = require('child_process')

const ROOT = 'C:/Users/RyanPC/Documents/Projects/ML-GS'
const CHAPTERS = path.join(ROOT, 'guides', 'vol-learning-guide', 'chapters')
const MARKER = path.join(ROOT, '.claude', '.guide-sync-marker')

function done(obj) {
  if (obj) process.stdout.write(JSON.stringify(obj))
  process.exit(0)
}

try {
  let input = ''
  try { input = fs.readFileSync(0, 'utf8') } catch (e) {}
  let payload = {}
  try { payload = JSON.parse(input || '{}') } catch (e) {}
  if (payload.stop_hook_active) done() // already in a hook-driven continuation

  // signature of chapter source
  let files
  try {
    files = fs.readdirSync(CHAPTERS).filter((f) => f.endsWith('.tex') && !f.startsWith('_')).sort()
  } catch (e) { done() }
  if (!files || !files.length) done()
  const h = crypto.createHash('sha256')
  for (const f of files) { h.update(f); h.update(fs.readFileSync(path.join(CHAPTERS, f))) }
  const sig = h.digest('hex')

  let marker = ''
  try { marker = fs.readFileSync(MARKER, 'utf8').trim() } catch (e) {}
  if (sig === marker) done() // already synced for this source state

  // only act on COMMITTED changes (a task that wrapped up), not mid-edit
  let dirty = ''
  try { dirty = execSync('git status --porcelain -- guides/vol-learning-guide/chapters', { cwd: ROOT, encoding: 'utf8' }).trim() } catch (e) { done() }
  if (dirty) done() // source edits not yet committed; wait

  // fire once: record the new signature so the upcoming sync does not re-trigger
  try { fs.mkdirSync(path.dirname(MARKER), { recursive: true }); fs.writeFileSync(MARKER, sig) } catch (e) {}

  const reason = [
    '[auto-sync] vol-learning-guide chapter source changed since the last docs sync.',
    'Run both steps now, automatically, WITHOUT asking the user (they pre-authorized this, including the push):',
    '1) Regenerate the markdown mirrors for the changed chapters (convert-chapter-markdown skill, or the markdown-mirror-regen workflow for many chapters), and commit them.',
    '2) Run the sync-docs skill: ensure changes are on main, then sync the docs-only branch and push both main and docs-only.',
    'After syncing, give a one-line confirmation of what was synced. If you intentionally do not want to sync, say so briefly.',
  ].join(' ')

  done({ decision: 'block', reason })
} catch (e) {
  // never break the session
  process.exit(0)
}
