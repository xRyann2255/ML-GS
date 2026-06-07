// Build per-chapter re-evaluation input files for the intuition-CUT boxes.
// Each file lists that chapter's intuition boxes currently marked CUT, with a
// stable id (chId::k) matching their order in findings.json's boxFindings.
const fs = require('fs')
const path = require('path')

const DIR = __dirname
const REEVAL = path.join(DIR, 'reeval')
fs.mkdirSync(REEVAL, { recursive: true })

const present = JSON.parse(fs.readFileSync(path.join(DIR, 'findings.json'), 'utf8'))

const manifest = []
for (const ch of present) {
  const bf = ch.boxFindings || []
  const boxes = []
  let k = 0
  for (const b of bf) {
    if (b.verdict === 'CUT' && b.boxType === 'intuition') {
      boxes.push({ id: ch._id + '::' + k, locator: b.locator, title: b.title || '', currentCutReason: b.reason })
    }
    if (b.verdict === 'CUT' && b.boxType === 'intuition') k++
  }
  if (boxes.length) {
    const obj = { chId: ch._id, file: ch._file, title: ch._title, boxes }
    fs.writeFileSync(path.join(REEVAL, ch._id + '.json'), JSON.stringify(obj, null, 2))
    manifest.push({ id: ch._id, file: ch._file, title: ch._title, count: boxes.length })
  }
}
fs.writeFileSync(path.join(REEVAL, '_manifest.json'), JSON.stringify(manifest, null, 2))
console.log('Wrote ' + manifest.length + ' reeval files; total intuition-CUT boxes = ' + manifest.reduce((a, m) => a + m.count, 0))
console.log(JSON.stringify(manifest.map((m) => m.id)))
