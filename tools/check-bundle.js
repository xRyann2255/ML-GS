/* check-bundle.js — structural checks on a generated Trailhead HTML file.
 *
 *   node tools/check-bundle.js [path]      default: demo/trailhead-demo.html
 *
 * Enforces the "hard constraints" table in docs/walkthrough-spec.md §1.
 * These are acceptance tests 1 and 12; the rest live in verify-contract.js.
 * Exits non-zero on any failure so it can gate a build.
 */
const fs = require('fs');
const path = require('path');

const file = process.argv[2] || path.join(__dirname, '..', 'demo', 'trailhead-demo.html');
if (!fs.existsSync(file)) { console.error('not found:', file); process.exit(2); }
const src = fs.readFileSync(file, 'utf8');
const kb = Buffer.byteLength(src) / 1024;

let fail = 0;
const check = (ok, label, detail = '') => {
  console.log(`  ${ok ? 'pass' : 'FAIL'}  ${label}${detail ? '  — ' + detail : ''}`);
  if (!ok) fail++;
};

console.log(`\n${path.relative(process.cwd(), file)}  ${kb.toFixed(1)} KB\n`);

// --- 1. no external requests -------------------------------------------------
// Namespace URIs inside inline SVG (xmlns=) are declarations, not fetches, and
// are deliberately excluded. Anything in src/href/fetch/import is a real load.
//
// `href` is the one attribute that is not inherently a load. On <link> it is —
// and <link> is banned outright below. On <a> it is a click-time navigation that
// costs nothing at page load, so prerequisite install links leave the offline
// guarantee (spec §1) intact: the page still opens and renders complete with the
// network off. Anchors are therefore excised before this grep and held to a
// stricter rule of their own in 1b.
const ANCHOR = /<a\b[^>]*>/gi;
const loaders = src.replace(ANCHOR, '')
  .match(/(?:\bsrc|\bhref|\bfetch|\bimport)\s*[=(]\s*["']?\s*(?:https?:)?\/\//g) || [];
check(loaders.length === 0, 'zero external loads (src/href/fetch/import, <a> excluded)',
  loaders.join(' ') || 'none');

// --- 1b. anchors: navigation is allowed, unsafe navigation is not ------------
// Every <a> the renderer can emit must be reachable-but-inert: a real scheme, and
// noopener/noreferrer so a target=_blank tab cannot reach back through
// window.opener. Checked against the literal tags in source, which is where the
// renderer's templates live — so this proves the renderer *always* emits them.
// Comments are stripped first: prose that merely *mentions* <a href> is not an
// anchor, and a gate that fails on how a comment is worded is a gate people
// route around. Block and HTML comments only — stripping // to end-of-line
// would eat the "//" in every https:// URL in the payload.
const anchors = (src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '').match(ANCHOR)) || [];
const hrefOf = a => (a.match(/href\s*=\s*"([^"]*)"/i) || [])[1];
const badScheme = anchors.filter(a => {
  const h = hrefOf(a);
  // a templated href (href="${...}") is validated in the renderer and by
  // verify-contract.js against the payload; only literals are judged here
  return h !== undefined && !h.startsWith('${') && !/^(https?:\/\/|#|mailto:)/i.test(h);
});
check(badScheme.length === 0, 'anchor hrefs are http(s), # or mailto only', badScheme.join(' ') || 'none');
const noRel = anchors.filter(a =>
  !/rel\s*=\s*["'][^"']*\bnoopener\b/i.test(a) || !/rel\s*=\s*["'][^"']*\bnoreferrer\b/i.test(a));
check(noRel.length === 0, 'every <a> carries rel="noopener noreferrer"', noRel.join(' ') || 'none');
if (anchors.length) console.log(`  note  ${anchors.length} anchor template(s) — navigation only, nothing fetched at load`);

const linkTags = src.match(/<link\b[^>]*>/gi) || [];
check(linkTags.length === 0, 'no <link> tags', linkTags.join(' ') || 'none');

const extScripts = src.match(/<script\b[^>]*\bsrc=/gi) || [];
check(extScripts.length === 0, 'no external <script src>', extScripts.join(' ') || 'none');

const webfonts = src.match(/@import|@font-face/g) || [];
check(webfonts.length === 0, 'no @font-face or CSS @import', webfonts.join(' ') || 'none');

// --- 2. single self-contained file -------------------------------------------
check((src.match(/<style>/g) || []).length >= 1, 'inline <style> present');
check((src.match(/<script>/g) || []).length >= 1, 'inline <script> present');
check(/<!DOCTYPE html>/i.test(src), 'has doctype');
check(/<title>[^<]+<\/title>/.test(src), 'has non-empty <title>');
check(/<html[^>]+lang=/.test(src), 'html has lang attribute');
check(/name=["']viewport["']/.test(src), 'has viewport meta');

// --- 3. size budget (spec §1: target < 2 MB, hard cap 5 MB) ------------------
check(kb < 5120, 'under 5 MB hard cap', kb.toFixed(1) + ' KB');
if (kb >= 2048) console.log('  note  over the 2 MB target — consider capping embedded excerpt bytes');

// --- 4. spec-required affordances -------------------------------------------
check(/prefers-color-scheme/.test(src), 'light/dark via prefers-color-scheme');
check(/data-theme/.test(src), 'explicit theme override hook');
check(/prefers-reduced-motion/.test(src), 'honours prefers-reduced-motion');
check(/@media print/.test(src), 'has print stylesheet');
check(/overflow-x\s*:\s*auto|overflow\s*:\s*auto/.test(src), 'contained horizontal scroll');
check(/focus-visible/.test(src), 'visible focus styling');
check(/data-proj/.test(src), 'projector mode');
check(/localStorage/.test(src), 'progress persistence');
// @3 template affordances: the engineering-grid background and the mobile
// rail toggle. Template-level (payload-independent), so their absence means
// the wrong renderer shipped, not a degraded repo. Scoped to the parity
// template by its banner; the frozen demo bundle keeps the old renderer.
if (src.includes('RENDER: knows only')) {
  check(/body::before[\s\S]{0,400}linear-gradient/.test(src), 'engineering grid background');
  check(/railbtn/.test(src), 'mobile rail toggle');
}

// --- 5. inline JS parses -----------------------------------------------------
const scripts = [...src.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let parsed = true, err = '';
for (const js of scripts) {
  try { new (require('vm').Script)(js); } catch (e) { parsed = false; err = e.message; }
}
check(parsed, 'inline JS parses', err);

// --- 6. CSS brace balance (cheap smoke test) --------------------------------
const css = [...src.matchAll(/<style>([\s\S]*?)<\/style>/g)].map(m => m[1]).join('\n');
const open = (css.match(/{/g) || []).length, close = (css.match(/}/g) || []).length;
check(open === close, 'CSS braces balanced', `${open} open / ${close} close`);

console.log(fail ? `\n${fail} FAILURE(S)\n` : '\nBUNDLE OK\n');
process.exit(fail ? 1 : 0);
