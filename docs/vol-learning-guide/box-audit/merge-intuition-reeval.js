// Apply intuition re-evaluation decisions to findings.json.
// For each intuition box currently marked CUT (id = chId::k, k = its index among
// that chapter's intuition-CUT entries, same scheme as prep), apply the decision:
//   KEEP -> remove the finding (box is restored, no longer cut)
//   TRIM -> convert verdict to TRIM with the given trimNote
//   CUT  -> leave as a cut
// Usage: node merge-intuition-reeval.js reeval/decisions.json
const fs = require('fs')
const path = require('path')

const DIR = __dirname
const decisionsPath = process.argv[2] || path.join(DIR, 'reeval', 'decisions.json')

const present = JSON.parse(fs.readFileSync(path.join(DIR, 'findings.json'), 'utf8'))
let dec = JSON.parse(fs.readFileSync(decisionsPath, 'utf8'))
if (dec.results) dec = dec.results // accept {results:[...]} or [...]

const byId = new Map()
for (const r of dec) for (const d of (r.decisions || [])) byId.set(d.id, d)

let removed = 0, converted = 0, upheld = 0, missing = 0
const missingIds = []

for (const ch of present) {
  const out = []
  let k = 0
  for (const b of (ch.boxFindings || [])) {
    if (b.verdict === 'CUT' && b.boxType === 'intuition') {
      const id = ch._id + '::' + k
      k++
      const d = byId.get(id)
      if (!d) { missing++; missingIds.push(id); out.push(b); continue }
      if (d.verdict === 'KEEP') { removed++; continue }
      if (d.verdict === 'TRIM') {
        converted++
        out.push({
          locator: b.locator,
          boxType: 'intuition',
          title: b.title || '',
          verdict: 'TRIM',
          reason: 'Restored to TRIM (plain-English aid for a hard equation): ' + (d.reason || ''),
          trimNote: d.trimNote || '',
        })
        continue
      }
      // CUT upheld
      upheld++
      out.push(b)
    } else {
      out.push(b)
    }
  }
  ch.boxFindings = out
}

fs.writeFileSync(path.join(DIR, 'findings.json'), JSON.stringify(present, null, 2))
console.log('Intuition re-eval merged into findings.json:')
console.log('  restored to KEEP (removed from cuts): ' + removed)
console.log('  converted CUT -> TRIM:                ' + converted)
console.log('  CUT upheld:                           ' + upheld)
console.log('  ids with no decision (left as CUT):   ' + missing + (missingIds.length ? ' ' + JSON.stringify(missingIds) : ''))
