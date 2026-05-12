# Design Spec: Vol-Project-Ref Ch17 -- Modular Pipeline Design

**Date:** 2026-05-12
**Status:** Draft
**Scope:** One new chapter (ch17) for `guides/vol-project-ref/`, bumping existing ch17 (development plan) to ch18

---

## 1. Overview

### What we're adding

A new Chapter 17: Modular Pipeline Design, inserted between the current ch16 (System Architecture) and the current ch17 (Development Plan, which becomes ch18).

### Why

Chapters 14-16 describe the logical pipeline, feature lineage, and ensemble architecture. None of them show the software design that makes the system modular. This chapter fills that gap: config-driven experiments, registry-based composition, and the ability to swap features, models, and CV strategies without code changes.

### Design constraints

- **Same style** as existing vol-project-ref chapters: terse, table-driven, booktabs tables, TikZ diagrams, 1-2 boxes per chapter (keyidea + warning only).
- **No em dashes** in text.
- **No fluff.** Show how it works, not why modularity is good.
- **No developer onboarding.** This is a project reference showing capabilities, not a guide for extending the system.
- **Zero repetition** with existing chapters. No logical pipeline ordering (ch14), no feature lineage (ch15), no ensemble architecture (ch16), no development milestones (ch18).
- **~100-120 lines.**

### What existing chapters cover (overlap guard)

| Chapter | Covers | Ch17 must NOT repeat |
|---|---|---|
| Ch14 | End-to-end system diagram (Figure 14.1), 6-step implementation order, retraining/monitoring, lookahead checklist | Logical pipeline diagram, implementation step details |
| Ch15 | Feature lineage funnel (Figure 15.1), complete feature matrix (Table 15.1) | Feature definitions, derivation chains, source-to-measure mapping |
| Ch16 | Three ensemble architectures (Figure 16.1), feature stacking vs residual stacking vs prediction blending | Ensemble model architecture, architecture comparison |
| Ch09 | LightGBM config, QLIKE objective, Table 9.1 (layer/features/count) | Model configuration details |
| Ch13 | QLIKE formula, CV methodology, walk-forward, success targets | Evaluation methodology, metric definitions |

---

## 2. Chapter Structure

### Opening (2-3 lines)

Chapter 14 gives the logical pipeline order. Chapter 16 describes the ensemble model architecture. This chapter describes the software design: config-driven, registry-based, every experiment defined by one YAML file. No code changes to run a different experiment.

### Figure 17.1: Pipeline Architecture with Plug Points

Combined TikZ diagram showing four pipeline stages (INGEST, TRAIN, EVALUATE, COMPARE) driven by a CONFIG node. Key design decisions:

- **CONFIG** is a distinct shape (rounded rectangle, blue fill) on the left, feeding into all stages via a single arrow into INGEST.
- **INGEST, TRAIN, EVALUATE** are processing stage boxes (green fill for INGEST/EVALUATE, orange fill for TRAIN).
- **COMPARE** has a dashed border (future/not yet implemented).
- **TRAIN is visually dominant** -- it is the modular hub where all three registries plug in.
- **Three registry boxes** hang below TRAIN, connected by arrows:
  - FEATURE_REGISTRY (lists: har_core, asymmetry, options, ...)
  - MODEL_REGISTRY (lists: har, harq, lightgbm, ...)
  - CV config (lists: method, n_splits, purge_gap, ...)
- **Color coding:** blue for config/data, green for fixed computation stages, orange for the modular TRAIN stage. Matches ch14/ch15/ch16 color conventions.
- **Stage descriptions inside boxes:** INGEST = "ticks to bars to 18 measures", TRAIN = "features + model + CV splits", EVALUATE = "QLIKE, MSE, R-squared", COMPARE = "DM, MCS".
- **No overlapping boxes or arrows.** Clean spacing. Consistent node sizes for the four stages. CONFIG node slightly smaller.

### Section: Plug Points

One `\section{}` with three `\subsection{}` blocks. No section divider comments between subsections (they're too short to warrant them).

**\subsection{Feature Layers} (~3-4 lines)**

The `feature_layers` list in the config names the layers to compose. The pipeline iterates the list, resolves each from `FEATURE_REGISTRY`, and calls `.compute()`. Adding a layer to the experiment means adding one string to the list. Points to Chapter 15 Table 15.1 for the full feature inventory.

**\subsection{Models} (~3-4 lines)**

The `model.name` field selects the model class from `MODEL_REGISTRY`. All models satisfy the same `VolModel` protocol. Swapping HAR for LightGBM means changing one line in the config. Model-specific hyperparameters go in `model.params`. Points to Chapter 9 for LightGBM configuration.

**\subsection{Cross-Validation} (~3-4 lines)**

The `cv.method` field selects the splitter: expanding window, rolling window, purged k-fold, or blocked k-fold. All produce time-aware train/test splits with a configurable purge gap. Points to Chapter 13 for evaluation methodology.

### Side-by-Side YAML Configs

Two `lstlisting` environments inside `minipage` blocks (each 0.47\textwidth), presented as a figure or listing pair. Left: HAR baseline config. Right: LightGBM with more feature layers and different CV.

**Left config:**
```yaml
name: baseline_har
universe: [SPY]
horizons: [1, 5, 22]
feature_layers: [har_core]
model:
  name: har
cv:
  method: expanding_window
  purge_gap: 5
```

**Right config:**
```yaml
name: lgbm_full
universe: [SPY, AAPL, MSFT, NVDA]
horizons: [1, 5, 22]
feature_layers:
  - har_core
  - asymmetry
  - options
  - cross_asset
model:
  name: lightgbm
  params: {num_leaves: 31}
cv:
  method: purged_kfold
  purge_gap: 22
```

No annotation prose needed. The contrast speaks for itself. A one-line caption: "Two experiments, same pipeline. Left: HAR baseline. Right: LightGBM with four feature layers."

### Boxes

1. **keyidea: "One YAML, One Experiment"** -- The entire experiment (universe, horizons, features, model, CV strategy) is defined by a single config file. Reproducing or modifying an experiment means copying the file and changing values, not code.

2. **warning: "Registries Require Import"** -- Feature layers and models register via decorators at import time. A new layer or model that is never imported will not appear in the registry. The package `__init__.py` triggers all registration imports.

---

## 3. Files to Create

| File | Purpose |
|---|---|
| `guides/vol-project-ref/chapters/ch17-modular-pipeline.tex` | Modular pipeline design chapter |

## 4. Files to Modify

| File | Change |
|---|---|
| `guides/vol-project-ref/main.tex` | Rename ch17 input to ch18, insert new ch17 input |
| `guides/vol-project-ref/chapters/ch17-development-plan.tex` | Rename to ch18-development-plan.tex, update `\chapter` label |

## 5. LaTeX Conventions (matching existing guide)

- `\chapter{Title}` with `\label{ch:short-name}`
- Sections marked with `%% ------` visual dividers (for main sections, not subsections)
- Tables: booktabs (`\toprule`, `\midrule`, `\bottomrule`), `\small` font, `@{}` column padding
- TikZ diagrams: blue for data/config, green for computation, orange for models
- Boxes: `\begin{keyidea}[Title]` and `\begin{warning}[Title]` only
- Citations: `\citep{}` parenthetical, `\citet{}` textual
- Cross-references: `Chapter~\ref{ch:...}`, `Figure~\ref{fig:...}`, `Table~\ref{tab:...}`
- No em dashes
- YAML listings: `lstlisting` with basic formatting, `\scriptsize` font

## 6. Diagram Review

During implementation, dispatch a subagent to independently review the TikZ diagram for:
- No overlapping boxes or arrows
- Clean visual spacing and alignment
- Color consistency with ch14/ch15/ch16 diagrams
- All nodes labeled, all connections shown
- TRAIN visually dominant as the modular hub
- COMPARE correctly shown as dashed/future
- Registry boxes clearly connected to TRAIN stage only
