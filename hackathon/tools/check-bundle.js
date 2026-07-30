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
const loaders = src.match(/(?:\bsrc|\bhref|\bfetch|\bimport)\s*[=(]\s*["']?\s*(?:https?:)?\/\//g) || [];
check(loaders.length === 0, 'zero external loads (src/href/fetch/import)', loaders.join(' ') || 'none');

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
