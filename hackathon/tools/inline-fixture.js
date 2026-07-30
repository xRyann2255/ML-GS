/* inline-fixture.js — splice verified.json payloads into the demo bundle.
 *
 *   node tools/inline-fixture.js                 rebuild from the manifest below
 *   node tools/inline-fixture.js a.json b.json   override the payload files, in
 *                                                manifest order
 *
 * The demo used to carry its data as a hand-edited JS object literal, which
 * meant the fixture and the page could drift. This makes the fixtures the single
 * source of truth: edit the JSON, re-run this, re-run the gate checks. It is a
 * stand-in for what stage 5 (RENDER) will do properly — same substitution,
 * generated HTML shell instead of a checked-in one.
 *
 * The demo bundle carries one payload per repo so the walkthroughs can share a
 * renderer instead of shipping as two near-identical files. A real generated
 * artifact carries exactly one; nothing below `D` in the renderer knows the
 * difference. Only the region between the DATA markers is touched.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const START = '/* ==== TRAILHEAD-DATA-START ==== */';
const END = '/* ==== TRAILHEAD-DATA-END ==== */';

const MANIFEST = [
  { key: 'payments-core', json: 'fixtures/verified.sample.json', synthetic: true },
  { key: 'ML-GS', json: 'fixtures/verified.ml-gs.json', synthetic: false },
];

const override = process.argv.slice(2).filter(a => a.endsWith('.json'));
const htmlArg = process.argv.slice(2).find(a => a.endsWith('.html'));
const html = htmlArg || path.join(ROOT, 'demo/trailhead-demo.html');

const manifest = MANIFEST.map((m, i) => ({ ...m, json: override[i] || path.join(ROOT, m.json) }));

for (const m of [...manifest.map(m => m.json), html])
  if (!fs.existsSync(m)) { console.error('not found:', m); process.exit(2); }

const src = fs.readFileSync(html, 'utf8');
const a = src.indexOf(START), b = src.indexOf(END);
if (a < 0 || b < 0) { console.error('data markers not found (start=%d end=%d)', a, b); process.exit(2); }

const entries = manifest.map(m => {
  const data = JSON.parse(fs.readFileSync(m.json, 'utf8'));
  if (data.repo.name !== m.key)
    console.log(`  note  ${path.basename(m.json)} repo.name is "${data.repo.name}", manifest key is "${m.key}"`);
  // JSON is valid JS, so the payload goes in verbatim. 1-space indent keeps the
  // bundle a little smaller without making it unreadable.
  return ' ' + JSON.stringify(m.key) + ': ' + JSON.stringify(data, null, 1);
}).join(',\n');

const synth = manifest.filter(m => m.synthetic).map(m => JSON.stringify(m.key) + ':true').join(',');

const block = START + '\n'
  + 'const BUNDLES = {\n' + entries + '\n};\n'
  + '/* Demo-only: which of these are synthetic fixtures rather than real repos.\n'
  + '   Kept outside the payloads so each stays a pure verified.json. */\n'
  + 'const SYNTHETIC = {' + synth + '};\n'
  + END;

const out = src.slice(0, a) + block + src.slice(b + END.length);
fs.writeFileSync(html, out);

const kb = n => (n / 1024).toFixed(1) + ' KB';
console.log(`\n${manifest.length} payload(s)  ->  ${path.relative(process.cwd(), html)}`);
for (const m of manifest) console.log(`  ${m.key.padEnd(16)} ${path.relative(process.cwd(), m.json)}`);
console.log(`  data block  ${kb(b - a)}  ->  ${kb(block.length)}`);
console.log(`  bundle      ${kb(src.length)}  ->  ${kb(out.length)}\n`);
