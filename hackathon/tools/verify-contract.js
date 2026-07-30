/* verify-contract.js — checks a verified.json payload against the contract.
 *
 *   node tools/verify-contract.js [path]   default: demo/trailhead-demo.html
 *
 * Accepts either an HTML bundle (data is scraped out of the inlined `const D`)
 * or a bare verified.json — so the same assertions gate the demo today and the
 * generator's stage-4 output tomorrow. Covers docs/verified-contract.md and
 * acceptance tests 3–6 in docs/walkthrough-spec.md §8:
 *
 *   - every rendered claim resolves to a real line range in the bundle
 *   - every anchor's sha256 matches the bundled excerpt it points at
 *   - focus lines fall inside their anchor
 *   - inferred claims carry no anchor (they must not look verified)
 *   - dropped claims appear nowhere but the ledger
 *   - failing commands always carry a BROKEN banner
 *   - checkpoint answer keys are well formed and cite provenance
 *   - the top-bar report matches what the page actually shows
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const file = process.argv[2] || path.join(__dirname, '..', 'demo', 'trailhead-demo.html');
if (!fs.existsSync(file)) { console.error('not found:', file); process.exit(2); }
const src = fs.readFileSync(file, 'utf8');

let D;
if (file.endsWith('.json')) {
  D = JSON.parse(src);
} else {
  // Extract the inlined data object. Markers avoid literal newlines so the search
  // is CRLF-agnostic.
  const a = src.indexOf('const D = {');
  const b = src.indexOf('RENDER — knows only');
  if (a < 0 || b < 0) { console.error('data markers not found (a=%d b=%d)', a, b); process.exit(2); }
  const raw = src.slice(src.indexOf('{', a), b).replace(/\/\*[\s\S]*$/, '').trim().replace(/;\s*$/, '');
  D = eval('(' + raw + ')');
}

let fail = 0;
const bad = m => { console.log('  FAIL  ' + m); fail++; };
const stops = D.tracks.flatMap(t => t.stops);

// The contract version was never asserted, which made a silent bump possible.
const KNOWN = ['trailhead/verified@1', 'trailhead/verified@2'];
if (!KNOWN.includes(D.contract)) bad(`unknown contract version: ${JSON.stringify(D.contract)}`);

console.log(`\n${path.relative(process.cwd(), file)}`);
console.log(`tracks ${D.tracks.length} | stops ${stops.length} | bundled files ${Object.keys(D.files).length}\n`);

const ids = stops.map(s => s.id);
if (new Set(ids).size !== ids.length) bad('duplicate stop ids');

// The excerpt an anchor points at: source lines start..end joined by \n, no
// trailing newline and no line numbers. sha256 is taken over exactly this —
// see docs/verified-contract.md. Stage 4 recomputes it from the file on disk;
// here we recompute it from the bundle, which proves the shipped excerpt is
// still the one that was hashed at generation time.
function excerptOf(an, f) {
  const out = [];
  for (let n = an.start; n <= an.end; n++) out.push(f[n]);
  return out.join('\n');
}

let hashed = 0;
function anchor(an, who) {
  if (!an) return bad(`${who}: no anchor`);
  const f = D.files[an.file];
  if (!f) return bad(`${who}: file not bundled -> ${an.file}`);
  const ls = Object.keys(f).map(Number), lo = Math.min(...ls), hi = Math.max(...ls);
  if (an.start < lo || an.end > hi)
    bad(`${who}: range ${an.start}-${an.end} outside bundled ${lo}-${hi} in ${an.file}`);
  for (const n of an.focus || [])
    if (n < an.start || n > an.end) bad(`${who}: focus line ${n} outside ${an.start}-${an.end}`);
  let whole = true;
  for (let n = an.start; n <= an.end; n++)
    if (!(n in f)) { bad(`${who}: line ${n} missing from ${an.file}`); whole = false; }

  if (!an.sha256) return bad(`${who}: anchor carries no sha256 — nothing to verify against`);
  if (!whole) return;
  const got = crypto.createHash('sha256').update(excerptOf(an, f), 'utf8').digest('hex');
  if (got !== an.sha256)
    bad(`${who}: sha256 mismatch on ${an.file}:${an.start}-${an.end}\n          recorded ${an.sha256}\n          bundled  ${got}`);
  else hashed++;
}

let claims = 0, inferred = 0, cps = 0, cmds = 0, preds = 0;
for (const s of stops) for (const bl of s.blocks) {
  switch (bl.type) {
    case 'prose':
      for (const c of bl.claims) {
        claims++;
        if (c.status === 'inferred') {
          inferred++;
          if (c.anchor) bad(`${c.id}: inferred claim carries an anchor — it would render as verified`);
        } else anchor(c.anchor, c.id);
      }
      break;
    case 'trace':
      bl.steps.forEach((st, i) => {
        anchor(st.anchor, `trace hop ${i + 1}`);
        // @2: a hop may ask the reader to predict the next file. The key is the
        // NEXT hop's anchor, so the last hop can never carry one.
        if (st.predict === undefined) return;
        preds++;
        if (typeof st.predict !== 'string' || !st.predict.trim())
          bad(`trace hop ${i + 1}: predict must be a non-empty question`);
        if (!bl.steps[i + 1])
          bad(`trace hop ${i + 1}: predict on the last hop has no next anchor to key against`);
        else if (bl.steps[i + 1].anchor.file === st.anchor.file)
          bad(`trace hop ${i + 1}: predict is trivial, next hop is the same file`);
      });
      break;
    case 'excerpt':
      anchor(bl.anchor, 'excerpt');
      break;
    case 'command':
      cmds++;
      if (bl.exit !== 0 && !bl.broken) bad(`${bl.cmd}: failing command with no BROKEN banner`);
      if (!bl.env) bad(`${bl.cmd}: no environment note`);
      if (!bl.out) bad(`${bl.cmd}: no captured output`);
      // @2: optional prediction. The key is derived from `exit` by the renderer,
      // never authored, so there is no answer field here to disagree with the run.
      if (bl.predict !== undefined) {
        preds++;
        if (typeof bl.predict !== 'string' || !bl.predict.trim())
          bad(`${bl.cmd}: predict must be a non-empty question`);
        if ('answer' in bl)
          bad(`${bl.cmd}: command predictions must not carry an answer — the captured exit code is the key`);
      }
      break;
    case 'checkpoint':
      cps++;
      if (!bl.provenance) bad(`${bl.id}: no answer-key provenance`);
      if (!bl.explanation) bad(`${bl.id}: no explanation`);
      if (bl.kind === 'single' && !(bl.answer >= 0 && bl.answer < bl.options.length))
        bad(`${bl.id}: answer index out of range`);
      if (bl.kind === 'order') {
        const want = [...Array(bl.options.length)].map((_, i) => i + 1).join();
        if (bl.answer.length !== bl.options.length) bad(`${bl.id}: answer/options length mismatch`);
        if ([...bl.answer].sort((x, y) => x - y).join() !== want)
          bad(`${bl.id}: answer is not a permutation of 1..n`);
      }
      break;
    case 'table':
      if (bl.rows.some(r => r.length !== bl.columns.length)) bad('table row/column mismatch');
      break;
    case 'graph': case 'callout': case 'ledger': break;
    default: bad(`unknown block type: ${bl.type}`);
  }
}

const rendered = new Set(stops.flatMap(s =>
  s.blocks.filter(x => x.type === 'prose').flatMap(x => x.claims.map(c => c.id))));
for (const d of D.dropped) {
  if (rendered.has(d.id)) bad(`${d.id}: dropped claim is rendered in the course`);
  if (!d.reason) bad(`${d.id}: dropped with no reason`);
}
if (D.dropped.length !== D.report.dropped)
  bad(`report says ${D.report.dropped} dropped, ledger lists ${D.dropped.length}`);

const failing = stops.flatMap(s => s.blocks).filter(x => x.type === 'command' && x.exit !== 0).length;
if (failing !== D.report.failed)
  bad(`report says ${D.report.failed} failing commands, page shows ${failing}`);

// graph integrity
const nodeIds = new Set(D.map.nodes.map(n => n.id));
for (const e of D.map.edges) {
  if (!nodeIds.has(e.a)) bad(`edge references unknown node ${e.a}`);
  if (!nodeIds.has(e.b)) bad(`edge references unknown node ${e.b}`);
}

console.log(`rendered claims ${claims} (inferred ${inferred}) | checkpoints ${cps} | predictions ${preds} | commands ${cmds} | dropped ${D.dropped.length}`);
console.log(`anchors sha256-verified ${hashed}`);
console.log(fail ? `\n${fail} FAILURE(S)\n` : '\nALL ANCHOR + CONTRACT CHECKS PASS\n');
process.exit(fail ? 1 : 0);
