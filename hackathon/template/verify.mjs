// verify.mjs : independent re-check of the built artifact, stage-4 style.
// Reads the HTML, extracts the payload, then for every anchor: re-reads the
// file from the snapshot, recomputes the sha256 over the recorded range, and
// compares. Also asserts the report numbers equal what the payload holds,
// and re-scans the whole file for barred characters and external URLs.
//
// Usage: node verify.mjs      (from hackathon/template/)

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', 'restored');
const OUT = path.resolve(HERE, '..', 'out', 'trailhead-mlvol-template.html');

const html = fs.readFileSync(OUT, 'utf8');
const m = html.match(/const DATA = (\{.*?\});\n/s);
if (!m) { console.error('FAIL: payload not found'); process.exit(1); }
const D = JSON.parse(m[1]);

let checked = 0; const errs = [];
const cache = new Map();
const lines = rel => {
  if (!cache.has(rel)) {
    const p = path.join(REPO, rel);
    cache.set(rel, fs.existsSync(p) ? fs.readFileSync(p, 'utf8').split(/\r?\n/) : null);
  }
  return cache.get(rel);
};

function checkAnchor(a, where) {
  checked++;
  const L = lines(a.file);
  if (!L) return errs.push(where + ': file missing ' + a.file);
  const text = L.slice(a.start - 1, a.end).join('\n');
  const h = crypto.createHash('sha256').update(text, 'utf8').digest('hex');
  if (h !== a.sha256) return errs.push(where + ': sha256 mismatch on ' + a.file + ':' + a.start + '-' + a.end);
  for (const f of a.focus || [])
    if (f < a.start || f > a.end) return errs.push(where + ': focus ' + f + ' outside window');
  // bundled lines must equal the disk lines
  const bundled = D.files[a.file] || {};
  for (let n = a.start; n <= a.end; n++)
    if ((bundled[String(n)] ?? null) !== (L[n - 1] ?? null))
      return errs.push(where + ': bundled line ' + n + ' of ' + a.file + ' differs from disk');
}

let claims = 0, verified = 0, inferred = 0;
for (const t of D.tracks) for (const s of t.stops) for (const b of s.blocks) {
  if (b.type === 'prose') for (const c of b.claims) {
    claims++;
    if (c.status === 'verified') { verified++; checkAnchor(c.anchor, c.id); }
    else inferred++;
    if (/[—–]/.test(c.text)) errs.push(c.id + ': claim text carries a barred dash');
  }
  if (b.type === 'excerpt') checkAnchor(b.anchor, s.id + ':excerpt');
  if (b.type === 'trace') for (const st of b.steps) checkAnchor(st.anchor, s.id + ':trace');
  if (b.type === 'command') {
    if (typeof b.exit !== 'number' || !b.out || /placeholder/i.test(b.out))
      errs.push(s.id + ': command lacks a real exit/output: ' + b.cmd);
  }
  if (b.type === 'checkpoint' && !b.provenance) errs.push(b.id + ': checkpoint without provenance');
}
for (const g of D.glossary || []) if (g.anchor) checkAnchor(g.anchor, 'glossary:' + g.id);
for (const n of D.map.nodes) if (n.anchor) checkAnchor(n.anchor, 'node:' + n.id);

// report integrity: the badge numbers must equal the payload's actual content
const r = D.report;
const total = claims + (D.dropped || []).length;
if (r.claims !== total) errs.push('report.claims=' + r.claims + ' but payload holds ' + total);
if (r.verified !== verified) errs.push('report.verified=' + r.verified + ' but payload holds ' + verified);
if (r.inferred !== inferred) errs.push('report.inferred=' + r.inferred + ' but payload holds ' + inferred);
if (r.dropped !== (D.dropped || []).length) errs.push('report.dropped drifts from ledger');
const cmds = D.tracks.flatMap(t => t.stops).flatMap(s => s.blocks).filter(b => b.type === 'command');
if (r.commands !== cmds.length) errs.push('report.commands=' + r.commands + ' but payload holds ' + cmds.length);
if (r.failed !== cmds.filter(c => c.exit !== 0).length) errs.push('report.failed drifts from captures');

// whole-file scans
const dash = html.match(/[—–]/g);
if (dash) errs.push('artifact contains ' + dash.length + ' barred dash characters');
if (/(?:src|href)\s*=\s*["']https?:|url\(\s*["']?https?:/.test(html)) errs.push('artifact contains a live external URL');
if (/@font-face|@import\b/.test(html)) errs.push('artifact contains a barred CSS at-rule');
if (/<a\s/i.test(html)) errs.push('artifact contains an <a> element');
if (/<link|<script\s+src|fetch\(|XMLHttpRequest|navigator\.sendBeacon/.test(html)) errs.push('artifact references an external resource mechanism');

if (errs.length) {
  console.error('VERIFY FAILED (' + errs.length + ' problems, ' + checked + ' anchors checked)');
  for (const e of errs) console.error('  - ' + e);
  process.exit(1);
}
console.log('VERIFY PASSED');
console.log('  anchors re-hashed against the snapshot: ' + checked);
console.log('  claims ' + total + ' = ' + verified + ' verified + ' + inferred + ' inferred + ' + (D.dropped || []).length + ' dropped (badge matches)');
console.log('  commands ' + cmds.length + ' (' + cmds.filter(c => c.exit !== 0).length + ' failing, all outputs captured)');
console.log('  no barred dashes, no external URLs, no anchor elements, size ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB');
