# Trailhead - GS AI Hackathon, 30-31 July 2026

**Theme:** Improve the Developer Experience · **Categories:** Saving Time, Improving User Experience

---

## 1. Summary

**Trailhead is not a single prompt.** It is a five-stage pipeline in which four stages are deterministic Python, plus two Node gate scripts and a 700-test suite - the model writes prose in exactly one stage, and ordinary code checks every sentence it writes. Point it at a repo and you get one self-contained web page that teaches it: what the code does, how to run it, how one request flows through it, and a clickable evidence trail behind every factual sentence.

What matters is what happens to sentences it *cannot* back up: they are deleted before anyone sees the page, and the number deleted is printed on screen.

| Term | Meaning |
|---|---|
| **claim** | One factual sentence in the generated page |
| **anchor** | The `file:line` range a claim cites, plus those lines and a sha256 |
| **`verified.json`** | The data file the page is built from - the frozen generator-to-page contract, now `trailhead/verified@3` |

---

## 2. The problem

Reading code you did not write is slow, and it is not only a new-joiner problem - the same cost lands on experienced engineers several times a year.

| Situation | What they need | Where the time goes today |
|---|---|---|
| **New joiner onboarding** | A map before the detail | Files read in arbitrary order; asking a colleague costs two people |
| **Engineer entering an unfamiliar module** | Boundaries, conventions, blast radius | Grep-and-guess; conventions live in one or two heads |
| **Returning to code after months** | What it does, and why | Re-deriving decisions the code never recorded |

**The answer is already in the repo - the cost is locating it and trusting it.** Documentation solves locating, then decays. Asking a person keeps trust but spends two people's time.

---

## 3. What Trailhead is, mechanically

Five stages run in order. Only one uses AI. All five are built and tested.

```
repo ──▶ 1 SURVEY ──▶ survey.json ──▶ 2 MAP ──▶ map.json
                          │                        │
                          └──▶ 3 NARRATE (LLM) ──▶ content.json
                                                     │
                                    4 VERIFY ◀───────┘
                                        │
                    verified.json + verification-report.json
                                        │
                                   5 RENDER ──▶ trailhead.html
```

| Stage | AI? | Job |
|---|---|---|
| 1 Survey | No | File tree, import graph, entry points, dangling imports, churn - stdlib `ast`, Python only |
| 2 Map | No | Collapse 300+ modules to a board of ~11 groups; DAG-layered columns; test containers taken off-board; geometry computed up front, no layout engine in the page |
| 3 Narrate | **Yes** | Prose only. One self-describing prompt pack per unit; the model answers with claims plus verbatim quotes, never line numbers |
| 4 Verify | No | Re-open every cited file, resolve every quote, hash every excerpt, delete what fails, assemble the payload |
| 5 Render | No | Splice one JSON payload into a fixed renderer template; refuse anything that would render a lie or a blank page |

Plus a **command runner** (before narrate, deterministic) that executes the repo's own allowlisted setup and test commands and captures real exit codes, output and timings - a failing command ships failing.

Narrate runs as two CLI passes with an agent step in between: pass A emits the packs and stops; the host agent answers each pack into the narration store; pass B replays the store with no live model in the loop. For the proving-ground repo that is 22 packs across 9 unit kinds.

---

## 4. Innovation - the model writes, the machine checks

**Only stage 3 touches a model.** Everything that checks is deterministic code - a model cannot be its own auditor.

**Never ask for line numbers; ask for a quote.** Models count badly and copy well. The model sees numbered windows and must return the verbatim snippet; code locates it and derives the range. A snippet not found word-for-word is deleted, not repaired.

**Deleted claims are counted on screen.** The badge opens a ledger of every deletion and its reason. This is now observed behaviour, not design intent: the first full generation run deleted 10 of 65 claims (quotes taken outside the shown windows, one docstring duplicated across two files, one over-length answer). They were re-answered honestly; the final run carries 0 deletions because every anchor resolves, and the ledger says which of those two worlds you are in.

**Commands are run, not described.** 4 commands executed on the demo repo, 3 failing, shown failing, with cause hypotheses explicitly tagged INFERRED.

---

## 5. How a claim is checked

Each claim arrives as a sentence plus the **verbatim snippet** it cites. The snippet must survive: a quality floor (length and distinctiveness), exact character-for-character match, exactly one match, in the cited file, inside the window the model was shown, then a sha256 over the resolved lines - recomputed by stage 4 against disk and again by the gate against the copy shipped inside the page. Failing any check deletes the claim and ledgers the reason; twelve reasons are defined.

> **What this does not check:** that a sentence is a *good* description - only that it cites real code, uniquely, where it says it does, and that the evidence shipped is the evidence checked. Anything unanchorable is marked `INFERRED` on screen instead of dressed up as fact.

The same machinery now verifies every new `@3` surface: glossary anchors, map-node excerpts, and tour references all resolve, hash, and drop through the same ledger (`g-`, `n-`, `t-` prefixed entries).

---

## 6. What is new since the spec (contract `@3`)

The hand-built walkthrough at `out/trailhead-mlvol-template.html` was authored first as the quality lock; the generator was then rebuilt until its output matches it. The renderer in the pipeline **is** that template. Everything below is generated for any repo, degrades to the old `@2` page when narration is absent, and is enforced by the extended gates:

| Feature | What it is |
|---|---|
| **Whole-sentence evidence** | Every verified sentence is clickable; the excerpt opens inline with real line numbers and a sha chip |
| **Narrated node drawers** | Click any map module: 2-3 role paragraphs, what flows in and out, key files with purposes, concept chips, one anchored excerpt. Falls back to mechanical stats when unnarrated |
| **Layered map** | Import-DAG columns with model-narrated labels; edges dim by default, hover isolates; tests off-board with an honest note |
| **Guided tour** | Steps through the board from the entry point with narration; BACK / NEXT / OPEN |
| **Glossary** | Dotted terms in prose open popovers with a jump to the defining lines; a glossary stop lists all terms; dead references are rewritten to plain text at verify |
| **Stats tiles** | Cover metrics straight from `survey.json` - loc, files, modules, tests, commands, missing modules |
| **Restore ledger** | When imports resolve to no file on disk (14 modules, 706 sites on the demo repo), a table names them instead of writing around them |
| **Dive stops** | An INSIDE THE SYSTEM track: one narrated deep-dive per major subsystem, each with prose, an anchored excerpt, and group stats |
| **Predictions and confidence** | Command results and trace hops veil until you predict; checkpoints capture sure/guessing before answering; a YOUR RECORD panel reports confident-and-wrong |
| **Honest provenance** | The ledger footer prints the real regeneration command; checkpoint answer keys still come from `survey.json`, never a model |
| Plus | Engineering-grid GS shell, cover START, mobile rail, print linearises every stop, keyboard-complete, light and dark |

---

## 7. Feasibility - current state, all machine-checked

```
PYTHONPATH=src python -m pytest tests/ → 587 passed, 122 subtests passed
node tools/check-bundle.js out/restored.html    → BUNDLE OK
node tools/verify-contract.js out/restored.html → ALL ANCHOR + CONTRACT CHECKS PASS (72 anchors sha256-verified)
node tools/check-fixtures.js                    → FIXTURE CHAIN CONSISTENT
```

| Piece | State |
|---|---|
| Stages 1-5 + command runner | Built, tested, run end to end |
| Contract `trailhead/verified@3` | Frozen, gate-enforced with negative tests and a parity fixture |
| Generated demo | `out/restored.html`: 17 stops, 63 claims (49 verified / 14 inferred / 0 dropped), 27 live glossary terms, both gates green |
| Quality lock | `out/trailhead-mlvol-template.html`: hand-built target the generator is judged against |
| Genericity | Four fixture repos generate cold (no narration) with honest degradation and green gates, pinned by tests |

---

## 8. Demo - the 60-second path

1. Open `hackathon/out/restored.html` - no server, no network
2. Read the badge: 63 claims, 0 dropped, 4 cmds, 3 failing; click it for the ledger
3. On **Five sentences**, click any sentence - the cited lines open with a sha chip
4. On **The map**, hit GUIDED TOUR, then click the `data` node for its drawer
5. On **Prerequisites and setup**, answer the prediction, then read the missing-modules restore ledger
6. Open any **Inside ...** stop and click a dotted glossary term

---

## 9. What is still missing

Stated plainly, because a page about verification that overstated itself would be self-defeating.

| Item | Detail |
|---|---|
| **Checkpoint breadth** | 4 derived checkpoints in 2 stops; the quality lock carries 13 across 5. More deterministic key sources needed (GET IT RUNNING, dives, conventions have none) |
| **Glossary depth** | Pack caps at 14 terms; the lock carries 28. Raising the cap is a prompt-pack change |
| **Trace discovery** | The 8-hop trace for the demo repo is a hand-checked fixture (by design); automatic trace discovery for arbitrary repos is not built - repos without a fixture get an honest degradation callout |
| **Named AI tool** | Narrate runs as host-agent-answered prompt packs (any model) or a live provider; which internal GS tool it names on stage is still the open decision |
| **Language scope** | Python-only survey via stdlib `ast`, deliberately |
| **Time saved** | Unmeasured. The experiment: two engineers, one unfamiliar repo, five comprehension questions, with and without Trailhead |

---

## Judging criteria - where the evidence is

| Criterion | Evidence |
|---|---|
| **Innovation** | §4 - deterministic checker between model and reader, quote-not-line-numbers, observed deletions on screen. §5 - the checks and the drop vocabulary. §3 - one stage of five uses AI |
| **Impact** | §2 - where the time goes. §7 - generated once per commit, read many times, offline |
| **Feasibility** | §7 - full pipeline built, 587 tests, gates green on generated output, genericity pinned on fixture repos. §9 - what is not built, stated |
| **User experience** | §6 - the feature set. §8 - a 60-second path anyone can follow |
