# Diagram Audit — vol-project-ref (2026-06-01)

17 figures: 16 already-clean, 1 fixed, 0 need human

## Results

| guide | file | id | status | blocking (before -> after) | note |
|---|---|---|---|---|---|
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch01-what-we-forecast.tex | fig:pipeline | already_clean | 1 -> 1 | Deterministic node_overlap (100%) is a false positive from row-level bbox union; visually all nodes are well-separated, text legible, arrows clear. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch03-har-core.tex | fig:harq-shrinkage | already_clean | 6 -> 6 | Figure itself is clean and legible; all 6 script-flagged blocking defects (text overlaps, node_overlap 100%) are in body text and tcolorbox callouts below the figure, not in the diagram. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch05-options-implied.tex | fig:options-horizon | fixed | 29 -> 0 | Moved legend from top-right (0.98,0.95 north east) to top-left (0.02,0.98 north west) so it no longer collides with the tallest orange h=22 bar, and raised ymax 14->16 for headroom; the "10" data label is now fully visible. Visual crop is clean; remaining deterministic node_overlap flags are false positives generic to interior-legend bar charts with nodes near coords. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch07-cross-asset.tex | fig:vol-network | already_clean | 2 -> 2 | 2 deterministic "node_overlap" blocking entries are false positives capturing the unrelated full-width tcolorbox callout panels below the figure; the actual network diagram has well-separated nodes, correctly directed labeled edges, and reads cleanly. Only warn-level 6pt w_k labels, which remain legible. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch08-feature-composition.tex | fig:diminishing-returns | already_clean | 7 -> 7 | 7 blocking node_overlap entries are false positives from axis/frame rectangle geometry; rendered bar chart reads cleanly with legible labels. Minor warn-level crowding of y-axis '60' tick against the '55' bar value label, not blocking. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch10-lstm-intraday.tex | fig:lstm-pipeline | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch11-ensemble.tex | fig:ensemble-arch | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch12-rashomon.tex | fig:rashomon-pipeline | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch13-evaluation.tex | guides/vol-project-ref/chapters/ch13-evaluation.tex:61 | already_clean | 1 -> 1 | The 1 deterministic "blocking" node_overlap is a false positive: its bbox maps to flowing body paragraph text ("We use purged 5-fold CV...", the 13.2.2 heading), not the figure. The figure itself (Train/Purge/Embargo/Test/Purge timeline with brace and time axis) is fully legible with no overlaps. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch13-evaluation.tex | guides/vol-project-ref/chapters/ch13-evaluation.tex:109 | already_clean | 1 -> 1 | Walk-forward figure is clean; the 1 deterministic node_overlap (y=553-678pt) is the adjacent purged-CV figure's Purge/Embargo labels, not this target. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch13-evaluation.tex | fig:mcs-flowchart | already_clean | 4 -> 4 | All 4 deterministic "blocking" defects are false positives located in callout boxes/body text below the figure (inspector cropped the whole page); the flowchart itself has clean, well-separated nodes, unambiguous Yes/No arrows, and a correct loop-back, fully legible. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch13-evaluation.tex | fig:eval-workflow | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch14-complete-pipeline.tex | fig:full-pipeline | already_clean | 9 -> 9 | Deterministic blocking flags are false positives: edge labels (tabular/intraday seq./raw bars) are small but legible; node "overlaps" are bbox artifacts with no real collision; 100% overlap is outside the figure in body text. Diagram reads cleanly. |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch15-pipeline.tex | fig:data-funnel | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch16-architecture.tex | fig:architecture-comparison | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch17-modular-pipeline.tex | fig:pipeline-plugpoints | already_clean | 0 -> 0 | none |
| guides/vol-project-ref | guides/vol-project-ref/chapters/ch18-development-plan.tex | fig:critical-path | already_clean | 8 -> 8 | Checker flags 8 node_overlap blocking defects, but rendered crop shows clean, well-spaced nodes; all text legible, arrows unambiguous — false positives. |

## Needs human

None. No figures require human intervention.

## Fixed

- **fig:options-horizon** (guides/vol-project-ref/chapters/ch05-options-implied.tex, 29 -> 0): Moved the legend from top-right (`0.98,0.95` north east) to top-left (`0.02,0.98` north west) so it no longer collides with the tallest orange h=22 bar, and raised `ymax` 14 -> 16 for headroom so the "10" data label is fully visible.

[Contact sheet](./2026-06-01-vol-project-ref-contact-sheet.png)
