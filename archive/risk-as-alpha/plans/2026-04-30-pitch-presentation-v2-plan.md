# Pitch Presentation v2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the pitch presentation, speaker script, and Q&A battle card as a 5-slide product pitch for the Risk as Alpha index, replacing the 11-slide research-proposal framing.

**Architecture:** Three independent deliverable files. The HTML slide deck is the largest task (reuses v1 CSS styling, rebuilds slide HTML). The speaker script and battle card are markdown files. All three can be built in parallel since they have no code dependencies on each other.

**Tech Stack:** HTML/CSS (slide deck), Markdown (script and battle card). No build tools, no JavaScript changes beyond updating the slide count.

**Spec:** `docs/superpowers/specs/2026-04-30-pitch-presentation-v2-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `deliverables/pitch_presentation_v2.html` | Create | 5 main slides + 3 backup slides. Single-file HTML with embedded CSS and JS. Reuses v1 styling classes. |
| `deliverables/speaker_script_v2.md` | Create | Speaker reference script for the 5-slide structure. ~15-17 min delivery. |
| `deliverables/qa_battle_card.md` | Modify | Add 12 new questions with answers across three new sections. Preserve all existing content. |

---

## Chunk 1: HTML Slide Deck

### Task 1: Create v2 HTML file with CSS and slide 1

**Files:**
- Reference: `deliverables/pitch_presentation.html` (v1 baseline for CSS)
- Create: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Create the HTML file with full CSS block**

Copy the entire `<head>` section from v1 including all CSS. Add one new CSS class for the two-tier product boxes used on slide 4. The CSS block from v1 is reused unchanged except:
- Add `.two-tier` grid class for the slide 4 right column (public index vs. internal index boxes -- two stacked boxes, one `.col-a` style and one `.col-b` style, within a single column)

All other slide layouts reuse existing v1 classes: `.two-col` for two-column layouts (slides 2, 4, 5), `.dual-banner` for the dual-value section (slide 2), `.stats-row`/`.stat-card` for stat cards (slide 3), `.edge-box`/`.edge-old`/`.edge-new` for the data edge comparison (slide 4), `.timeline-table` for the timeline (slide 5), `.wont-be` for the "what this won't be" strip (slide 5).

Start the `<body>` with slide 1 (title slide):

```html
<!-- SLIDE 1: Title -->
<div class="slide title-slide active" id="slide1">
  <h1>Risk as Alpha</h1>
  <p class="subtitle">A tradeable index from risk-system outputs</p>
  <div class="title-meta">
    <span>Ryan Vincent</span>
    <span>&middot;</span>
    <span>XA Strats</span>
    <span>&middot;</span>
    <span>May 2026</span>
  </div>
  <div class="slide-number">1 / 5</div>
</div>
```

- [ ] **Step 2: Verify the file opens in a browser**

Open `deliverables/pitch_presentation_v2.html` in a browser. Confirm the title slide renders correctly with the dark background, centered text, and proper styling.

- [ ] **Step 3: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: create v2 presentation with CSS and title slide"
```

---

### Task 2: Add slide 2 -- The Product

**Files:**
- Modify: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Add slide 2 HTML**

Two-column layout using the `.two-col` grid from v1. Left column: "What it does" with `.key-points` list. Right column: "Dual value" using `.dual-banner` adapted from v1 slide 6 but with two sub-sections (product + risk management). Bottom: pipeline strip using v1 `.pipeline` component with 5 nodes (Risk System -> Feature Engineering -> Models -> Predictions -> Index). Below pipeline: `.bottom-line` with the IC key line.

Content per spec slide 2:
- Headline: "A systematic index that trades on dealer balance-sheet constraints"
- Left: 4 bullet points (rules-based, risk-system inputs, prediction targets, instruments)
- Right: "As a product" paragraph + "As risk management" paragraph
- Pipeline: 5 nodes matching v1 pipe-node styling
- Key line: "Even a modest edge -- IC of 0.03-0.05 -- is tradeable through liquid instruments with real capacity."

- [ ] **Step 2: Verify in browser**

Open the file and navigate to slide 2. Confirm two-column layout renders, pipeline strip is visible, key line appears at bottom.

- [ ] **Step 3: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: add slide 2 -- the product"
```

---

### Task 3: Add slide 3 -- Why It Works

**Files:**
- Modify: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Add slide 3 HTML**

Two sections stacked vertically. Top: three `.stat-card` elements in a `.stats-row` grid (reuse v1 slide 3 stat cards exactly -- 77%, 6, Daily). Bottom: feature table with 5 rows (reuse v1 slide 5 table structure -- same columns: Feature Family, What It Measures, Why It Should Predict). Below table: `.bottom-line` with the key line.

Content per spec slide 3:
- Headline: "Intermediary asset pricing theory predicts these signals should exist. They've never been tested with the right data."
- Stat cards: 77% (Adrian, Etula & Muir 2014), 6 (He, Kelly & Manela 2017), Daily (the data edge)
- Feature table: VaR Utilization, Factor Concentration, VaR Dynamics, Scenario P&L, Cross-Asset Flow
- Key line: "These aren't proxies. VaR utilization literally is the constraint the theory says drives prices. Every feature has a theoretical prediction before any model is trained."

Note: font sizes on the feature table may need to be slightly smaller (16px instead of 18px for `td`) to fit both the stat cards and the full table on one slide. Test visually and adjust.

- [ ] **Step 2: Verify in browser**

Navigate to slide 3. Confirm stat cards render in a row, feature table is fully visible below them, and nothing overflows the viewport.

- [ ] **Step 3: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: add slide 3 -- why it works"
```

---

### Task 4: Add slide 4 -- Why Only GS

**Files:**
- Modify: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Add slide 4 HTML**

Two-column layout. Left column: data edge comparison using v1's `.edge-compare` layout but simplified into a single column (no arrow between two boxes -- instead, two stacked boxes: "What external researchers use" with x-mark items, "What SecDB provides" with checkmark items, using `.edge-box`, `.edge-old`, `.edge-new` classes from v1). Right column: two-tier product structure using two stacked boxes -- "Public index (the product)" and "Internal enhanced index (GS's edge)" -- styled with `.col-a` and `.col-b` classes from v1. Below both columns: `.bottom-line` with key line.

Content per spec slide 4:
- Headline: "The public version proves the thesis is real. The internal version is why GS should run it."
- Left: 4 items under "What external researchers use" (x marks), 4 items under "What SecDB provides" (checkmarks)
- Right: "Public index" with 3 bullets, "Internal enhanced index" with 3 bullets
- Key line: "The theory was proved with quarterly proxies. The internal version uses the real measurement -- daily, correctly-signed, desk-level. That gap is the product's moat."

- [ ] **Step 2: Verify in browser**

Navigate to slide 4. Confirm both columns render, edge comparison items have correct icons (x vs. checkmark), two-tier boxes are visually distinct, key line appears at bottom.

- [ ] **Step 3: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: add slide 4 -- why only GS"
```

---

### Task 5: Add slide 5 -- Plan & Rigor

**Files:**
- Modify: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Add slide 5 HTML**

Two-column layout. Left: timeline table using v1's `.timeline-table` class with 6 rows (Weeks 1-2, 3-5, 6-12, 13 checkpoint, 14-17, 18-20). Week 13 row uses `.checkpoint` class for blue highlight. Right: rigor table with 5 rows (Data snooping, Overfitting, Lookahead bias, "Can you trade it?", Unstable features). Below both columns: bottom strip with two sections. Note: v1 slide 11 had a two-box `.ask-grid` ("What I need from you" + "What you get back"). v2 removes the "What I need" box entirely. Use a single `.ask-box` for "What you get" content, then the `.wont-be` grid for "What this won't be" items.

Content per spec slide 5:
- Headline: "20-week plan. Hard checkpoint at Week 13. Validation built before any signals are tested."
- Left: 6-row timeline table
- Right: 5-row rigor table
- Bottom "What you get": Week 13 memo + Week 20 report/index spec
- Bottom "What this won't be": 3 items (not black box, not fishing expedition, not overfit backtest)

- [ ] **Step 2: Verify in browser**

Navigate to slide 5. Confirm both tables render, checkpoint row is highlighted in blue, bottom strip is visible without scrolling.

- [ ] **Step 3: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: add slide 5 -- plan and rigor"
```

---

### Task 6: Add backup slides and navigation JS

**Files:**
- Modify: `deliverables/pitch_presentation_v2.html`

- [ ] **Step 1: Add 3 backup slides**

Copy backup slides (slides 12-14) from v1 unchanged. These become slides 6-8 in v2. Update their `id` attributes to `slide6`, `slide7`, `slide8`. Keep the `<div class="backup-marker">Backup Slide</div>` on each. Update the slide-number text to "Backup 1", "Backup 2", "Backup 3" (same as v1).

- [ ] **Step 2: Add navigation script**

Copy the `<script>` block from v1. Update the constants:

```javascript
let current = 1;
const total = 8;
const mainSlides = 5;
```

Also copy the `.nav-hint` element: `<div class="nav-hint">Arrow keys or click to navigate</div>`

- [ ] **Step 3: Verify full navigation in browser**

Open the file. Navigate through all 8 slides using arrow keys. Confirm:
- Slides 1-5 show "N / 5" numbering
- Slides 6-8 show "Backup N" and have the backup marker
- All content renders without overflow on each slide
- Keyboard navigation (left/right arrows, Home, End) works
- Click navigation works

- [ ] **Step 4: Commit**

```bash
git add deliverables/pitch_presentation_v2.html
git commit -m "feat: add backup slides and navigation"
```

---

## Chunk 2: Speaker Script

### Task 7: Write speaker script v2

**Files:**
- Reference: `deliverables/speaker_script.md` (v1 baseline for style)
- Create: `deliverables/speaker_script_v2.md`

- [ ] **Step 1: Write the full script**

Follow the v1 script format: slide-by-slide sections with timing, spoken text in quotes, delivery cues in bold brackets, advance cues between sections. Target ~15-17 minutes total.

Structure:

**Slide 1 -- Title [~20 seconds]**
- Opening line. Frame as product pitch. Acknowledge the audience's time.

**Slide 2 -- The Product [~4-5 minutes]**
- Open with "here's what I'm building" framing
- Walk through what the index does (left column)
- Explain dual value: product for clients + risk management for the desk
- Trace the pipeline strip quickly
- Land the IC key line
- Transition: "So why should this work?"

**Slide 3 -- Why It Works [~4-5 minutes]**
- Let the stat cards land before speaking
- Walk through 77%, 6 asset classes, Daily -- same verbal structure as v1 slide 3
- Walk through the feature table -- spend time on VaR utilization and factor concentration (the two priorities)
- Land the key line: "These aren't proxies."
- Transition per spec: "These signals should exist in any dealer's risk system. But testing them requires the right data -- and there's a massive gap between what's publicly available and what SecDB produces."

**Slide 4 -- Why Only GS [~3-4 minutes]**
- Gesture to left column: what external researchers use (don't read every bullet)
- Gesture to right column: what SecDB provides
- Explain the two-tier product structure: public index is the product, internal version is GS's edge
- Mention data access naturally: "And with access to VaR data, the internal version gets even stronger"
- Land the key line about the moat
- Transition: "Here's how I execute this."

**Slide 5 -- Plan & Rigor [~3-4 minutes]**
- Walk through timeline quickly -- emphasize Week 13 checkpoint
- Walk through rigor table -- keep it crisp, don't explain details unless asked
- Land on deliverables: what you get at Week 13 and Week 20
- End on "what this won't be" -- three items
- Stop. Let the conversation begin naturally.

**General delivery notes** (same section as v1):
- Pace, eye contact, handling interruptions, handling pushback
- Tonal shift: use "this index" and "this product" language throughout, not "this project" or "this research"
- Have the battle card open in a separate window

- [ ] **Step 2: Review script timing**

Read through the script out loud (mentally). Confirm each slide's content fits within its allocated time. Adjust if any section runs long.

- [ ] **Step 3: Commit**

```bash
git add deliverables/speaker_script_v2.md
git commit -m "feat: add speaker script v2 for 5-slide pitch"
```

---

## Chunk 3: Q&A Battle Card Updates

### Task 8: Add new sections to battle card

**Files:**
- Modify: `deliverables/qa_battle_card.md`

- [ ] **Step 1: Add three new sections**

Append three new sections to the end of the existing battle card (before any closing content). All existing content stays unchanged. New sections:

**Section 12: Index product questions** (6 questions with answers)
- "Why would a client pay for this when they can replicate the public version?"
- "What's the capacity of this index?"
- "How is this different from existing GS research indices?"
- "Who maintains the index after the internship?"
- "What if the public version performs as well as the internal version? Where's the edge?"
- "What instruments does the index trade? Are they all liquid enough?"

**Section 13: Two-tier structure questions** (3 questions with answers)
- "Isn't publishing the methodology giving away the signal?"
- "What stops a client from just building this themselves?"
- "How do you price the index product?"

**Section 14: Replicability questions** (3 questions with answers)
- "Which public proxies map to which SecDB features?"
- "How much signal degradation do you expect from public vs. proprietary data?"
- "What if the signal only works on proprietary data and not on public proxies?"

Answer content for all 12 questions is specified in the design spec under "Q&A Battle Card Updates." Use the same verbal-delivery style as the existing battle card answers (direct, concise, no hedging).

- [ ] **Step 2: Verify formatting**

Read through the modified file. Confirm:
- All 11 existing sections are unchanged
- New sections follow the same markdown heading structure (## for section, ### for each question)
- Answer format matches v1 style (paragraph form, conversational tone)
- No em dashes (use -- instead)

- [ ] **Step 3: Commit**

```bash
git add deliverables/qa_battle_card.md
git commit -m "feat: add index product, two-tier, and replicability Q&A sections"
```

---

## Chunk 4: Final Review

### Task 9: Cross-check all deliverables against spec

**Files:**
- Read: `docs/superpowers/specs/2026-04-30-pitch-presentation-v2-design.md`
- Read: `deliverables/pitch_presentation_v2.html`
- Read: `deliverables/speaker_script_v2.md`
- Read: `deliverables/qa_battle_card.md`

- [ ] **Step 1: Verify slide deck content matches spec**

Open the HTML file in a browser and check each slide against the spec:
- Slide 1: title, subtitle, name, desk, date
- Slide 2: headline, two columns (what it does / dual value), pipeline strip, key line
- Slide 3: headline, three stat cards (77%, 6, Daily), feature table (5 rows), key line
- Slide 4: headline, data edge comparison (left), two-tier structure (right), key line
- Slide 5: headline, timeline table (left), rigor table (right), deliverables strip, "won't be" strip
- Backup 1-3: unchanged from v1

- [ ] **Step 2: Verify no content overflow on any slide**

Navigate through all 8 slides. Confirm that all content fits within the viewport on a standard 1920x1080 display without scrolling. If any slide overflows, reduce font sizes on that slide's elements (prefer reducing table `td` font-size from 18px to 16px, or stat-card padding).

- [ ] **Step 3: Verify speaker script covers all slides**

Read through the script. Confirm each slide has a section with timing, spoken text, and delivery cues. Confirm the total time adds up to ~15-17 minutes. Confirm the transition language between slide 3 and slide 4 matches the spec.

- [ ] **Step 4: Verify battle card has all 12 new questions**

Count the new questions. Confirm all 12 are present with answers. Confirm existing content is unchanged.

- [ ] **Step 5: Final commit if any adjustments were made**

```bash
git add deliverables/
git commit -m "fix: final adjustments from cross-check review"
```
