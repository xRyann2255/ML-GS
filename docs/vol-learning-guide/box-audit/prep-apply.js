// Build per-chapter apply input files from findings.json.
// Each file lists that chapter's CUT boxes, TRIM boxes, and fluff edits.
const fs = require('fs')
const path = require('path')

const DIR = __dirname
const APPLY = path.join(DIR, 'apply')
fs.mkdirSync(APPLY, { recursive: true })

const present = JSON.parse(fs.readFileSync(path.join(DIR, 'findings.json'), 'utf8'))

const manifest = []
for (const ch of present) {
  const bf = ch.boxFindings || []
  const cuts = bf.filter((b) => b.verdict === 'CUT')
  const trims = bf.filter((b) => b.verdict === 'TRIM')
  const fluff = ch.fluffFindings || []
  const obj = { chId: ch._id, file: ch._file, title: ch._title, cuts, trims, fluff }
  fs.writeFileSync(path.join(APPLY, ch._id + '.json'), JSON.stringify(obj, null, 2))
  manifest.push({ id: ch._id, file: ch._file, title: ch._title, cuts: cuts.length, trims: trims.length, fluff: fluff.length })
}
fs.writeFileSync(path.join(APPLY, '_manifest.json'), JSON.stringify(manifest, null, 2))
const tot = manifest.reduce((a, m) => ({ cuts: a.cuts + m.cuts, trims: a.trims + m.trims, fluff: a.fluff + m.fluff }), { cuts: 0, trims: 0, fluff: 0 })
console.log('Wrote ' + manifest.length + ' apply files. Totals: cuts=' + tot.cuts + ' trims=' + tot.trims + ' fluff=' + tot.fluff)
