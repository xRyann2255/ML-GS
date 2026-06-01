export const meta = {
  name: 'verify-all-diagrams',
  description: 'Audit and fix every TikZ diagram across all guides: crop + deterministic checks + a visual pass + fix-loop, one agent per guide (compile-isolated), with a contact-sheet report. Leaves edits staged; never auto-commits.',
  whenToUse: 'When you want to sweep all guide diagrams for legibility/clarity defects and fix the failures. Pass args="guides/vol-project-ref" to limit to one guide, or omit for all.',
  phases: [
    { title: 'Discover', detail: 'enumerate every tikzpicture figure across the guides' },
    { title: 'Verify', detail: 'one agent per guide runs the engine on its figures sequentially' },
    { title: 'Consolidate', detail: 'recompile guides, build the contact sheet, write the summary' },
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
// <<< VERIFY-ALL-DIAGRAMS HELPERS <<<

const GUIDES = args && String(args).trim()
  ? [String(args).trim()]
  : ['guides/vol-project-ref', 'guides/quant-trading', 'vol-learning-guide']

// ---- Phase 1: Discover (an agent reads the .tex; JS post-processes deterministically) ----
phase('Discover')
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

const discovery = await agent(
  `Enumerate every TikZ figure in these guides: ${JSON.stringify(GUIDES)}.
For each guide root, Glob its chapter .tex files (<guide>/chapters/*.tex and <guide>/*.tex), Read each,
and find every \\begin{tikzpicture}. For each occurrence, emit one flat array element:
- guide: the guide root (exactly one of the inputs)
- file: the repo-relative .tex path
- label: the \\label that belongs to THIS picture (the one that follows it, before the enclosing
  \\end{figure} or the next \\begin{tikzpicture}); null if none
- caption: the first ~80 chars of THIS picture's \\caption (same association rule); null if none
- lineStart: the 1-based line number of its \\begin{tikzpicture}
- id: the label, or "<file>:<lineStart>" if unlabeled
Do NOT attach a neighbouring figure's label/caption to a bare picture. Return a FLAT 'figures' array.`,
  { label: 'discover:figures', phase: 'Discover', agentType: 'Explore', schema: DISCOVER_SCHEMA }
)

const figures = (discovery.figures || []).map(f => ({ ...f, locate: locateSubstr(f) }))
const guideGroups = groupByGuide(figures)
const totalFigs = figures.length
log(`Discovered ${totalFigs} figures across ${guideGroups.length} guides`)

// ---- Phase 2: Verify — ONE agent per guide (compile-isolated: no two agents share a main.tex) ----
phase('Verify')
const GUIDE_RESULT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    guide: { type: 'string' },
    results: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        id: { type: 'string' }, file: { type: 'string' },
        status: { type: 'string', enum: ['already_clean', 'fixed', 'needs_human'] },
        blockingBefore: { type: 'number' }, blockingAfter: { type: 'number' },
        finalCrop: { type: 'string' }, notes: { type: 'string' },
      },
      required: ['id', 'status'],
    } },
  },
  required: ['guide', 'results'],
}

const perGuide = (await parallel(guideGroups.map(group => () =>
  agent(
    `You are auditing and fixing every TikZ diagram in ONE guide: ${group.guide}.
Work through these figures ONE AT A TIME (they share this guide's main.pdf, so never parallelise them):
${JSON.stringify(group.figures.map(f => ({ id: f.id, file: f.file, locate: f.locate, caption: f.caption })), null, 1)}

Apply the verify-diagram engine to each figure, with this batch adaptation: a workflow agent CANNOT
spawn sub-agents, so YOU are both the inspector and the reviewer (you lose the blind-reviewer split;
the deterministic checks are the hard floor and you add the visual judgement yourself).
1. Compile the guide once: cd ${group.guide} && pdflatex -interaction=nonstopmode -halt-on-error main.tex
   (run bibtex + pdflatex x2 if refs are unresolved). Fix any compile error before proceeding.
2. For the figure run:
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/diag_inspect.py --pdf ${group.guide}/main.pdf --locate "<the figure's locate>" --out ${group.guide}/.diagverify
   Read ${group.guide}/.diagverify/inspection.json and VIEW ${group.guide}/.diagverify/crop.png (Read tool).
3. Blocking defects = the JSON's blocking deterministic defects PLUS anything you can SEE in the crop as
   a first-time learner: overlapping/cramped/illegible text, ambiguous arrows, "does the concept read?".
4. If there are blocking defects, edit ONLY this figure's TikZ in its .tex file, recompile (step 1),
   re-inspect (step 2). Cap at 5 iterations.
5. Record per figure: status = already_clean | fixed | needs_human; file; blockingBefore/blockingAfter
   (count of blocking-severity defects in inspection.json, before any fix vs after); finalCrop = the last crop.png path.
Do NOT git commit — leave edits in the working tree. Other guides are handled by parallel agents; touch
ONLY files under ${group.guide}. Return the schema (one result per figure).`,
    { label: `verify:${group.guide.split('/').pop()}`.slice(0, 40), phase: 'Verify',
      schema: GUIDE_RESULT_SCHEMA }
  )
))).filter(Boolean)

const flat = perGuide.flatMap(g => g.results.map(r => ({ guide: g.guide, ...r })))
const needHuman = flat.filter(r => r.status === 'needs_human')
const fixed = flat.filter(r => r.status === 'fixed')
log(`Verified ${flat.length} figures: ${fixed.length} fixed, ${needHuman.length} need human, ` +
    `${flat.length - fixed.length - needHuman.length} already clean`)

// ---- Phase 3: Consolidate ----
phase('Consolidate')
const SUMMARY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { reportPath: { type: 'string' }, contactSheet: { type: 'string' },
                guidesRecompiled: { type: 'array', items: { type: 'string' } },
                written: { type: 'boolean' } },
  required: ['reportPath', 'written'],
}

const consolidation = await agent(
  `Consolidate the batch diagram audit. All edits are already in the working tree (each guide was fixed
in place by its own agent — there are no worktrees to merge).
INPUTS (one row per figure): ${JSON.stringify(flat, null, 1)}
Guides touched: ${JSON.stringify(GUIDES)}

Do:
1. Recompile each touched guide whole (cd <guide> && pdflatex -interaction=nonstopmode -halt-on-error
   main.tex) to confirm nothing broke. Note any guide that now fails to compile.
2. Build a contact sheet of the final crops (skip any path that doesn't exist):
   PYTHONIOENCODING=utf-8 py .claude/skills/verify-diagram/contact_sheet.py --crops <finalCrop...> --out notes/diagram-audit/contact-sheet.png
3. Write a markdown report to notes/diagram-audit/2026-06-01-audit.md: a table of guide | figure |
   status | blockingBefore->blockingAfter, then a "Needs human" section listing the unresolved ones
   with their final crop paths, then a link to the contact sheet.
4. Do NOT git commit anything. Return the schema.`,
  { label: 'consolidate', phase: 'Consolidate', schema: SUMMARY_SCHEMA }
)

return {
  guides: GUIDES,
  totalFigures: totalFigs,
  fixed: fixed.length,
  needHuman: needHuman.map(r => `${r.guide}#${r.id}`),
  report: consolidation.reportPath,
  contactSheet: consolidation.contactSheet,
}
