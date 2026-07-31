# The target artifact: hand-built walkthrough of ml-vol-estimator

`../out/trailhead-mlvol-template.html` is the walkthrough the generator should
aspire to produce: one self-contained HTML file that teaches the restored
ml-vol-estimator repo (`hackathon/restored/`) with every factual sentence
anchored, hashed, and re-checked. It exists so we can see what "perfect output"
looks like before teaching the pipeline to approximate it.

## How it is built

Same discipline as the real pipeline, in miniature:

| Piece | Job |
|---|---|
| `dossiers/*.json` | 10 reader dossiers over the repo: claims carry VERBATIM QUOTES, never line numbers |
| `payload.mjs` | the authored walkthrough: tracks, stops, map narration, glossary, checkpoints; claims reference dossier quotes |
| `captures/*.txt` | real command output captured on this machine; never edited (dash chars transliterated at build) |
| `build.mjs` | resolves each quote to a line range against the snapshot, computes sha256, bundles excerpt lines, DELETES claims whose quotes fail (they land in the on-screen ledger), splices into the template, runs gates |
| `walkthrough.template.html` | the renderer: GS-token shell, engineering-grid background, layered map with drawers and guided tour, glossary popovers, predict blocks, checkpoints, audit panel |
| `verify.mjs` | independent stage-4 style re-check: re-reads every anchor from disk, recomputes every hash, asserts the badge equals the payload, re-scans for barred dashes and live external references |

```bash
cd hackathon/template
node build.mjs     # writes ../out/trailhead-mlvol-template.html
node verify.mjs    # must print VERIFY PASSED
```

## House rules this artifact obeys

- No em or en dash anywhere in the file (build and verify both scan).
- No `<a>` elements, no live external references, no font at-rules.
- Command output is real captured output; failures shown failing.
- Claims that cannot be anchored are marked INFERRED or deleted and counted.
- The 14 restore-gap modules are surfaced in their own ledger, not hidden.

## What the generator should steal from this

1. Node drawers with real narration (role paragraphs, key files, flows in/out).
2. The layered column map with default-dim edges and the guided tour.
3. Whole-sentence claim interaction plus glossary term popovers.
4. The restore/missing-module ledger pattern for honest degradation.
5. Quote-based anchoring with the non-adjacent-line matcher in `build.mjs`.
