export const meta = {
  name: 'write-copilot-plans',
  description: 'Fan-out engine for the write-copilot-plans skill: parallel recon of the target repo + research corpus, judged design candidates, per-plan drafting against a shared interface ledger, and multi-pass verification of the finished plan suite',
  whenToUse: 'Invoked BY the write-copilot-plans skill (.claude/skills/write-copilot-plans/SKILL.md) — one mode per call, main session in the loop between modes. Pass args={mode:"recon"|"design"|"draft"|"verify", ...}. Required args per mode are validated on entry and listed in the thrown error.',
  // Model tiering (mirrors deep-research-distill): Fable 5 on quality-bearing calls
  // (research maps, design authors, plan drafters, cross-plan judge); Sonnet 5 at xhigh
  // on grounded extraction and mechanical checks (contract/codebase maps, lints, scans).
  phases: [
    { title: 'Recon', model: 'fable', detail: 'contract map + research maps + codebase maps, in parallel' },
    { title: 'Design', model: 'fable', detail: 'candidate architectures through distinct lenses, scored by a judge panel' },
    { title: 'Draft', model: 'fable', detail: 'one drafter per plan against the overview + interface ledger; per-plan packet lint' },
    { title: 'Verify', model: 'fable', detail: 'cross-plan consistency, placeholder scan, rebuild check' },
  ],
}

// ---- args (robust to JSON-encoded strings) ----
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
if (!A || typeof A !== 'object') A = {}
const MODE = A.mode
const SKILL_DIR = '.claude/skills/write-copilot-plans'

function need(cond, msg) { if (!cond) throw new Error(`write-copilot-plans[${MODE}]: ${msg}`) }

const REPORT = {
  type: 'object',
  properties: { report: { type: 'string', description: 'Exhaustive markdown report' } },
  required: ['report'],
}
const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          plan: { type: 'string' }, location: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          issue: { type: 'string' }, fix: { type: 'string' },
        },
        required: ['plan', 'location', 'severity', 'issue', 'fix'],
      },
    },
  },
  required: ['findings'],
}

// =====================================================================
// MODE: recon — parallel maps of contract, research corpus, codebase
//   args: { mode, repoRoot, feature, researchDocs: [paths], extraFacets?: [{key, prompt}] }
// =====================================================================
if (MODE === 'recon') {
  need(A.repoRoot, 'needs repoRoot (absolute path of the TARGET repo Copilot executes in)')
  need(A.feature, 'needs feature (one sentence: what the suite will build)')
  const researchDocs = Array.isArray(A.researchDocs) ? A.researchDocs : []

  const contractTask = {
    key: 'contract',
    model: 'sonnet', effort: 'xhigh',
    prompt: `Map the CURRENT GitHub Copilot execution contract of the repo at ${A.repoRoot}. Read fully (where present): AGENTS.md, .github/copilot-instructions.md, policy/subagent_protocol.md, policy/context-isolation.md, policy/working-agreements.md, workflows/INDEX.md + plan/execute workflow files, .github/prompts/ (list all; quote the /plan and /execute prompt files), the repo-root CLI wrapper script, and any ML/domain constraints policy. Report EXHAUSTIVELY: (1) the subagent context-packet schema VERBATIM (every field, with the packet-writing rules); (2) the subagent return contract verbatim; (3) every hard rule a subagent inherits (CLI discipline, file-write discipline, terminal isolation, model pinning, depth/concurrency limits, retry policy); (4) the TDD gate's exact wording and exemptions; (5) test-suite conventions (layout, markers, fixture style, inner-loop vs pre-commit commands); (6) commit-message conventions; (7) experiment/config conventions (where configs live, naming, registries, how experiments are validated and interpreted); (8) where plan documents must live for agents to read them. Quote generously — the caller writes packets FROM this report, never from memory.`,
  }
  const codebaseTasks = [
    { key: 'extension-surface', model: 'sonnet', effort: 'xhigh', prompt: `In the repo at ${A.repoRoot}: map every extension seam relevant to building "${A.feature}" — registries and their registration mechanics, base classes/protocols with VERBATIM signatures and capability flags, the end-to-end checklist of what one must touch to add one new component that participates in the repo's main run command. Exact file paths + line references.` },
    { key: 'execution-config', model: 'sonnet', effort: 'xhigh', prompt: `In the repo at ${A.repoRoot}: map how work is configured and executed end-to-end — the run command's full module chain, the config schema (paste the main config dataclasses/structures verbatim), one COMPLETE real config example, output/artifact locations, caching/checkpoint/resume mechanics, and every parallelism mechanism (process pools, GPU assignment, progress/event plumbing) with the invariants they obey. Exact paths + line references.` },
    { key: 'existing-inventory', model: 'sonnet', effort: 'xhigh', prompt: `In the repo at ${A.repoRoot}: build the ALREADY-EXISTS inventory for "${A.feature}". Grep source files (not just directory listings) for the feature's nouns and synonyms; open every hit. Report every existing component the feature area already has — even partial/buried implementations, dead code paths, config stubs, and prior experiment configs — each with: path, verbatim public signature, what works, what is missing, and how a new plan should EXTEND it. Explicitly list what a plan suite must NOT rebuild. This report is the input to a later rebuild-check.` },
    ...(Array.isArray(A.extraFacets) ? A.extraFacets.map(f => ({ key: f.key, model: 'sonnet', effort: 'xhigh', prompt: f.prompt })) : []),
  ]
  const researchTasks = researchDocs.map((doc, i) => ({
    key: `research-${i + 1}`,
    model: 'fable', effort: 'high',
    prompt: `Read the ENTIRE research artifact at ${doc} (in chunks until every line is read). Extract everything a plan suite for "${A.feature}" needs: every method/architecture/component discussed (with the math, verbatim where compact), stated hyperparameters and protocols, quantitative results WITH exact numbers and their evaluation caveats, recommended build order or gates, known pitfalls/leakage rules, and full citations. Do not round numbers or summarize away specifics — the caller writes expected-outcome priors and decision gates from this report.`,
  }))

  phase('Recon')
  const tasks = [contractTask, ...researchTasks, ...codebaseTasks]
  const results = await parallel(tasks.map(t => () =>
    agent(t.prompt, { label: `recon:${t.key}`, phase: 'Recon', schema: REPORT, model: t.model, effort: t.effort })
  ))
  const out = {}
  tasks.forEach((t, i) => { out[t.key] = results[i] ? results[i].report : 'AGENT FAILED — rerun this facet' })
  const failed = tasks.filter((t, i) => !results[i]).map(t => t.key)
  if (failed.includes('contract')) log('WARNING: the contract map failed — do NOT write packets until it is re-run')
  return { mode: 'recon', reports: out, failed }
}

// =====================================================================
// MODE: design — candidate architectures through lenses, judged
//   args: { mode, feature, groundingPaths: [paths to saved recon reports / draft overview],
//           lenses?: [..], nJudges?: 3 }
// =====================================================================
if (MODE === 'design') {
  need(A.feature, 'needs feature')
  need(Array.isArray(A.groundingPaths) && A.groundingPaths.length, 'needs groundingPaths (files holding the recon reports)')
  const lenses = (Array.isArray(A.lenses) && A.lenses.length) ? A.lenses : [
    'minimal-diff: smallest change that ships the feature by maximally reusing existing seams',
    'library-first: lean on established external libraries wherever one fits, own code only for glue',
    'convention-purist: mirror the repo\'s strongest existing pattern even where a shortcut exists',
  ]
  const grounding = A.groundingPaths.map(p => `- ${p}`).join('\n')

  phase('Design')
  const APPROACH = {
    type: 'object',
    properties: {
      name: { type: 'string' }, thesis: { type: 'string' },
      architecture: { type: 'string', description: 'component-by-component design with exact repo seams it plugs into' },
      plan_split: { type: 'string', description: 'proposed decomposition into sequential plans with gates' },
      reuses: { type: 'array', items: { type: 'string' } },
      new_dependencies: { type: 'array', items: { type: 'string' } },
      risks: { type: 'array', items: { type: 'string' } },
    },
    required: ['name', 'thesis', 'architecture', 'plan_split', 'reuses', 'new_dependencies', 'risks'],
  }
  const candidates = (await parallel(lenses.map((lens, i) => () =>
    agent(
      `Design the best implementation approach for "${A.feature}" through this lens: ${lens}.\nGround every choice in the recon reports (read them fully):\n${grounding}\nHonor the target repo's contract and extend (never rebuild) the already-exists inventory. Produce a complete architecture and a proposed split into sequential plans with decision gates.`,
      { label: `design:candidate-${i + 1}`, phase: 'Design', schema: APPROACH, model: 'fable', effort: 'high' }
    )
  ))).filter(Boolean)
  if (!candidates.length) throw new Error('design: all candidate authors failed')

  const JUDGE = {
    type: 'object',
    properties: {
      ranking: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            fit: { type: 'number' }, evidence: { type: 'number' },
            risk: { type: 'number' }, complexity: { type: 'number' },
            total: { type: 'number' }, rationale: { type: 'string' },
          },
          required: ['name', 'fit', 'evidence', 'risk', 'complexity', 'total', 'rationale'],
        },
      },
      recommendation: { type: 'string', description: 'winner + which runner-up ideas to graft onto it' },
    },
    required: ['ranking', 'recommendation'],
  }
  const nJudges = A.nJudges || 3
  const judges = (await parallel(Array.from({ length: nJudges }, (_, j) => () =>
    agent(
      `You are judge ${j + 1} of ${nJudges}. Score each candidate architecture 1-10 on: fit (plugs into the repo's REAL seams per the recon), evidence (supported by the research reports' numbers, not folklore), risk (10 = safest: leakage, drift, irreversibility considered), complexity (10 = simplest that works). total = fit+evidence+risk+complexity. Be adversarial: hunt for the seam a candidate missed or the component it would rebuild.\nGrounding reports:\n${grounding}\n\nCandidates:\n${JSON.stringify(candidates, null, 2)}`,
      { label: `design:judge-${j + 1}`, phase: 'Design', schema: JUDGE, model: 'sonnet', effort: 'xhigh' }
    )
  ))).filter(Boolean)
  return { mode: 'design', candidates, judges }
}

// =====================================================================
// MODE: draft — one drafter per plan against the overview + ledger
//   args: { mode, overviewPath, outDir, suite,
//           planBriefs: [{n, slug, title, brief, groundingPaths?: [..]}] }
// =====================================================================
if (MODE === 'draft') {
  need(A.overviewPath, 'needs overviewPath (the hand-written 00-overview.md)')
  need(A.outDir, 'needs outDir (absolute dir where plan files are written)')
  need(A.suite, 'needs suite (short id used in subtask_ids, e.g. "gnn")')
  need(Array.isArray(A.planBriefs) && A.planBriefs.length, 'needs planBriefs [{n, slug, title, brief}]')

  phase('Draft')
  const DRAFT = {
    type: 'object',
    properties: {
      path: { type: 'string' },
      interfaces_produced: { type: 'array', items: { type: 'string' } },
      ledger_deviations: { type: 'array', items: { type: 'string' }, description: 'signatures that had to differ from the overview ledger — MUST be back-ported by the caller' },
      summary: { type: 'string' },
    },
    required: ['path', 'interfaces_produced', 'ledger_deviations', 'summary'],
  }
  const results = await pipeline(
    A.planBriefs,
    b => {
      const nn = String(b.n).padStart(2, '0')
      const dest = `${A.outDir}/plan-${nn}-${b.slug}.md`
      const extra = Array.isArray(b.groundingPaths) && b.groundingPaths.length
        ? `\nAdditional grounding to read fully: ${b.groundingPaths.join(', ')}` : ''
      return agent(
        `Write Plan ${nn} — "${b.title}" of the "${A.suite}" Copilot plan suite, to ${dest} (Write the file yourself).\n\nRead FIRST, fully: ${A.overviewPath} (the overview — its interface ledger and shared conventions are AUTHORITATIVE: copy signatures, never re-derive), ${SKILL_DIR}/references/plan-template.md (the required structure), ${SKILL_DIR}/references/context-packet.md (packet schema + orchestrator prompt).${extra}\n\nBrief for this plan: ${b.brief}\n\nRequirements: every task carries a complete context packet; TDD steps contain ACTUAL test code and implementation code (or a bounded recipe naming the in-repo exemplar file); configs/experiments are complete YAML with hypothesis + expected-outcome prior + decision rule; the plan ends with the orchestrator prompt (wave ordering from depends_on + disjoint write_scopes) and an acceptance gate. No placeholders (no TBD, no "similar to Task N"). If a signature you need is missing from the ledger, choose one, use it consistently, and report it in ledger_deviations.`,
        { label: `draft:plan-${nn}`, phase: 'Draft', schema: DRAFT, model: 'fable', effort: 'high' }
      )
    },
    (draft, b) => {
      if (!draft) return null
      return agent(
        `Packet-lint the plan file at ${draft.path} against ${SKILL_DIR}/references/context-packet.md and the conventions in ${A.overviewPath}. Check EVERY task: packet present with all fields; goal is one testable sentence; file_scope minimal (plan section + true integration points only); write_scopes disjoint across tasks marked parallel in the orchestrator prompt; every acceptance criterion machine-verifiable; TDD steps show red-then-green with real code; commit message present; no placeholder text anywhere. Report findings only (empty list if clean) — do not edit the file.`,
        { label: `lint:plan-${String(b.n).padStart(2, '0')}`, phase: 'Draft', schema: FINDINGS, model: 'sonnet', effort: 'xhigh' }
      ).then(l => ({ draft, lint: l ? l.findings : [{ plan: draft.path, location: '-', severity: 'major', issue: 'lint agent failed', fix: 'rerun lint' }] }))
    }
  )
  return { mode: 'draft', plans: results.filter(Boolean) }
}

// =====================================================================
// MODE: verify — cross-plan passes over the finished suite
//   args: { mode, planDir, repoRoot, inventoryPath? }
// =====================================================================
if (MODE === 'verify') {
  need(A.planDir, 'needs planDir (dir holding 00-overview.md + plan-NN-*.md)')
  need(A.repoRoot, 'needs repoRoot (target repo, for the rebuild check)')
  const inventory = A.inventoryPath || `${A.planDir}/00-overview.md`

  phase('Verify')
  const checks = [
    {
      key: 'consistency', model: 'fable', effort: 'high',
      prompt: `Cross-plan consistency check. Read ${A.planDir}/00-overview.md (the interface ledger is ground truth) and EVERY plan-NN-*.md in ${A.planDir} in full. Find: signatures/field-lists/defaults used in one plan that contradict the ledger or another plan; registry keys, config fields, column names, event types, or file paths spelled differently across plans; plan/trial/experiment numbering collisions; depends_on or gate references to tasks/plans that do not exist; orchestrator-prompt wave orderings that violate depends_on or overlap write_scopes. Report each as a finding with the exact locations of BOTH sides of the contradiction.`,
    },
    {
      key: 'placeholders', model: 'sonnet', effort: 'xhigh',
      prompt: `Placeholder scan over every .md file in ${A.planDir}. Find: TBD/TODO used as content (an explicit instruction to the executor with a stated fallback is sanctioned — flag only content-free ones); "similar to Task N" without repeated content or an anchor; test steps without test code; implementation steps that describe without code AND without naming an in-repo exemplar file; acceptance criteria requiring human judgment ("works correctly"); empty sections. Report findings only.`,
    },
    {
      key: 'rebuild', model: 'sonnet', effort: 'xhigh',
      prompt: `Rebuild check. Read the already-exists inventory in ${inventory} (and spot-verify against the repo at ${A.repoRoot} by opening the named files). Then read every plan in ${A.planDir}. Flag any task that CREATES a component the inventory (or the repo) already provides — same responsibility under a different name counts. For each: the task, the existing component's path + signature, and the fix (extend/delegate instead).`,
    },
  ]
  const results = await parallel(checks.map(c => () =>
    agent(c.prompt, { label: `verify:${c.key}`, phase: 'Verify', schema: FINDINGS, model: c.model, effort: c.effort })
  ))
  const findings = []
  checks.forEach((c, i) => {
    if (!results[i]) findings.push({ plan: '-', location: '-', severity: 'major', issue: `${c.key} check agent failed`, fix: 'rerun this check' })
    else findings.push(...results[i].findings.map(f => ({ ...f, check: c.key })))
  })
  const order = { blocker: 0, major: 1, minor: 2 }
  findings.sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3))
  log(`verify: ${findings.length} findings (${findings.filter(f => f.severity === 'blocker').length} blockers)`)
  return { mode: 'verify', findings }
}

throw new Error(`write-copilot-plans: unknown mode ${JSON.stringify(MODE)} — pass args={mode:"recon"|"design"|"draft"|"verify", ...}`)
