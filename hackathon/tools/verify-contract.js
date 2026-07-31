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
 *
 * trailhead/verified@3 additions (all additive; an @2 payload passes as-is):
 *   - glossary: slug ids, unique, definitions present, anchors hashed
 *   - explicit [[id|label]] markers resolve to a glossary entry
 *   - map columns sit inside the viewBox; tour steps name real nodes
 *   - node role / key_files / concepts / reads / feeds are well typed,
 *     node anchors hashed, @3 nodes carry an explicit numeric h
 *   - stats blocks: v/l strings, color limited to ok|inf|bad
 *   - no em or en dash in authored strings (@3 only; files and command
 *     out are exempt: repo bytes and real capture are never rewritten)
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const file = process.argv[2] || path.join(__dirname, '..', 'demo', 'trailhead-demo.html');
if (!fs.existsSync(file)) { console.error('not found:', file); process.exit(2); }
const src = fs.readFileSync(file, 'utf8');

// A bare verified.json is one payload; a demo bundle may carry several, one per
// repo, so every one of them is checked. Extraction keys off explicit markers —
// it used to key off a prose comment, which made the gate hostage to its wording.
let PAYLOADS;
if (file.endsWith('.json')) {
  PAYLOADS = [['(file)', JSON.parse(src)]];
} else {
  const START = '/* ==== TRAILHEAD-DATA-START ==== */';
  const END = '/* ==== TRAILHEAD-DATA-END ==== */';
  const a = src.indexOf(START), b = src.indexOf(END);
  if (a < 0 || b < 0) { console.error('data markers not found (start=%d end=%d)', a, b); process.exit(2); }
  const raw = src.slice(a + START.length, b);
  const m = raw.indexOf('const BUNDLES =');
  if (m < 0) { console.error('BUNDLES declaration not found between the data markers'); process.exit(2); }
  // brace-match rather than search for '};' — the SYNTHETIC map that follows
  // ends the same way, and a string search happily walks past the real close
  const open = raw.indexOf('{', m);
  let depth = 0, close = -1, inStr = false, q = '', esc = false;
  for (let i = open; i < raw.length; i++) {
    const c = raw[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === q) inStr = false;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { inStr = true; q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) { close = i; break; } }
  }
  if (close < 0) { console.error('unbalanced braces in BUNDLES'); process.exit(2); }
  PAYLOADS = Object.entries(eval('(' + raw.slice(open, close + 1) + ')'));
  if (!PAYLOADS.length) { console.error('no payloads in BUNDLES'); process.exit(2); }
}

let fail = 0;
const bad = m => { console.log('  FAIL  ' + m); fail++; };

console.log(`\n${path.relative(process.cwd(), file)}`);
if (PAYLOADS.length > 1) console.log(`${PAYLOADS.length} payloads: ${PAYLOADS.map(p => p[0]).join(', ')}`);

for (const [label, payload] of PAYLOADS) check(label, payload);

console.log(fail ? `\n${fail} FAILURE(S)\n` : '\nALL ANCHOR + CONTRACT CHECKS PASS\n');
process.exit(fail ? 1 : 0);

function check(LABEL, D) {
if (PAYLOADS.length > 1) console.log(`\n--- ${LABEL} ---`);

const stops = D.tracks.flatMap(t => t.stops);

// The contract version was never asserted, which made a silent bump possible.
const KNOWN = ['trailhead/verified@1', 'trailhead/verified@2', 'trailhead/verified@3'];
if (!KNOWN.includes(D.contract)) bad(`unknown contract version: ${JSON.stringify(D.contract)}`);
// @3-only assertions key off this. Everything @3 added is additive: the new
// fields are validated wherever they appear, but rules that would re-litigate
// frozen @2 payloads (the dash policy, explicit node heights) apply only when
// the payload says it is @3.
const V3 = D.contract === 'trailhead/verified@3';

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

/* @3: authored-text policy. Two rules, both scoped to strings a human or a
 * model WROTE, never to bytes the repo or a command produced: the files map
 * is the repo's own source (hash integrity wins) and command `out` is real
 * capture (non-negotiable #4), so both are exempt by design.
 *
 *   1. No em or en dash (U+2014 / U+2013) in authored strings. Scoped to @3
 *      payloads: the frozen @2 fixtures predate the policy and stay valid.
 *   2. An explicit [[id|label]] glossary marker must name a glossary entry.
 *      The renderer degrades an unknown id to the plain label, so an
 *      unresolvable marker is silent formatting loss; the gate makes it
 *      loud. Bare [[Label]] markers degrade by design and are not checked.
 *      Checked on every contract version: no @2 fixture carries a marker,
 *      and one that appeared would be an authoring bug worth failing.
 *
 * `noRefs` marks surfaces the renderer escapes rather than enriches
 * (glossary defs, checkpoint provenance / explanation): a marker there is
 * inert text, so only the dash rule applies. */
const glossIds = new Set((Array.isArray(D.glossary) ? D.glossary : []).map(g => g && g.id));
let refsSeen = 0;
function authored(s, who, noRefs) {
  if (typeof s !== 'string') return;
  if (V3 && /[–—]/.test(s))
    bad(`${who}: authored text contains an em or en dash (banned in @3 authored strings)`);
  if (noRefs) return;
  for (const m of s.matchAll(/\[\[([a-z0-9-]+)\|/g)) {
    refsSeen++;
    if (!glossIds.has(m[1]))
      bad(`${who}: explicit glossary marker [[${m[1]}|...]] resolves to no glossary entry`);
  }
}

// @3: glossary. Slug ids, unique; every entry defines its term; the anchor is
// optional and, when present, is a standard anchor: bundled, whole, hashed.
// (Stage 4 drops a failed glossary ANCHOR but keeps the definition, ledger id
// g-<slug>; what ships here must therefore always pass in full.)
let gloss = 0;
if (D.glossary !== undefined) {
  if (!Array.isArray(D.glossary)) bad('glossary must be an array');
  const gseen = new Set();
  for (const g of Array.isArray(D.glossary) ? D.glossary : []) {
    gloss++;
    const who = `glossary/${(g && g.id) || '(no id)'}`;
    if (!g || typeof g.id !== 'string' || !/^[a-z0-9-]+$/.test(g.id))
      bad(`${who}: id must be a slug of [a-z0-9-]`);
    else if (gseen.has(g.id)) bad(`${who}: duplicate glossary id`);
    else gseen.add(g.id);
    if (!g || typeof g.term !== 'string' || !g.term.trim()) bad(`${who}: no term`);
    if (!g || typeof g.def !== 'string' || !g.def.trim()) bad(`${who}: no definition`);
    if (g) authored(g.def, `${who} def`, true);
    if (g && g.anchor) anchor(g.anchor, who);
  }
}

let claims = 0, inferred = 0, cps = 0, cmds = 0, preds = 0, links = 0, lsteps = 0;
for (const s of stops) {
authored(s.lede, `lede ${s.id}`);
for (const bl of s.blocks) {
  switch (bl.type) {
    case 'prose':
      for (const c of bl.claims) {
        claims++;
        authored(c.text, c.id);
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
      authored(bl.provenance, `${bl.id} provenance`, true);
      authored(bl.explanation, `${bl.id} explanation`, true);
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
    case 'callout':
      authored(bl.text, `callout "${bl.title}"`);
      // @2: optional `links[]` pointing at where to install what `text` names.
      // The renderer whitelists the scheme at paint time and shows a refusal chip
      // for anything else; this asserts the payload never carries one that would
      // be refused, so that chip appearing on screen can only mean a bug here.
      for (const l of bl.links || []) {
        links++;
        if (!l.label || !String(l.label).trim()) bad(`callout "${bl.title}": link with no label`);
        if (!/^https?:\/\//i.test(l.href || ''))
          bad(`callout "${bl.title}": link href ${JSON.stringify(l.href)} is not http(s) — render would refuse it`);
      }
      if (bl.linknote !== undefined && !bl.links) bad(`callout "${bl.title}": linknote with no links`);
      break;
    case 'lineage': {
      // A lineage step claiming VERIFIED must be able to prove it, exactly as a
      // prose claim must. Two exemptions are deliberate: a RUNTIME step is
      // evidenced by captured output rather than a line range, and a DERIVED
      // step may or may not cite one. INFERRED must not — an anchor is what
      // makes a step render as evidenced.
      const STATUS = new Set(['verified', 'derived', 'inferred']);
      const EVIDENCE = new Set(['source', 'runtime', 'test', 'config', 'graph', 'git', 'inference']);
      const ents = bl.entities || [];
      if (!ents.length) bad('lineage block carries no entities');
      const seen = new Set();
      for (const e of ents) {
        const who = `lineage/${e.id || '(no id)'}`;
        if (!e.id) bad(`${who}: entity has no id`);
        if (seen.has(e.id)) bad(`${who}: duplicate entity id`);
        seen.add(e.id);
        if (!e.name) bad(`${who}: entity has no name`);
        if (!e.meaning) bad(`${who}: entity has no business meaning`);
        if (!Array.isArray(e.steps) || !e.steps.length) bad(`${who}: entity has no steps`);
        for (const [i, s] of (e.steps || []).entries()) {
          const sw = `${who}[${i}] ${s.stage || '?'}`;
          lsteps++;
          if (!s.stage) bad(`${sw}: step has no stage`);
          if (!s.label) bad(`${sw}: step has no label`);
          if (!s.description) bad(`${sw}: step has no description`);
          if (!EVIDENCE.has(s.evidence_type)) bad(`${sw}: unknown evidence_type ${JSON.stringify(s.evidence_type)}`);
          if (!STATUS.has(s.status)) bad(`${sw}: unknown status ${JSON.stringify(s.status)}`);
          if (s.status === 'inferred' && s.anchor)
            bad(`${sw}: inferred step carries an anchor — it would render as evidenced`);
          if (s.status === 'verified' && s.evidence_type !== 'runtime' && !s.anchor)
            bad(`${sw}: verified step carries no anchor`);
          if (s.anchor) anchor(s.anchor, sw);
        }
        if (e.failure_mode) {
          if (!e.failure_mode.text) bad(`${who}: failure_mode has no text`);
          if (!STATUS.has(e.failure_mode.status)) bad(`${who}: failure_mode status ${JSON.stringify(e.failure_mode.status)}`);
          if (e.failure_mode.anchor) anchor(e.failure_mode.anchor, `${who}/failure`);
        }
        if (e.boundary) {
          if (!e.boundary.text) bad(`${who}: boundary has no text`);
          // A boundary is by definition what could not be established here.
          // Calling one verified would claim knowledge of what lies outside.
          if (e.boundary.status === 'verified') bad(`${who}: a repository boundary cannot be verified`);
        }
        if (e.tests !== undefined && !Array.isArray(e.tests)) bad(`${who}: tests must be an array`);
      }
      break;
    }
    case 'stats':
      // @3: cover / dive tiles. Values are computed by COMPOSE from
      // survey.json, never by the model, so the gate checks shape, not truth:
      // `v` and `l` required strings, `s` and `of` optional strings, `color`
      // one of the three semantic names the renderer's CSS defines.
      if (!Array.isArray(bl.items) || !bl.items.length) bad('stats block with no items');
      for (const it of Array.isArray(bl.items) ? bl.items : []) {
        const who = `stats "${(it && it.l) || '(no label)'}"`;
        if (!it || typeof it.v !== 'string' || !it.v.trim()) bad(`${who}: v must be a non-empty string`);
        if (!it || typeof it.l !== 'string' || !it.l.trim()) bad(`${who}: l must be a non-empty string`);
        if (it && it.s !== undefined && typeof it.s !== 'string') bad(`${who}: s must be a string`);
        if (it && it.of !== undefined && typeof it.of !== 'string') bad(`${who}: of must be a string`);
        if (it && it.color !== undefined && !['ok', 'inf', 'bad'].includes(it.color))
          bad(`${who}: color ${JSON.stringify(it.color)} is not ok|inf|bad`);
      }
      break;
    case 'graph': case 'ledger': break;
    default: bad(`unknown block type: ${bl.type}`);
  }
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

// @3 board additions. All optional, all validated where they appear; the
// renderer's viewBox fallbacks (900x400) are mirrored here so a column check
// means the same thing the SVG will draw.
const W = D.map.w || 900;
for (const c of D.map.columns || []) {
  const who = `map column ${JSON.stringify((c && c.label) || '(no label)')}`;
  if (!c || typeof c.label !== 'string' || !c.label.trim()) bad(`${who}: no label`);
  if (!c || typeof c.x !== 'number' || c.x < 0 || c.x > W)
    bad(`${who}: x ${c && c.x} outside the 0-${W} viewBox`);
}
const tourSeen = new Set();
for (const t of D.map.tour || []) {
  const who = `tour step ${(t && t.id) || '(no id)'}`;
  if (!t || !nodeIds.has(t.id)) bad(`${who}: id is not a node on the board`);
  else if (tourSeen.has(t.id)) bad(`${who}: duplicate tour step`);
  else tourSeen.add(t.id);
  if (!t || typeof t.text !== 'string' || !t.text.trim()) bad(`${who}: no text`);
  if (t) authored(t.text, who);
}
if (D.map.note) authored(D.map.note.text, 'map note');
for (const n of D.map.nodes) {
  const who = `node ${n.id}`;
  // @3 nodes carry their height; the renderer stops deriving it. An @2
  // payload has no h and the renderer's fallback still draws it.
  if (V3 && typeof n.h !== 'number') bad(`${who}: @3 nodes carry an explicit numeric h`);
  if (n.role !== undefined) {
    if (!Array.isArray(n.role) || !n.role.length || n.role.some(p => typeof p !== 'string' || !p.trim()))
      bad(`${who}: role must be a non-empty array of paragraph strings`);
    else n.role.forEach((p, i) => authored(p, `${who} role[${i}]`));
  }
  if (n.key_files !== undefined) {
    if (!Array.isArray(n.key_files)) bad(`${who}: key_files must be an array`);
    else for (const k of n.key_files) {
      if (!k || typeof k.file !== 'string' || !k.file.trim() || typeof k.purpose !== 'string' || !k.purpose.trim())
        bad(`${who}: every key_files entry needs a file and a purpose`);
      else authored(k.purpose, `${who} key_files ${k.file}`);
    }
  }
  if (n.concepts !== undefined &&
      (!Array.isArray(n.concepts) || n.concepts.some(c => typeof c !== 'string' || !c.trim())))
    bad(`${who}: concepts must be an array of strings`);
  if (n.reads !== undefined) {
    if (typeof n.reads !== 'string') bad(`${who}: reads must be a string`);
    else authored(n.reads, `${who} reads`);
  }
  if (n.feeds !== undefined) {
    if (typeof n.feeds !== 'string') bad(`${who}: feeds must be a string`);
    else authored(n.feeds, `${who} feeds`);
  }
  if (n.anchor) anchor(n.anchor, who);
}

console.log(`rendered claims ${claims} (inferred ${inferred}) | checkpoints ${cps} | predictions ${preds} | lineage steps ${lsteps} | commands ${cmds} | links ${links} | dropped ${D.dropped.length}`);
if (gloss || refsSeen || (D.map.tour || []).length)
  console.log(`glossary ${gloss} | glossary refs ${refsSeen} | tour steps ${(D.map.tour || []).length} | columns ${(D.map.columns || []).length}`);
console.log(`anchors sha256-verified ${hashed}`);
}
