# Trailhead - GS AI Hackathon, 30–31 July 2026

**Theme:** Improve the Developer Experience · **Categories:** Saving Time, Improving User Experience

---

## 1. Summary

Trailhead turns a code repository into a single web page that teaches it. Point it at a repo and you get one file that walks a reader through what the code does, how to run it, and how one request flows through it. Every factual sentence carries a button opening the exact lines of code behind it.

What matters is what happens to sentences it *cannot* back up: they are deleted before anyone sees the page, and the number deleted is printed on screen.

| Term | Meaning |
|---|---|
| **claim** | One factual sentence in the generated page |
| **anchor** | The `file:line` range a claim cites, plus those lines and a checksum |
| **`verified.json`** | The data file the page is built from - the frozen generator-to-page contract |

---

## 2. The problem

Reading code you did not write is slow, and it is not only a new-joiner problem - the same cost lands on experienced engineers several times a year.

| Situation | What they need | Where the time goes today |
|---|---|---|
| **New joiner onboarding** | A map before the detail | Files read in arbitrary order; asking a colleague costs two people |
| **Engineer entering an unfamiliar module** | Boundaries, conventions, blast radius | Grep-and-guess; conventions live in one or two heads |
| **Returning to code after months** | What it does, and why | Re-deriving decisions the code never recorded |
| **Understanding a set of changes** | What moved, and what it affects | A diff without the structure to judge its consequences |

**The answer is already in the repo - the cost is locating it and trusting it.** Documentation solves locating, then decays. Asking a person keeps trust but spends two people's time.

> **Scope note.** Trailhead covers the first three cases today. The fourth is roadmap, not a current feature - see §10.

---

## 3. What Trailhead does

Five stages run in order. Only one uses AI.

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
| 1 Survey | No | File tree, import edges, entry points, git churn |
| 2 Map | No | Collapse to modules; compute the diagram layout up front |
| 3 Narrate | **Yes** | The prose - one small call per unit, returning claims plus verbatim quotes |
| 4 Verify | No | Re-open every file, hash-match every excerpt, delete what fails |
| 5 Render | No | Turn `verified.json` into one HTML file |

A command runner executes the repo's own setup and test commands, capturing real exit codes, output and timings.

---

## 4. Innovation - the model writes, the machine checks

Most tools ask a model to explain your code and print what it says. Trailhead assumes the model will sometimes be confident and wrong, and puts an automated checker between it and the reader.

**Only stage 3 touches a model.** Everything that checks is deterministic code - a model cannot be its own auditor.

**Never ask for line numbers; ask for a quote.** Models count badly and copy well. The model receives the file with line numbers attached and must return the snippet it cites; code then locates that snippet and derives the range. A snippet not found word-for-word is deleted, not repaired.

**Deleted claims are counted on screen.** The badge opens a ledger of every deletion and its reason. Hiding the number would defeat the point of computing it.

**Commands are run, not described.** Exit codes, output and timings come from real execution; failing commands are shown failing, with any suggested cause marked unverified.

---

## 5. How a claim is checked

All of the above rests on one question: when the page tells you something about the code, why should you believe it? Because a claim must pass a mechanical test before it is allowed onto the page - and that test is ordinary code that never asks a model anything.

Each claim arrives as a sentence plus the **verbatim snippet** it says it is citing, never a line number. The snippet then has to survive five checks:

1. **Quality floor** - at least two lines and 40 non-whitespace characters. Shorter quotes are not distinctive enough to locate reliably.
2. **Exact match** - searched for character-for-character in the cited file. No fuzzy matching, no whitespace-insensitive comparison, no closest-match fallback; a fallback that can land in the wrong place is the exact failure this exists to prevent.
3. **Exactly one match** - if the snippet appears twice, the claim is deleted rather than guessed at. Measured on a real repo, 12.8% of two-line quotes occur more than once in their own file.
4. **The right file** - if it resolves in a file other than the one cited, the claim is deleted. Without this check, a wrong-file citation would display as verified with a valid checksum.
5. **Checksum** - the cited lines are hashed, and the copy shipped inside the page is re-hashed by an automated gate. A mismatch means what you are reading is not what was checked.

A claim failing any check is removed from the page entirely and listed in the ledger with its reason. Twelve reasons are defined; these fire most:

| What went wrong | What the reader sees |
|---|---|
| Snippet is not in the file word-for-word | `snippet not found verbatim in file` |
| Snippet appears more than once | `snippet ambiguous` |
| Snippet is really in a different file | `snippet belongs to a different file than the one cited` |
| The file changed after the prose was written | `excerpt hash mismatch: file changed after narration` |
| The model returned something unusable | `model returned unparseable output` |

> **What this does not check.** None of it establishes that a sentence is a *good description* of the code - only that it cites real code, uniquely, where it says it does. That boundary is deliberate. Anything unanchorable is marked `INFERRED` on screen instead of dressed up as fact; the most interpretive part of the walkthrough is marked inferred wholesale; command output comes from execution, not description. What is guaranteed is that the evidence is real and is the evidence that was checked - narrower than "correct", and something ordinary code can guarantee with no model in the loop.

The resolver is specified in full and written test-first. Stage 4 is not yet built - see §10.

---

## 6. Impact

### Saving time

Generated once per commit, read many times. Two costs disappear: the "who do I ask" hop, and the "is this still true" re-check.

**Time saved per reader: [TBD - needs measurement].** No figure is quoted because none has been measured; inventing one would contradict the premise of the project.

Assumptions any figure would rest on, stated so they can be challenged:

- The reader would otherwise interrupt a colleague - the real cost is two people's time
- Generation is amortised: one run serves every later reader of that commit
- The walkthrough covers what people ask first - orientation, setup, one end-to-end path

**The experiment that would produce the number:** two engineers, one unfamiliar repo, five comprehension questions, one with Trailhead and one without; record time to correct answers.

### Improving user experience

| Today | With Trailhead |
|---|---|
| You must know what to ask before a chatbot helps | A fixed route; no question needed to start |
| Answers arrive with no evidence | Every claim expands to the lines behind it |
| Docs may be stale and you cannot tell | Unbackable claims deleted; the count is on screen |
| Setup steps may not work | Commands were executed; failures shown failing |
| Needs a network, a login, a tool | One file, opens offline from `file://` |

---

## 7. Feasibility

Some of this is built and machine-checked today; the rest is not. Both gates pass, output quoted verbatim.

```
node tools/check-bundle.js     → BUNDLE OK, exit 0    (21 structural checks, 125.2 KB)
node tools/verify-contract.js  → ALL ANCHOR + CONTRACT CHECKS PASS, exit 0
                                 payments-core: 5 tracks, 11 stops, 13 anchors sha256-verified
                                 ML-GS:         5 tracks, 12 stops, 17 anchors sha256-verified
PYTHONPATH=src py -3.11 -m unittest discover -s tests → Ran 8 tests, OK
```

| Piece | State |
|---|---|
| Artifact spec - 9 sections, 12 acceptance tests | Done |
| `verified.json` contract | Frozen |
| Renderer - all 9 block types | Working |
| Automated gates | Both passing |
| Verification design - resolver, drop vocabulary, hash recipe | Specified in full |
| Stage 1 Survey | Partial - import parsing, 8 tests; no file walker |
| Stages 2, 4, command runner | Not built |
| Stage 3 Narrate | Not built; AI tool not yet selected |

Budget is 10 hours, with the pivot rule fixed in advance: if the generator loop is still unreliable at hour 4, hard-code the demo path rather than chase generality.

---

## 8. What you see on screen

It reads like a short course, not a chat window - one screen at a time, contents rail down the left.

- **Top bar** - repo, commit, generation date; a badge showing claims, deletions, commands, failures; projector mode, theme, reset
- **Left rail** - the route in five tracks, a tick per completed stop, overall progress
- **Main column** - one stop at a time: prose, excerpts, module diagram, command output, checkpoints
- **Claim marker** - click a marked sentence; the cited lines appear, numbered and highlighted, with a copy button
- **Badge** - opens the ledger of deleted claims and the reason for each
- **Checkpoints** - graded in the page against a key derived from survey data, never a model; with no model present to grade free text, questions are multiple-choice or ordering
- Progress is saved per commit, so a regenerated walkthrough starts clean

---

## 9. Demo - the 60-second path

1. Open `hackathon/demo/trailhead-demo.html` - no server, no network
2. Read the top-bar badge: claims, deletions, commands, failures
3. Click it - the ledger lists every deleted claim and why
4. Open **Five things to know**, click a claim marker - the cited lines appear
5. Open **Run the gates** - real captured output, including a command that failed
6. Use the repo switcher to move between the two walkthroughs

---

## 10. Status, risks and next steps

Stated plainly, because a page about verification that overstated itself would be self-defeating.

| Item | Detail |
|---|---|
| **No model has run through the pipeline yet** | Stage 3 is not built; both walkthroughs were written by hand against the frozen contract. The checks in §5 are specified and test-driven, but the deletion counts shown are authored, not observed. |
| **One demo repo is synthetic** | `payments-core` does not exist - it is test data, labelled `SAMPLE · SYNTHETIC REPO` on screen. Its command output is illustrative, not captured. |
| **The real walkthrough's anchors are pinned to an older commit** | `ML-GS` cites commit `fb3c3ce`. Four of its eight cited files match that commit byte-for-byte, 14 of 14 lines. The other four were untracked then, and two have since been rewritten - 93 of 112 bundled lines no longer match the working tree. |
| **Why the gates still pass** | The gate recomputes each checksum from the copy shipped inside the page, proving the excerpt was not altered after generation. Re-opening the file on disk is stage 4's job, and stage 4 is not built - precisely the gap §5 closes once it ships. |

**Next, in order:** stage 4, so anchors are re-checked against disk; the command runner; select and wire the AI tool for stage 3; regenerate against a repo nobody has read; measure the time saved.

---

## Judging criteria - where the evidence is

| Criterion | Evidence on this page |
|---|---|
| **Innovation** | §4 - verification is deterministic code, not a second model; quote-not-line-numbers. §5 - the five checks a claim must survive and the twelve ways it can be deleted. §3 - one stage of five uses AI. |
| **Impact** | §2 - four situations, and where the time goes in each. §6 - mechanism and assumptions stated; the figure marked `[TBD]` rather than invented, with the experiment named. |
| **Feasibility** | §7 - both gates pass with output quoted, 8 tests pass, contract frozen, verification design specified in full, 10-hour budget with a written pivot rule. §10 - what is not built. |
| **User experience** | §8 - on-screen anatomy. §9 - a 60-second path anyone can follow. §6 - one offline file, evidence one click away, no question needed to start. |
