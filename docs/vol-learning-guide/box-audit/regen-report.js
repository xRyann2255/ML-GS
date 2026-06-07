// Regenerate report.md from findings.json, recomputing boxCounts from the
// authoritative boxFindings entries (source of truth). Keeps the two artifacts
// perfectly consistent. Usage: node regen-report.js
const fs = require('fs')
const path = require('path')

const DIR = __dirname
const findingsPath = path.join(DIR, 'findings.json')
const reportPath = path.join(DIR, 'report.md')

const present = JSON.parse(fs.readFileSync(findingsPath, 'utf8'))

// Recompute boxCounts per chapter from actual entries (entries are authoritative).
for (const r of present) {
  const bf = r.boxFindings || []
  const cut = bf.filter((b) => b.verdict === 'CUT').length
  const trim = bf.filter((b) => b.verdict === 'TRIM').length
  const total = r.totalBoxes || (cut + trim + ((r.boxCounts && r.boxCounts.keep) || 0))
  r.boxCounts = { keep: total - cut - trim, trim, cut }
}

const esc = (s) => String(s == null ? '' : s).replace(/\r?\n+/g, ' ').replace(/\|/g, '\\|').trim()

let totBoxes = 0, totCut = 0, totTrim = 0, totKeep = 0, totFluff = 0
const rows = []
for (const r of present) {
  const c = r.boxCounts
  const fluff = (r.fluffFindings || []).length
  totBoxes += (r.totalBoxes || 0); totCut += c.cut; totTrim += c.trim; totKeep += c.keep; totFluff += fluff
  rows.push('| ' + r._title + ' | ' + (r.totalBoxes || 0) + ' | ' + c.cut + ' | ' + c.trim + ' | ' + c.keep + ' | ' + fluff + ' |')
}

let grandTotalsTable = '| Chapter | Boxes | CUT | TRIM | KEEP | Fluff |\n|---|---:|---:|---:|---:|---:|\n'
grandTotalsTable += rows.join('\n') + '\n'
grandTotalsTable += '| **TOTAL** | **' + totBoxes + '** | **' + totCut + '** | **' + totTrim + '** | **' + totKeep + '** | **' + totFluff + '** |\n'

let md = '# Box & Fluff Audit — Review Report (MODERATE pass)\n\n'
md += 'Moderate earn-or-go pass over the 20 compiled chapters of `vol-learning-guide`. '
md += 'Verdicts: **CUT** = remove the box · **TRIM** = keep the box but shorten it · fluff = prose to tighten. '
md += 'Review below, override any verdict you disagree with, then approve Phase 2 (apply). '
md += '(The earlier conservative pass is preserved in `report-conservative.md`.)\n\n'
md += '## Grand totals\n\n' + grandTotalsTable + '\n'
md += 'Of ' + totBoxes + ' boxes: ' + totCut + ' proposed CUT (' + (totBoxes ? Math.round(1000 * totCut / totBoxes) / 10 : 0) + '%), ' + totTrim + ' TRIM, ' + totKeep + ' KEEP. Plus ' + totFluff + ' prose-fluff passages flagged.\n\n'
md += '---\n'

for (const r of present) {
  const c = r.boxCounts
  md += '\n## ' + r._title + ' — `' + r._file + '`\n'
  md += 'Boxes: ' + (r.totalBoxes || 0) + ' total → CUT ' + c.cut + ' · TRIM ' + c.trim + ' · KEEP ' + c.keep + '  |  fluff flagged: ' + ((r.fluffFindings || []).length) + '\n'
  if (r.skepticNotes && r.skepticNotes.length) md += '\n_Skeptic adjustments:_ ' + r.skepticNotes.map(esc).join('; ') + '\n'
  const bf = r.boxFindings || []
  if (bf.length) {
    md += '\n| Locator | Type | Verdict | Reason | Trim note |\n|---|---|---|---|---|\n'
    for (const b of bf) md += '| ' + esc(b.locator) + ' | ' + esc(b.boxType) + ' | ' + b.verdict + ' | ' + esc(b.reason) + ' | ' + esc(b.trimNote) + ' |\n'
  } else {
    md += '\n_No box CUT/TRIM proposed._\n'
  }
  const ff = r.fluffFindings || []
  if (ff.length) {
    md += '\n**Prose fluff:**\n\n| Locator | Type | Action | Change | Reason |\n|---|---|---|---|---|\n'
    for (const f of ff) {
      const change = f.action === 'DELETE' ? '~~' + esc(f.snippet) + '~~ (delete)' : esc(f.snippet) + ' → ' + esc(f.proposed)
      md += '| ' + esc(f.locator) + ' | ' + esc(f.fluffType) + ' | ' + f.action + ' | ' + change + ' | ' + esc(f.reason) + ' |\n'
    }
  }
}

fs.writeFileSync(findingsPath, JSON.stringify(present, null, 2))
fs.writeFileSync(reportPath, md)
console.log('Regenerated. Totals: boxes=' + totBoxes + ' cut=' + totCut + ' trim=' + totTrim + ' keep=' + totKeep + ' fluff=' + totFluff)
