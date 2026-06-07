// Check which of ch06's expected CUT boxes are still present in the edited chapter.
const fs = require('fs')
const path = require('path')
const cuts = JSON.parse(fs.readFileSync(path.join(__dirname, 'apply', 'ch06.json'), 'utf8')).cuts
const tex = fs.readFileSync('C:/Users/RyanPC/Documents/Projects/ML-GS/vol-learning-guide/chapters/06-har-model.tex', 'utf8')

const norm = (s) => s.replace(/[‘’′'`]/g, '').replace(/\s+/g, ' ').trim().toLowerCase()
const ntex = norm(tex)

let present = 0
for (const c of cuts) {
  const parts = c.locator.split('—') // em dash
  let tail = parts[parts.length - 1].replace(/\(note[^)]*\)/i, '')
  const key = norm(tail).split(' ').filter(Boolean).slice(0, 7).join(' ')
  const hit = key && ntex.includes(key)
  if (hit) { present++; console.log('STILL PRESENT  [' + c.boxType + '] "' + c.title + '"  ::  ' + key) }
}
console.log('---')
console.log('expected cuts: ' + cuts.length + ' ; still present (missed): ' + present)
