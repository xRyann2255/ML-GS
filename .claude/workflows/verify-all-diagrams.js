export const meta = {
  name: 'verify-all-diagrams',
  description: 'Per-diagram PARALLEL TikZ audit: compile each guide once, fan out one READ-ONLY inspector agent per figure against the shared PDF, fix ONLY the failures in isolated git worktrees (one agent each), then apply the authoritative edits (per-guide), confirm each fix in parallel, and write a contact-sheet report. Every agent runs on Opus 4.8. Optionally pass {guide, root} to run entirely inside a separate worktree so it never touches the main working tree. Leaves edits in the working tree; never commits.',
  whenToUse: 'When you want to sweep all guide diagrams for legibility/clarity defects and fix the failures, with one agent per diagram. Pass args="guides/vol-project-ref" (or another guide root) to limit to one guide, or args={guide, root:"<abs worktree path>"} to isolate from the main tree, or omit for all.',
  phases: [
    { title: 'Prepare', detail: 'discover every figure + compile each guide once (in parallel)', model: 'opus' },
    { title: 'Inspect', detail: 'one read-only agent per figure: crop + deterministic checks + visual judgement vs the shared PDF', model: 'opus' },
    { title: 'Fix', detail: 'one worktree-isolated agent per FAILING figure, iterating to clean', model: 'opus' },
    { title: 'Apply', detail: 'per-guide agent applies the authoritative edits + one full recompile', model: 'opus' },
    { title: 'Confirm', detail: 'one read-only agent per fixed figure re-checks the fix held', model: 'opus' },
    { title: 'Report', detail: 'build the contact sheet + write the audit markdown', model: 'opus' },
  ],
}

// >>> VERIFY-ALL-DIAGRAMS HELPERS (mirror of __tests__/verify-all-diagrams-helpers.test.mjs) >>>
// EDIT IN THE TEST FILE ONLY; paste verbatim here.
function groupByGuide(figures) {
  // [{guide, figures:[...]}] in first-seen guide order; figures keep their original order.
  const m = new Map()
  for (const f of figures) {
    if (!m.has(f.guide)) m.set(f.guide, [])
    m.get(f.guide).push(f)
  }
  return Array.from(m.entries()).map(([guide, figs]) => ({ guide, figures: figs }))
}

function locateSubstr(fig) {
  // the --locate substring diag_inspect uses to find a figure's page:
  // a distinctive caption fragment, else the label, else the synthetic id
  if (fig.caption && fig.caption.trim()) {
    return fig.caption.trim().split(/\s+/).filter(Boolean).slice(0, 6).join(' ')
  }
  return fig.label || fig.id
}

function slugify(s, i) {
  // filesystem-safe, index-prefixed crop-dir name for a figure (unique even when ids collide)
  const base = String(s || '').replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 44)
  return `f${String(i).padStart(3, '0')}_${base || 'fig'}`
}
// <<< VERIFY-ALL-DIAGRAMS HELPERS <<<

// Every agent() call below pins model:'opus' — in this project the opus tier resolves to Opus 4.8
// (matching the repo's "pin Opus 4.8 on all subagents" convention).
const OPUS = 'opus'
const q = (s) => String(s == null ? '' : s).replace(/"/g, "'")

// args may be a string (the guide) OR an object { guide, root }. `root` (optional) is an absolute base
// dir: point it at a dedicated git worktree to isolate EVERY compile / edit / PDF-read from the main
// working tree (e.g. when another agent is editing the same guide). SHARED phases route through P();
// the per-figure Fix agents stay RELATIVE (each runs in its OWN throwaway worktree branched from HEAD).
// args can arrive as an object OR (per the Workflow runtime) as a JSON string — accept both, plus a
// plain guide string.
let A = args
if (typeof A === 'string') {
  const s = A.trim()
  if (s.startsWith('{')) { try { A = JSON.parse(s) } catch (e) { A = { guide: s } } }
  else { A = { guide: s } }
}
if (!A || typeof A !== 'object' || Array.isArray(A)) A = { guide: A }
const ROOT = A.root ? String(A.root).replace(/\\/g, '/').replace(/\/+$/, '') : '.'
const P = (rel) => (ROOT === '.' ? rel : `${ROOT}/${rel}`)
const guideArg = A.guide != null ? A.guide : A.guides
const GUIDES = guideArg && String(guideArg).trim()
  ? [String(guideArg).trim()]
  : ['guides/vol-project-ref', 'guides/quant-trading', 'vol-learning-guide']

// ===================== Phase 1: Prepare (discover + compile, in parallel) =====================
phase('Prepare')
if (ROOT !== '.') log(`Isolation ON: all compiles/edits/reads happen under ${ROOT} (a separate git worktree); the main working tree is never touched.`)

const DISCOVER_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    figures: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        guide: { type: 'string' }, file: { type: 'string' },
        label: { type: 'string' }, caption: { type: 'string' },
        lineStart: { type: 'number' }, id: { type: 'string' },
      },
      required: ['guide', 'file', 'id'],
    } },
  },
  required: ['figures'],
}

const COMPILE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { guide: { type: 'string' }, compiled: { type: 'boolean' },
                pages: { type: 'number' }, notes: { type: 'string' }, commit: { type: 'string' } },
  required: ['guide', 'compiled'],
}

const guideRoots = GUIDES.map(g => ({ guide: g, path: P(g) }))

const prep = await parallel([
  () => agent(
    `List every TikZ figure in these guides (each has a repo-relative name and the directory to grep):
${JSON.stringify(guideRoots, null, 1)}
Work efficiently, WITHOUT reading whole chapters (reading every file in full will blow your context; do not).
For each guide, use the Grep tool (ripgrep) with line numbers over that guide's "path" directory, glob "*.tex"
(it recurses into chapters/), to get, in ONE pass, every line matching the begin-tikzpicture command, the
\\caption command, or the \\label command.
From that line-numbered output alone, for each begin-tikzpicture hit emit one flat 'figures' element:
- guide: the guide's repo-relative name (the "guide" field above, e.g. "vol-learning-guide")
- file: the .tex path RELATIVE to the repo root — it MUST begin with the guide name (e.g.
  "vol-learning-guide/chapters/06-har-model.tex"). If you grepped an absolute "path", strip everything up to
  and including the guide name so the result is repo-relative. NEVER return an absolute path.
- label: the FIRST label command AFTER this tikzpicture and BEFORE the next begin-tikzpicture hit; null if none
- caption: the FIRST caption in that same range, truncated to ~80 chars; null if none
- lineStart: the begin-tikzpicture line number
- id: the label, or "<file>:<lineStart>" if unlabeled
Only Read a SHORT slice of a file if a caption spans several lines and you must finish it — never read a whole
chapter. Do NOT attach a neighbouring figure's label/caption to a bare picture.
Return the FLAT 'figures' array by calling StructuredOutput.`,
    { label: 'discover:figures', phase: 'Prepare', model: OPUS, schema: DISCOVER_SCHEMA }
  ),
  ...GUIDES.map(g => () => agent(
    `Compile the guide ${g} ONCE so a single, current main.pdf exists for parallel inspection.
Run (resolve refs/TOC). NOTE the absolute base path — operate there, NOT in the main working tree:
cd ${P(g)} && pdflatex -interaction=nonstopmode -halt-on-error main.tex && (bibtex main || true) && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode -halt-on-error main.tex
Resolve any blocking compile error if you can; if you cannot, explain it in notes. Confirm ${P(g)}/main.pdf now exists.
Also run: git -C ${P(g)} rev-parse HEAD  and return its output (trimmed) as 'commit' — the exact source commit being audited.
Return {guide:"${g}", compiled (true iff ${P(g)}/main.pdf was produced), pages, notes, commit}.`,
    { label: `compile:${g.split('/').pop()}`.slice(0, 40), phase: 'Prepare', model: OPUS, schema: COMPILE_SCHEMA }
  )),
])

const discovery = prep[0] || { figures: [] }
const compiles = prep.slice(1).filter(Boolean)
const okGuides = new Set(compiles.filter(c => c.compiled).map(c => c.guide))
const commitC = compiles.find(c => c.commit)
const auditCommit = commitC ? String(commitC.commit).trim() : ''
for (const c of compiles) if (!c.compiled) log(`WARNING: ${c.guide} failed to compile — its figures are skipped. ${c.notes || ''}`)
if (auditCommit) log(`Auditing source commit ${auditCommit.slice(0, 12)}`)

const figures = (discovery.figures || [])
  .filter(f => okGuides.has(f.guide))
  .map((f, i) => ({ ...f, idx: i, locate: locateSubstr(f), slug: slugify(f.id, i),
                    outDir: `${f.guide}/.diagverify/${slugify(f.id, i)}` }))
log(`Discovered ${figures.length} figures across ${okGuides.size} compiled guide(s); one inspector agent per figure (parallel)`)

// ============ Phase 2+3: pipeline — inspect (read-only, parallel) then fix only failures (worktree) ============
const INSPECT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    id: { type: 'string' }, file: { type: 'string' }, label: { type: 'string' },
    locate: { type: 'string' }, located: { type: 'boolean' },
    blockingBefore: { type: 'number' }, visualBlocking: { type: 'boolean' },
    defectSummary: { type: 'string' },
    verdict: { type: 'string', enum: ['clean', 'needs_fix', 'unlocatable'] },
    cropPath: { type: 'string' },
  },
  required: ['id', 'file', 'located', 'verdict', 'blockingBefore', 'cropPath'],
}

const FIX_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    id: { type: 'string' }, file: { type: 'string' }, label: { type: 'string' },
    status: { type: 'string', enum: ['fixed', 'already_clean', 'needs_human'] },
    blockingBefore: { type: 'number' }, blockingAfter: { type: 'number' },
    edits: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: { oldBlock: { type: 'string' }, newBlock: { type: 'string' } },
      required: ['oldBlock', 'newBlock'] } },
    finalCrop: { type: 'string' }, notes: { type: 'string' },
  },
  required: ['id', 'file', 'status', 'blockingBefore', 'blockingAfter', 'edits'],
}

const rows = (await pipeline(
  figures,
  // ---- STAGE 1: inspect (READ-ONLY; all run in parallel vs the one shared, stable main.pdf) ----
  (f) => agent(
    `Inspect ONE TikZ figure in ${f.guide} against the ALREADY-COMPILED PDF at ${P(f.guide)}/main.pdf.
This step is STRICTLY READ-ONLY: do NOT edit any .tex file and do NOT recompile anything — other figures are
being inspected in parallel against this same PDF. Use the EXACT paths below (they may live in a separate worktree).
Figure: id="${q(f.id)}", file="${q(f.file)}", caption="${q(f.caption)}", intended locate="${q(f.locate)}".
Steps:
1. Run (ensure UTF-8 — bash: prefix the env var as shown; PowerShell: run $env:PYTHONIOENCODING='utf-8' first):
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --pdf ${P(f.guide)}/main.pdf --locate "${q(f.locate)}" --out ${P(f.outDir)}
2. Read ${P(f.outDir)}/inspection.json and VIEW ${P(f.outDir)}/crop.png with the Read tool.
3. Confirm the crop really shows THIS figure (content should match the caption). If inspection.json has
   "located": false, or the crop is clearly a different/wrong figure, choose a LONGER, more distinctive
   word-sequence from the caption and re-run step 1 with it as --locate (same --out). If you still cannot
   land on this figure, set verdict="unlocatable".
4. Decide BLOCKING defects = every inspection.json "defects" entry with "severity":"blocking", PLUS anything
   you can SEE that would block a first-time learner: overlapping/cramped/clipped/illegible text, ambiguous
   arrows or arrows to nowhere, colliding nodes, content running off the figure, a layout where the concept
   does not read. Warn-only issues are NOT blocking.
5. Return via StructuredOutput: id, file, label (the figure's label name, or "" if none), locate (the
   substring that worked), located (bool), blockingBefore (integer count of "blocking"-severity entries in
   inspection.json), visualBlocking (true iff YOU see a blocking problem the deterministic checks missed),
   defectSummary (one short line, or "none"), verdict ("clean" | "needs_fix" | "unlocatable"),
   cropPath="${P(f.outDir)}/crop.png".`,
    { label: `inspect:${f.slug}`.slice(0, 40), phase: 'Inspect', model: OPUS, schema: INSPECT_SCHEMA }
  ),
  // ---- STAGE 2: fix ONLY needs_fix figures, each in its OWN git worktree (RELATIVE paths; passthrough otherwise) ----
  async (insp, f) => {
    const baseRow = { id: f.id, file: f.file, guide: f.guide, label: f.label || '', locate: f.locate }
    if (!insp) return { ...baseRow, status: 'needs_human', blockingBefore: 0, blockingAfter: 0, cropPath: null, notes: 'inspector returned nothing' }
    if (insp.verdict === 'clean')
      return { ...baseRow, label: insp.label || f.label || '', locate: insp.locate || f.locate, status: 'already_clean',
               blockingBefore: insp.blockingBefore || 0, blockingAfter: insp.blockingBefore || 0, cropPath: insp.cropPath, notes: insp.defectSummary || 'none' }
    if (insp.verdict === 'unlocatable')
      return { ...baseRow, label: insp.label || f.label || '', locate: insp.locate || f.locate, status: 'needs_human',
               blockingBefore: insp.blockingBefore || 0, blockingAfter: insp.blockingBefore || 0, cropPath: insp.cropPath || null,
               notes: 'unlocatable in compiled PDF — inspect manually' }
    const fx = await agent(
      `You are fixing ONE TikZ figure in the guide ${f.guide}. You run inside an ISOLATED git worktree (your CWD):
edits you make to files here are SCRATCH, used only to compile-and-check your fix. The fix that will actually be
applied to the real repository is the LIST OF EDITS (oldBlock->newBlock pairs) you RETURN — so each oldBlock must
be byte-exact. Use RELATIVE paths (everything is under your worktree CWD).
Figure: id="${q(f.id)}", file="${q(f.file)}", label=${f.label ? '"' + q(f.label) + '"' : '(none)'}, locate="${q(f.locate)}".
Inspector found: ${q(insp.defectSummary) || '(see crop)'} (deterministic blocking=${insp.blockingBefore || 0}, visualBlocking=${insp.visualBlocking ? 'yes' : 'no'}).
Goal: targeted TikZ edits so EVERY blocking defect is gone, proven by recompiling and re-inspecting. Keep the
pedagogical content identical — fix only layout/legibility (spacing, font sizes, node sizes, arrow routing,
text wrapping, alignment).
Steps:
0. FIRST guarantee this worktree holds the SAME source that was audited (your worktree may have branched from an
   older commit that lacks recent files): run  git checkout ${auditCommit || 'HEAD'} -- ${f.file}
   If that command errors, continue with whatever ${f.file} you already have.
1. Open ${f.file}; find this figure's \\begin{tikzpicture} ... \\end{tikzpicture} (and enclosing figure env).
   For EACH region you will change, capture its EXACT current text as an oldBlock — a verbatim, UNIQUE substring
   of the file (include just enough TikZ to be unique). A figure may legitimately need MORE THAN ONE edit.
2. Edit ${f.file} in THIS worktree to apply your improved version(s) (each changed region becomes a newBlock).
3. Recompile to check. FAST PATH if the figure has a \\label inside a figure environment:
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/standalone_wrapper.py --guide ${f.guide} --label ${f.label || 'MISSING'} --out ${f.guide}/.diagstandalone
   then inspect the single-figure PDF (locate is empty — it is the only thing on the page):
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --pdf ${f.guide}/_diagstandalone.pdf --locate "" --out ${f.guide}/.diagverify/fixcheck
   If standalone_wrapper prints "FALLBACK", recompile the whole guide instead:
   cd ${f.guide} && pdflatex -interaction=nonstopmode -halt-on-error main.tex
   and inspect with --pdf ${f.guide}/main.pdf --locate "${q(f.locate)}".
4. Read inspection.json and VIEW the new crop.png. If blocking defects remain, refine and repeat steps 2-4.
   HARD CAP: 5 iterations.
5. Return via StructuredOutput: id, file, label, status ("fixed" if the final crop has ZERO blocking defects;
   "already_clean" if on close inspection it was actually fine and you changed nothing; "needs_human" if 5
   iterations did not clear it), blockingBefore=${insp.blockingBefore || 0}, blockingAfter (final blocking count
   you observed), edits (an ARRAY of {oldBlock, newBlock} — ONE entry per disjoint region you changed; return ALL
   of them, so a figure needing two separate fixes returns BOTH; each oldBlock must match the file byte-for-byte;
   empty array if already_clean or you made no edit), finalCrop (path to your last crop.png), notes (one line:
   what you changed, or why it still needs a human).`,
      { label: `fix:${f.slug}`.slice(0, 40), phase: 'Fix', model: OPUS, isolation: 'worktree', schema: FIX_SCHEMA }
    )
    if (!fx) return { ...baseRow, label: insp.label || f.label || '', locate: insp.locate || f.locate, status: 'needs_human',
                      blockingBefore: insp.blockingBefore || 0, blockingAfter: insp.blockingBefore || 0, cropPath: insp.cropPath || null, notes: 'fixer skipped' }
    return { ...baseRow, label: fx.label || insp.label || f.label || '', locate: insp.locate || f.locate, status: fx.status,
             blockingBefore: fx.blockingBefore, blockingAfter: fx.blockingAfter, edits: fx.edits || [],
             cropPath: insp.cropPath || null, notes: fx.notes || '' }
  }
)).filter(Boolean)

log(`Inspected ${rows.length}: ${rows.filter(r => r.status === 'already_clean').length} already-clean, ` +
    `${rows.filter(r => r.status === 'fixed').length} fixed, ${rows.filter(r => r.status === 'needs_human').length} need human`)

// ===================== Phase 4: Apply (parallel PER GUIDE — the only serial-within-guide step) =====================
phase('Apply')
const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    guide: { type: 'string' }, recompiled: { type: 'boolean' }, applied: { type: 'number' },
    problems: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: { id: { type: 'string' }, note: { type: 'string' } }, required: ['id', 'note'] } },
  },
  required: ['guide', 'recompiled'],
}

const fixedGroups = groupByGuide(rows.filter(r => r.status === 'fixed'))
const applyResults = (await parallel(fixedGroups.map(grp => () => agent(
  `Apply the verified TikZ fixes for guide ${grp.guide} to the working tree at the EXACT paths below (these may be
a separate worktree — do NOT edit anything outside them), then recompile that guide once.
The fixes were produced by per-figure agents in throwaway worktrees, so NOTHING is written to these paths yet.
FIXES (one per figure; "file" is the absolute path to edit; "edits" is the list of replacements to apply in order): ${JSON.stringify(grp.figures.map(r => ({ id: r.id, file: P(r.file), edits: r.edits || [] })), null, 1)}
Do:
1. For EACH fix: open its file and apply EVERY entry in its "edits" list — replace each entry's EXACT oldBlock
   substring with its newBlock (Edit tool, exact match). If an oldBlock is absent but its newBlock is already
   present -> that entry is already applied. If an oldBlock is simply not found -> record a problem
   {id, note:"apply_failed"} (still apply the figure's OTHER entries). Count 'applied' = figures with >=1 entry applied.
2. Recompile ${grp.guide} FULLY (so refs/TOC also resolve):
   cd ${P(grp.guide)} && pdflatex -interaction=nonstopmode -halt-on-error main.tex && (bibtex main || true) && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode -halt-on-error main.tex
   If it FAILS: read the pdflatex error, find the offending applied figure, REVERT that figure's edits (each newBlock->oldBlock),
   record a problem {id, note:"compile_break"}, and recompile again. Repeat until ${P(grp.guide)}/main.pdf compiles cleanly.
3. Return: guide="${grp.guide}", recompiled (true iff ${P(grp.guide)}/main.pdf finally built), applied (count), problems (list).
   Do NOT git commit.`,
  { label: `apply:${grp.guide.split('/').pop()}`.slice(0, 40), phase: 'Apply', model: OPUS, schema: APPLY_SCHEMA }
)))).filter(Boolean)

// fold apply problems back into the rows (downgrade failed/reverted fixes to needs_human)
const problemNote = new Map()
for (const a of applyResults) for (const p of (a.problems || [])) problemNote.set(p.id, p.note)
for (const r of rows) if (r.status === 'fixed' && problemNote.has(r.id)) { r.status = 'needs_human'; r.notes = problemNote.get(r.id) }
const recompileFailed = applyResults.filter(a => !a.recompiled).map(a => a.guide)
if (recompileFailed.length) log(`WARNING: guides that did not cleanly recompile: ${recompileFailed.join(', ')}`)

// ===================== Phase 5: Confirm (one read-only agent per still-fixed figure, in parallel) =====================
phase('Confirm')
const CONFIRM_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { id: { type: 'string' }, blockingAfter: { type: 'number' },
                cropPath: { type: 'string' }, held: { type: 'boolean' } },
  required: ['id', 'blockingAfter', 'held'],
}
const toConfirm = rows.filter(r => r.status === 'fixed')
const confirms = (await parallel(toConfirm.map((r, k) => () => agent(
  `Re-inspect ONE already-fixed TikZ figure in ${r.guide} against the FRESHLY RECOMPILED PDF at ${P(r.guide)}/main.pdf
to confirm the fix held. STRICTLY READ-ONLY (do not edit or recompile). Figure id="${q(r.id)}", file="${q(r.file)}", locate="${q(r.locate)}".
1. PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --pdf ${P(r.guide)}/main.pdf --locate "${q(r.locate)}" --out ${P(r.guide)}/.diagverify/final_${k}
2. Read .../inspection.json and VIEW .../crop.png. If it lands on the wrong figure, refine --locate with a
   longer caption fragment and re-run (same --out).
3. blockingAfter = count of "blocking"-severity defects you can confirm (deterministic + anything you still SEE).
   held = (blockingAfter == 0 AND the figure now reads cleanly to a first-time learner).
Return: id="${q(r.id)}", blockingAfter, cropPath="${P(r.guide)}/.diagverify/final_${k}/crop.png", held.`,
  { label: `confirm:${slugify(r.id, k)}`.slice(0, 40), phase: 'Confirm', model: OPUS, schema: CONFIRM_SCHEMA }
)))).filter(Boolean)

const cmap = new Map(confirms.map(c => [c.id, c]))
for (const r of rows) {
  const c = cmap.get(r.id)
  if (!c) continue
  r.blockingAfter = c.blockingAfter
  if (c.cropPath) r.cropPath = c.cropPath
  if (!c.held) { r.status = 'needs_human'; r.notes = `${r.notes || ''} fix_did_not_hold`.trim() }
}

// ===================== Phase 6: Report (contact sheet + audit markdown) =====================
phase('Report')
const REPORT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { reportPath: { type: 'string' }, contactSheet: { type: 'string' }, written: { type: 'boolean' } },
  required: ['reportPath', 'written'],
}
const reportDir = P('notes/diagram-audit')
const reportRows = rows.map(r => ({ guide: r.guide, file: r.file, id: r.id, status: r.status,
  blockingBefore: r.blockingBefore, blockingAfter: r.blockingAfter, cropPath: r.cropPath || null, notes: r.notes || '' }))

const report = await agent(
  `Write the final audit artifacts for the diagram sweep of ${JSON.stringify(GUIDES)}. All fixes are already applied
and the guide(s) are recompiled; you only ASSEMBLE outputs (no .tex edits, no recompile). Write everything UNDER
the output directory ${reportDir} (it may be a separate worktree).
ROWS (final statuses, one per figure; cropPath is the exact crop image path): ${JSON.stringify(reportRows, null, 1)}
Do:
1. Get today's date as YYYY-MM-DD (bash: date +%F ; PowerShell: Get-Date -Format yyyy-MM-dd). Call it DATE.
2. CONTACT SHEET: gather each row's cropPath that actually EXISTS on disk (skip missing). Then:
   (bash) mkdir -p ${reportDir}
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/contact_sheet.py --crops <existing crop paths...> --out ${reportDir}/<DATE>-contact-sheet.png
3. REPORT: write ${reportDir}/<DATE>-audit.md containing:
   - a one-line summary: "<N> figures: <A> already-clean, <F> fixed, <H> need human" (use the FINAL statuses);
   - a markdown table, columns: guide | file | id | status | blocking (before -> after) | note;
   - a "## Needs human" section: each needs_human row with file, id, note, and its crop path;
   - a "## Fixed" section: each fixed row with a one-line description of the change (from its notes);
   - a final line linking ./<DATE>-contact-sheet.png.
4. Do NOT git commit. Return via StructuredOutput: reportPath="${reportDir}/<DATE>-audit.md" (with DATE
   substituted), contactSheet="${reportDir}/<DATE>-contact-sheet.png", written=true.`,
  { label: 'report', phase: 'Report', model: OPUS, schema: REPORT_SCHEMA }
)

return {
  guides: GUIDES,
  root: ROOT,
  totalFigures: figures.length,
  alreadyClean: rows.filter(r => r.status === 'already_clean').length,
  fixed: rows.filter(r => r.status === 'fixed').length,
  needHuman: rows.filter(r => r.status === 'needs_human').map(r => `${r.file}#${r.id}`),
  recompileFailed,
  report: report.reportPath,
  contactSheet: report.contactSheet,
}
