---
name: expand-learning-graph
description: "Add new concepts, merge checklists, or add entire layers to the vol-learning dependency graph. USE FOR: merging checklist files into graph nodes, adding individual concepts, adding new feature layers, graph validation and deduplication. DO NOT USE FOR: quizzing (use quiz), teaching (use learn), checking progress (use learning-status)."
---

# /expand-learning-graph — Graph Expansion and Validation

> **Purpose:** Expand the dependency graph with new concepts, merge external checklists, or add entire feature layers. All expansion work is done by a subagent with robust deduplication. NEVER writes to `workspace/learning/graph.yaml` without user approval.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph (nodes, edges, key_points, misconceptions) | Read + Write (only after user approval) |
| `workspace/learning/mastery-state.json` | Per-node mastery state (new nodes get "untested" entries) | Write (after graph update) |

## Three Modes

### Mode 1: Merge — `/expand-learning-graph merge <file-path>`

Merge an external checklist or concept list into the existing graph.

1. Read the checklist file at the given path
2. For each item: fuzzy-match against existing nodes (see deduplication below)
3. If match found: merge new points into existing node's `key_points` or `misconceptions`
4. If no match: create a new node, propose `requires` edges based on content
5. Present ALL proposed changes for user approval before committing

### Mode 2: Add — `/expand-learning-graph add "<concept description>"`

Add a single concept to the graph.

1. Parse the description to create a node following the schema
2. Propose `requires` and `connects_to` edges based on content similarity
3. Ask user to confirm edges and placement
4. Only write after confirmation

### Mode 3: Layer — `/expand-learning-graph layer <N>`

Add an entire feature layer to the graph.

1. Read relevant chapters from the vol-learning-guide markdown (if available locally)
2. If guide not available, use `key_points` from the design spec or ask user for source material
3. Propose nodes for the layer (do NOT auto-create)
4. Run coverage check (see below)
5. User approves/edits, then nodes are added

## Subagent: Expansion and Validation

ALL expansion work is done by an **Opus 4.6** subagent:

```
Prompt: You are a learning framework data agent. Read workspace/learning/graph.yaml.
Also read [input file if merge mode].

Perform the requested expansion:
- Mode: [merge | add | layer]
- Input: [file path | concept description | layer number]

For each proposed node or modification, run the full deduplication and validation
checks (see below). Return:
{
  "proposed_additions": [...],    // new nodes with full schema
  "proposed_merges": [...],       // existing nodes with merged key_points/misconceptions
  "proposed_edges": [...],        // new requires/connects_to relationships
  "duplicates_found": [...],      // near-duplicates flagged for user decision
  "validation_warnings": [...],   // structural issues found
  "coverage_gaps": [...]          // uncovered sections (layer mode only)
}

Do NOT write to graph.yaml. Return proposed changes only.
```

## Deduplication and Validation (Robust)

On every expansion, the subagent runs these 5 checks:

1. **Exact ID check:** reject if `id` already exists in the graph

2. **Semantic similarity check:** for each proposed node, compare its `name` + `key_points` against ALL existing nodes. Flag if:
   - Two nodes share 60%+ of the same `key_points`
   - Two node names describe the same concept with different wording (e.g., "why we use log returns" vs "log returns vs simple returns")
   - A proposed node's content is a strict subset of an existing node (the existing node already covers it)

3. **Merge-or-split decision:** when a near-duplicate is found, present three options:
   - **Merge:** fold the new content into the existing node's `key_points`/`misconceptions`
   - **Split:** if the existing node is too broad, split it into two focused nodes and redistribute edges
   - **Keep both:** if they're genuinely distinct despite surface similarity (user confirms)

4. **Structural validation:**
   - No orphan nodes (every non-root node has at least one `requires`)
   - No circular dependencies
   - All `requires` and `connects_to` targets exist in the graph
   - No node has more than 5 `requires` edges (if it does, it probably needs intermediate nodes)

5. **Coverage check (layer mode):** after adding a layer, verify that every section heading in the relevant guide chapter maps to at least one node. Flag uncovered sections.

## User Approval Gate

**NEVER write to `workspace/learning/graph.yaml` without user approval.**

After the subagent returns proposed changes, present them to the user:
- Show new nodes (name, layer, requires, key_points summary)
- Show merges (what's being added to existing nodes)
- Show any duplicate flags requiring decision
- Show validation warnings
- Ask: "Approve all / Approve with edits / Reject?"

Only after explicit approval, dispatch a second Opus 4.6 subagent to:
1. Write approved changes to `workspace/learning/graph.yaml`
2. Add "untested" entries to `workspace/learning/mastery-state.json` for new nodes

## Session Flow

1. Parse invocation mode and arguments
2. Dispatch Opus 4.6 subagent for expansion + validation
3. Present proposed changes to user
4. Wait for user approval
5. If approved: dispatch subagent to write changes
6. Confirm: "Added [N] nodes, merged [M] existing nodes, created [E] edges."
