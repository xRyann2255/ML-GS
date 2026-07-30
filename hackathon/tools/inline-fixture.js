/* inline-fixture.js — splice a verified.json into the demo bundle's data block.
 *
 *   node tools/inline-fixture.js [json] [html]
 *   defaults: fixtures/verified.sample.json  demo/trailhead-demo.html
 *
 * The demo used to carry its data as a hand-edited JS object literal, which
 * meant the fixture and the page could drift. This makes the fixture the single
 * source of truth: edit fixtures/verified.sample.json, re-run this, re-run the
 * gate checks. It is a stand-in for what stage 5 (RENDER) will do properly —
 * same substitution, generated HTML shell instead of a checked-in one.
 *
 * Only the `const D = { … };` block is touched. Everything else is byte-identical.
 */
const fs = require('fs');
const path = require('path');

const json = process.argv[2] || path.join(__dirname, '..', 'fixtures', 'verified.sample.json');
const html = process.argv[3] || path.join(__dirname, '..', 'demo', 'trailhead-demo.html');
for (const f of [json, html])
  if (!fs.existsSync(f)) { console.error('not found:', f); process.exit(2); }

const D = JSON.parse(fs.readFileSync(json, 'utf8'));
const src = fs.readFileSync(html, 'utf8');

const START = 'const D = {';
const a = src.indexOf(START);
if (a < 0) { console.error('data block start marker not found'); process.exit(2); }

// End of the block is the `};` that closes it, found by brace-matching from the
// opening `{` so nothing in the payload can be mistaken for the terminator.
const open = src.indexOf('{', a);
let depth = 0, end = -1, inStr = false, quote = '', esc = false;
for (let i = open; i < src.length; i++) {
  const ch = src[i];
  if (inStr) {
    if (esc) esc = false;
    else if (ch === '\\') esc = true;
    else if (ch === quote) inStr = false;
    continue;
  }
  if (ch === '"' || ch === "'" || ch === '`') { inStr = true; quote = ch; continue; }
  if (ch === '{') depth++;
  else if (ch === '}') { depth--; if (depth === 0) { end = i; break; } }
}
if (end < 0) { console.error('unbalanced braces in data block'); process.exit(2); }

// JSON is valid JS, so the payload goes in verbatim. 1-space indent keeps the
// bundle a little smaller without making it unreadable.
const out = src.slice(0, a) + 'const D = ' + JSON.stringify(D, null, 1) + src.slice(end + 1);
fs.writeFileSync(html, out);

const kb = n => (n / 1024).toFixed(1) + ' KB';
console.log(`\n${path.relative(process.cwd(), json)}  ->  ${path.relative(process.cwd(), html)}`);
console.log(`  data block  ${kb(end + 1 - a)}  ->  ${kb(JSON.stringify(D, null, 1).length)}`);
console.log(`  bundle      ${kb(src.length)}  ->  ${kb(out.length)}\n`);
