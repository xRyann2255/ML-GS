#!/usr/bin/env node
/**
 * check-fixtures.js — the pipeline fixtures agree with each other.
 *
 * survey.sample.json + content.sample.json + commands.sample.json are the inputs
 * VERIFY consumes; verified.sample.json is what it should be able to produce.
 * All four describe the same synthetic repo (payments-core @ a3f9c21). If they
 * drift apart, three owners are coding against three different repos and nobody
 * finds out until integration.
 *
 * Contracts: docs/pipeline-contracts.md
 * Run:  node tools/check-fixtures.js
 */
const path = require("path");

const DIR = path.join(__dirname, "..", "fixtures");
const load = (n) => require(path.join(DIR, n));

let failed = 0;
const chk = (ok, msg, detail) => {
  console.log(`  ${ok ? "pass" : "FAIL"}  ${msg}${detail ? "  — " + detail : ""}`);
  if (!ok) failed++;
};

const survey = load("survey.sample.json");
const content = load("content.sample.json");
const commands = load("commands.sample.json");
const verified = load("verified.sample.json");

console.log("\nfixtures/  survey + content + commands  vs  verified\n");

// ---- contract tags -------------------------------------------------------
chk(survey.contract === "trailhead/survey@1", "survey contract tag", survey.contract);
chk(content.contract === "trailhead/content@1", "content contract tag", content.contract);
chk(commands.contract === "trailhead/commands@1", "commands contract tag", commands.contract);

// ---- same repo, same commit ---------------------------------------------
const commit = verified.repo.commit;
chk(
  survey.repo.commit === commit && content.repo.commit === commit,
  "all fixtures describe one commit",
  commit
);
chk(
  survey.repo.name === verified.repo.name && content.repo.name === verified.repo.name,
  "all fixtures describe one repo",
  verified.repo.name
);

// ---- survey internal consistency ----------------------------------------
const modules = Object.keys(survey.modules);
chk(
  survey.edges.every((e) => modules.includes(e.a) && modules.includes(e.b)),
  "every edge names a known module"
);
chk(
  survey.files.every((f) => !f.path.includes("\\")),
  "file paths are repo-relative with forward slashes"
);
for (const [id, cp] of Object.entries(survey.checkpoints)) {
  chk(
    Boolean(cp.provenance && cp.explanation),
    `checkpoint ${id} carries provenance + explanation`
  );
  chk(
    cp.kind === "single"
      ? Number.isInteger(cp.answer) && cp.answer >= 0 && cp.answer < cp.options.length
      : Array.isArray(cp.answer) && cp.answer.length === cp.options.length,
    `checkpoint ${id} answer is well formed for kind=${cp.kind}`
  );
}

// ---- content: the rules VERIFY will enforce ------------------------------
const blocks = content.tracks.flatMap((t) => t.stops.flatMap((s) => s.blocks));
const claims = blocks.filter((b) => b.type === "prose").flatMap((b) => b.claims);
const steps = blocks.filter((b) => b.type === "trace").flatMap((b) => b.steps);
const cited = [...claims.filter((c) => c.cite), ...steps];

chk(
  !/"(start|end)"\s*:\s*\d/.test(JSON.stringify(content)),
  "content carries NO line numbers (non-negotiable #7)"
);
chk(
  claims.filter((c) => c.status === "verified").every((c) => c.cite && c.cite.quote),
  "every verified claim carries a quote"
);
chk(
  claims.filter((c) => c.status === "inferred").every((c) => !c.cite),
  "no inferred claim carries a cite"
);
chk(
  claims.every((c) => c.status === "verified" || c.status === "inferred"),
  "no claim is pre-marked dropped — only stage 4 drops"
);
chk(
  cited.every((c) => (c.cite.focus || []).every((f) => c.cite.quote.includes(f))),
  "every focus string is a substring of its own quote"
);
const ids = claims.map((c) => c.id);
chk(new Set(ids).size === ids.length, "claim ids are unique", `${ids.length} claims`);

// ---- the deliberate failures the fixture exists to exercise --------------
const badCp = blocks
  .filter((b) => b.type === "checkpoint")
  .map((b) => b.id)
  .filter((id) => !(id in survey.checkpoints));
chk(badCp.length === 1, "exactly one unresolvable checkpoint reference", badCp.join(", "));

const captured = new Set(commands.runs.map((r) => r.cmd));
const uncaptured = blocks
  .filter((b) => b.type === "command")
  .map((b) => b.cmd)
  .filter((c) => !captured.has(c));
chk(uncaptured.length === 1, "exactly one command with no real capture", uncaptured.join(", "));

const doomed = new Set(verified.dropped.map((d) => d.id));
const present = claims.filter((c) => doomed.has(c.id)).map((c) => c.id);
chk(
  present.length === doomed.size,
  "content contains every claim the verified ledger says was dropped",
  `${present.length}/${doomed.size}`
);

// ---- commands: output is real or the run is a fraud (non-negotiable #4) ---
chk(commands.runs.every((r) => r.out && r.out.trim().length > 0), "every run has non-empty out");
chk(
  commands.runs.every((r) => typeof r.dur === "string" && typeof r.dur_ms === "number"),
  "every run has both dur and dur_ms"
);
chk(
  commands.runs.filter((r) => r.exit !== 0).length === verified.report.failed,
  "failing-command count matches verified report.failed",
  String(verified.report.failed)
);

console.log(
  failed ? `\n${failed} CHECK${failed > 1 ? "S" : ""} FAILED\n` : "\nFIXTURE CHAIN CONSISTENT\n"
);
process.exit(failed ? 1 : 0);
