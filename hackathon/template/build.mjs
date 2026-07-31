// build.mjs : assemble the hand-built target walkthrough.
//
// The same discipline as the real pipeline, in miniature:
//   - authors write claims with VERBATIM QUOTES, never line numbers
//   - this script resolves each quote to a line range against the snapshot,
//     computes the sha256 the contract requires, bundles the excerpt lines,
//     and DELETES (ledger + on-screen count) any claim whose quote fails
//   - command output is spliced from real captured runs, never authored
//   - the finished HTML is scanned: no em or en dash anywhere, no external
//     URL anywhere, payload token replaced, size cap respected
//
// Usage: node build.mjs        (from hackathon/template/)

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', 'restored');
const OUT = path.resolve(HERE, '..', 'out', 'trailhead-mlvol-template.html');
const CAPS = path.resolve(HERE, 'captures');

const { payload } = await import('./payload.mjs');

const fileCache = new Map();
function readLines(rel) {
  if (!fileCache.has(rel)) {
    const p = path.join(REPO, rel);
    if (!fs.existsSync(p)) return null;
    fileCache.set(rel, fs.readFileSync(p, 'utf8').split(/\r?\n/));
  }
  return fileCache.get(rel);
}

const BAD_CHARS = /[—–]/;
const files = {};           // bundled excerpt lines
const dropped = [];         // the ledger
let claimSeq = 0, verified = 0, inferred = 0;

function bundle(rel, start, end) {
  const lines = readLines(rel);
  files[rel] = files[rel] || {};
  for (let n = start; n <= end; n++) files[rel][String(n)] = lines[n - 1] ?? '';
}

function sha(rel, start, end) {
  const lines = readLines(rel);
  const text = lines.slice(start - 1, end).join('\n');
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

// Resolve a verbatim quote to 1-based line numbers. Fails loudly on
// no-match and on ambiguity: an ambiguous anchor is not an anchor.
// Quotes may join NON-ADJACENT lines (dossier style): each quoted line is
// matched in order, nearest-first, and the whole set must fit in MAXSPAN.
const MAXSPAN = 60;
const eq = (a, b) => a === b || (a !== undefined && a.trimEnd() === b.trimEnd());
function locate(rel, quote, nth) {
  const lines = readLines(rel);
  if (!lines) return { err: 'file missing from snapshot' };
  const q = quote.split('\n').filter(l => l.trim() !== '');
  if (!q.length) return { err: 'empty quote' };
  const starts = [];
  for (let i = 0; i < lines.length; i++) if (eq(lines[i], q[0])) starts.push(i);
  if (!starts.length) return { err: 'quote not found verbatim' };
  const completions = [];
  for (const s of starts) {
    const focus = [s + 1];
    let pos = s, ok = true;
    for (let j = 1; j < q.length; j++) {
      let found = -1;
      for (let i = pos + 1; i <= Math.min(lines.length - 1, s + MAXSPAN); i++)
        if (eq(lines[i], q[j])) { found = i; break; }
      if (found < 0) { ok = false; break; }
      focus.push(found + 1); pos = found;
    }
    if (ok) completions.push(focus);
  }
  if (!completions.length) return { err: 'quote lines not found within ' + MAXSPAN + ' lines of each other' };
  if (completions.length > 1 && nth === undefined) {
    // distinct anchor sites are ambiguous; overlapping ones are the same site
    const spans = completions.map(f => [f[0], f[f.length - 1]]);
    const disjoint = spans.every((a, i) => spans.every((b, j) => i === j || a[1] < b[0] || b[1] < a[0]));
    if (disjoint) return { err: 'ambiguous quote, ' + completions.length + ' sites' };
  }
  return { focus: completions[Math.min(nth ?? 0, completions.length - 1)] };
}

// Turn an authored anchor {file, quote, before?, after?, nth?} into the
// contract shape {file, start, end, focus[], sha256}, dodging dash chars
// in the context window (the artifact must contain none).
function resolveAnchor(a, label) {
  const loc = locate(a.file, a.quote, a.nth);
  if (loc.err) return { err: loc.err };
  const lines = readLines(a.file);
  const focus = loc.focus;
  const f0 = focus[0], f1 = focus[focus.length - 1];
  for (const n of focus) {
    if (BAD_CHARS.test(lines[n - 1] ?? ''))
      return { err: 'focus line ' + n + ' contains a dash character barred from the artifact' };
  }
  let start = Math.max(1, f0 - (a.before ?? 5));
  let end = Math.min(lines.length, f1 + (a.after ?? 9));
  // clip the window inward past any dash-bearing context line
  for (let n = f0 - 1; n >= start; n--)
    if (BAD_CHARS.test(lines[n - 1] ?? '')) { start = n + 1; break; }
  for (let n = f1 + 1; n <= end; n++)
    if (BAD_CHARS.test(lines[n - 1] ?? '')) { end = n - 1; break; }
  // an interior line (between focus lines) carrying a dash cannot be clipped
  for (let n = start; n <= end; n++)
    if (BAD_CHARS.test(lines[n - 1] ?? ''))
      return { err: 'excerpt window line ' + n + ' contains a barred dash character' };
  bundle(a.file, start, end);
  return { file: a.file, start, end, focus, sha256: sha(a.file, start, end) };
}

function resolveClaim(c) {
  claimSeq++;
  const id = 'c-' + String(claimSeq).padStart(3, '0');
  if (!c.anchor) { inferred++; return { id, text: c.text, status: 'inferred' }; }
  const r = resolveAnchor(c.anchor, id);
  if (r.err) {
    dropped.push({ id, text: c.text, file: c.anchor.file, reason: r.err });
    return null;
  }
  verified++;
  return { id, text: c.text, status: 'verified', anchor: r };
}

let commands = 0, failed = 0;
function resolveCommand(b) {
  commands++;
  if (b.exit !== 0) failed++;
  let out = fs.readFileSync(path.join(CAPS, b.capture), 'utf8').replace(/\r\n/g, '\n').replace(/\n+$/, '');
  if (b.elide && out.split('\n').length > b.elide.head + b.elide.tail + 4) {
    const L = out.split('\n');
    const cut = L.length - b.elide.head - b.elide.tail;
    out = [...L.slice(0, b.elide.head), '   [... ' + cut + ' lines elided by the bundler, full run captured ...]', ...L.slice(-b.elide.tail)].join('\n');
  }
  out = out.replace(/[—–]/g, '-');   // captured text may not carry barred chars into the artifact
  const { capture, elide, ...rest } = b;
  return { ...rest, out: out || '(no output)' };
}

// Order checkpoints are AUTHORED with their options in the true sequence and
// the identity key, the same contract as the generator's _order_block. The
// shuffle happens here: Fisher-Yates over the (option, rank) pairs, seeded
// from repo.commit and the checkpoint id, so a rebuild asks the same question
// the same way. An identity draw re-rolls on the next seed: a rank question
// whose on-screen order is already correct grades itself.
function shuffleOrder(b) {
  const n = b.options.length;
  if (n > 9) throw new Error(b.id + ': order checkpoint exceeds the 9-option seed budget');
  for (let round = 0; ; round++) {
    const perm = permutation(payload.repo.commit + '\x00' + b.id + '\x00' + round, n);
    if (n > 1 && perm.every((v, i) => v === i)) continue;
    return { ...b, options: perm.map(j => b.options[j]), answer: perm.map(j => b.answer[j]) };
  }
}

function permutation(seed, n) {
  const bytes = crypto.createHash('sha256').update(seed, 'utf8').digest();
  const perm = [...Array(n).keys()];
  for (let i = n - 1; i > 0; i--) {
    const j = bytes.readUInt32BE((n - 1 - i) * 4) % (i + 1);
    [perm[i], perm[j]] = [perm[j], perm[i]];
  }
  return perm;
}

function walkBlocks(blocks) {
  return blocks.map(b => {
    if (b.type === 'prose') {
      const claims = b.claims.map(resolveClaim).filter(Boolean);
      return { ...b, claims };
    }
    if (b.type === 'checkpoint' && b.kind === 'order') return shuffleOrder(b);
    if (b.type === 'excerpt') {
      const r = resolveAnchor(b.anchor, 'excerpt');
      if (r.err) throw new Error('excerpt anchor failed (' + b.anchor.file + '): ' + r.err);
      return { ...b, anchor: r };
    }
    if (b.type === 'command') return resolveCommand(b);
    if (b.type === 'trace') {
      const steps = b.steps.map(s => {
        const r = resolveAnchor(s.anchor, 'trace');
        if (r.err) throw new Error('trace anchor failed (' + s.anchor.file + '): ' + r.err);
        return { ...s, anchor: r };
      });
      return { ...b, steps };
    }
    return b;
  });
}

// ---------- assemble ----------
const T0 = Date.now();
const P = structuredClone(payload);
P.repo.generated_at = new Date().toISOString().replace(/\.\d+Z$/, 'Z');

for (const track of P.tracks)
  for (const stop of track.stops)
    stop.blocks = walkBlocks(stop.blocks);

// glossary anchors
for (const g of P.glossary || []) {
  if (g.anchorSrc) {
    const r = resolveAnchor(g.anchorSrc, 'glossary:' + g.id);
    if (r.err) { console.warn('glossary anchor dropped (' + g.id + '): ' + r.err); }
    else g.anchor = r;
    delete g.anchorSrc;
  }
}

// map: columns -> coordinates; node anchors resolved
{
  const m = P.map;
  const W = m.w = 1000, colW = 150, gap = 26, topPad = 40;
  const nCols = m.columnLabels.length;
  const span = (W - 40) / nCols;
  m.columns = m.columnLabels.map((label, i) => ({ label, x: Math.round(20 + span * i + span / 2), line: i > 0 }));
  const byCol = {};
  for (const n of m.nodes) (byCol[n.col] = byCol[n.col] || []).push(n);
  let maxY = 0;
  for (const [ci, list] of Object.entries(byCol)) {
    let y = topPad;
    for (const n of list) {
      n.w = colW;
      n.h = Math.round(42 + Math.min(28, Math.sqrt(n.loc) / 6));
      n.x = Math.round(20 + span * (+ci) + (span - colW) / 2);
      n.y = y;
      y += n.h + gap;
      maxY = Math.max(maxY, y);
    }
  }
  m.h = maxY + 8;
  delete m.columnLabels;
  for (const n of m.nodes) {
    if (n.anchorSrc) {
      const r = resolveAnchor(n.anchorSrc, 'node:' + n.id);
      if (r.err) console.warn('node anchor dropped (' + n.id + '): ' + r.err);
      else n.anchor = r;
      delete n.anchorSrc;
    }
    delete n.col;
  }
}

P.files = files;
P.dropped = dropped;
P.report = {
  claims: claimSeq,
  verified,
  dropped: dropped.length,
  inferred,
  commands,
  failed,
  tool_version: P.report.tool_version,
  duration_s: Math.max(1, Math.round((Date.now() - T0) / 1000)),
  regen: P.report.regen,
};

// ---------- splice ----------
const tpl = fs.readFileSync(path.join(HERE, 'walkthrough.template.html'), 'utf8');
const json = JSON.stringify(P).replace(/</g, '\\u003c');
const html = tpl.replace('__PAYLOAD_JSON__', json);

// ---------- gates ----------
const errs = [];
if (html.includes('__PAYLOAD_JSON__')) errs.push('payload token not replaced');
const dash = html.match(/[—–]/g);
if (dash) errs.push('artifact contains ' + dash.length + ' em/en dash characters');
// live external references only: a URL rendered as text inside a source
// excerpt issues no request and is the repo's own content
{
  const live = html.match(/(?:src|href)\s*=\s*["']https?:|url\(\s*["']?https?:|fetch\(|XMLHttpRequest|navigator\.sendBeacon|@import/);
  if (live) errs.push('artifact contains a live external reference: ' + live[0]);
}
if (/@font-face|@import/.test(html)) errs.push('artifact contains a barred CSS at-rule');
if (/<a\s/i.test(html)) errs.push('artifact contains an <a> element (this build ships none)');
const mb = Buffer.byteLength(html) / 1024 / 1024;
if (mb > 5) errs.push('artifact exceeds the 5 MB cap: ' + mb.toFixed(2) + ' MB');

if (errs.length) {
  console.error('BUILD FAILED');
  for (const e of errs) console.error('  - ' + e);
  process.exit(1);
}

fs.writeFileSync(OUT, html);
console.log('built ' + OUT);
console.log('  size      ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB');
console.log('  claims    ' + claimSeq + ' (' + verified + ' verified, ' + inferred + ' inferred, ' + dropped.length + ' dropped)');
console.log('  commands  ' + commands + ' (' + failed + ' failing)');
console.log('  files     ' + Object.keys(files).length + ' bundled');
if (dropped.length) {
  console.log('  DROPPED CLAIMS:');
  for (const d of dropped) console.log('    [' + d.id + '] ' + d.file + ' : ' + d.reason + '  <- ' + d.text.slice(0, 70));
}
