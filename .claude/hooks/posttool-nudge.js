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
