---
created: 2026-04-10
updated: 2026-04-14
tags: [ref, secdb, graph, computation, invalidation, node, lifecycle, onoffgraph]
status: dormant
relates:
  - ref/secdb-ufo-diddles.md
  - slang/best-practices.md
  - slang/lint-edit.md
  - slang/run.md
---

# SecDB Graph — Core Concepts

Reference from SecDb Topics Part II (2015, Walker & Madsen), workspace builtins docs, and the official **EngHub Graph framework docs** (`secdb/secdb-docs/secdb-platform-docs`, Jan 2025). Contact: gs-secdb-graph-team@gs.com.

---

## The Computation Graph

SecDB models everything as a **directed acyclic computation graph** (DAG):
- **Nodes** = atomic units of computation (identified by VT + security + args + database)
- **Edges** = dependencies between nodes
- Arrows point in dependency direction (child → parent)
- Must be directed, acyclic, with values at terminals

### Three Key Principles

1. **Invalidation** — bottom up. When a node's value changes, all parents are marked invalid (recursively). Invalidation is cheap — runs no functions.
2. **Calculation** — top down (lazy/"backward chaining"). Values are only calculated when requested via GetValue. Post-order traversal: calculate children first, then run node function.
3. **Purity** — node functions must be pure and side-effect free. Given same inputs, same output.

---

## Node Types

| Type | Description |
|------|-------------|
| **Calc** | Has a function that calculates its value from children |
| **Retain** | Has a value that can be set (overridden) |
| **InStream** | Will be persisted to the database |
| **Stored** (InStream + Retain) | Can be set AND persisted — key terminal node type |
| **Calc + Retain** | Has a function but can be overridden with a set |

### Extended Node Classification (EngHub)

| Category | Description |
|----------|-------------|
| **Terminal** | Results from computation or set/diddle (distinct from "leaf") |
| **Non-Terminal** | Array expansion, pass-through |
| **Literal** | Simply holds values |

### Node Identity

A node is uniquely identified by: **Security + Value Type (VT) + Arguments + Db Set**

### Node Attributes

- **Value** (if valid)
- **State**: Status (Valid/Invalid/Doubtful), Topology status, Child List status, Flags, Error
- **Children** and **Parents**

### Db Set

- **Physical databases**: e.g. `!NYC_Production;!NYC_BaseRef`
- **Virtual databases** (Diddlescopes): numerical IDs, e.g. `!1;!NYC_Production;!NYC_BaseRef`
- Union notation: `a;b;c` is subordinate to `b;c` which is subordinate to `c`

---

## Classes and Objects (Securities)

- **Class** = defines how a graph is laid out (like a template/schema)
- **Object/Security** = instance of a class — a grouping label for a bundle of nodes
- A security is more like an **Excel worksheet** than a C++ object
- Unlike Excel: code (formula) is separate from instance (terminal values)
- `NewSecurity( "ClassName" )` creates in-memory instance; `GetSecurity( "SecName" )` loads from DB.

## Memoization

- Every computed value is cached ("memoized") in the graph.
- If a value is needed by two parents, it's computed once and shared.

## OnGraph vs OffGraph

**OnGraph** = accessing values through the graph's dependency mechanism (`Price( Self )`). Dependencies tracked; invalidation propagates correctly.

**OffGraph** = accessing values outside the graph. No dependency tracking → **inconsistent state**.

| Pattern | Why OffGraph | OnGraph Fix |
|---------|-------------|-------------|
| `GetValue( "A", Self )` | Not parsed by UFO; no dependency built | `A( Self )` |
| `@Library::Func( Self )` | Only the VT is parsed, not closure | `@Library::OtherFunc( VT( Self ) )` |
| `Today()` | Value changes without graph knowing | `Pricing Date( "Security Database" )` |
| `Private::Variable` | Set elsewhere, no invalidation | Set onto a graph node |
| Cache in `_LIB` or addin | No invalidation semantics | Consult canonical FAQ |
| `Random()` | Not a pure function | Make graph deterministic |

## UFO Parser

1. Takes Slang code → finds VT access patterns (`A( Self )`, `B( Self )`)
2. Replaces them with offsets into a **child list**
3. Establishes the child list (dependencies)
4. Result: function on an array (`ChildData[0]`, `ChildData[1]`, etc.)

---

## Graph Lifecycle: Build, Calculate, Invalidate

### Build (lazy)
When you get a value from a node that doesn't exist:
1. Allocate node, build child list from UFO definition
2. Mark invalid
3. Calculate

### Calculate (top-down, lazy)
- If valid: return memoized value
- If invalid: get values from all children (recursively), run function, memoize, return
- If doesn't exist: build, then calculate

### Invalidate (bottom-up, immediate)
- Visit each valid parent
- If parent is valid and not explicitly set/diddled: mark invalid
- Recurse up
- **Invalidation runs NO functions** — it's cheap
- `InvalidateValue` addin for explicit invalidation.

## Dependencies

### Static vs Dynamic

- **Static**: determined from source code analysis (UFO parser scanning VT access)
- **Dynamic**: determined by graph state at build time (e.g., which branch of an If is taken)

### Child List Size

- Normally **fixed** at parse time (for efficiency)
- Exception: **Each** nodes have dynamic child lists

## Each — Dynamic Iteration on Graph

```slang
x = Sum( B( Self, Each( D( Self ) ) ) );
```
- Creates a node for **each element** of the array
- Special "Each" node depends on all created nodes. Result is a vector.

## Edge Dependencies (Purple Children)

Nodes have two kinds of children:
1. **Regular** — value dependencies
2. **Edge** (formerly "purple") — nodes that affect the **identity** of other children

When an edge child changes, the parent's **child list** becomes invalid (not just its value). Edge dependencies are evaluated first.

**Two sources:**

1. **Predication** — `If` blocks. The condition node is an edge dependency.
2. **Arguments** — `B( Self, E( Self ) )` → `E( Self )` determines the identity of the B node.

---

## Key SecDB APIs

| API | Description |
|-----|-------------|
| `GetSecurity` / `NewSecurity` | Load from DB or create object of given class |
| `GetValue` | Get value of a node, building graph as needed |
| `DefineClass` / `DefineClassNonStreamable` / `DefineInterface` | Define a SecDB class |
| `DeclareClassWithSeq` | Register class in `_LIB Class Declarations` |
| `UpdateSecurity` / `RenameSecurity` / `DeleteSecurity` | Persist, rename, or delete from DB |
| `SetValue` | Permanently set a node's value |
| `SetDiddle` / `WhiteOutDiddle` | Temporarily override / restore true value |
| `Restore` / `RestoreDiddle` | Remove diddles (alias) |
| `DiddleScopeDefine` / `DiddleScopeUse` | Create / activate persistent diddle scope |
| `ForChildren` | Traverse built graph and enumerate dependencies |
| `InvalidateValue` / `InvalidateValueIfNotDiddled` | Clear a Set-Retained value |
| `SecDbGraphClearFailures` | Clear cached failures on a node and descendants |
| `SecDbBuildChildren` / `SecDbBuildFullGraph` | Build child list or full graph |
| `VTApply` / `Value Reference` | Construct graph expressions programmatically |
| `CheckE` / `CheckN` / `Check` | Throw on error / null / error+null+false+0 |

> **See also:** [ref/secdb-ufo-diddles.md](secdb-ufo-diddles.md) — UFO class system, diddles & scopes, value methods, debugging.

---

## Quick Reference: Graph Rules

1. Invalidation goes **up** (child → parents). Calculation goes **down** (parent → children).
2. Invalidation is **cheap** (no functions run). Calculation is **expensive** (runs functions).
3. Graph builds **lazily** — only when a value is requested.
4. Node functions must be **pure** — no side effects, deterministic.
5. **Everything is memoized** — computed once, cached.
6. Child list size is **fixed** (exception: Each nodes).
7. **Edge dependencies** cause child list invalidation, not just value invalidation.
8. **Diddles are scoped** — Eval (temporary), DiddleScope (persistent), Global.
9. **OffGraph** access breaks the graph — avoid `GetValue`, `Today()`, `Private::Variable` in VTs.
10. Use `ForChildren` to traverse and `TraceOn` / UFO breakpoints to debug.
11. `@Stored` VT order matters — used for serialization/deserialization of security BLOBs.
12. Graph Privacy must be explicitly opted-in per class; VTs default to private+non-diddleable when on.
13. **Predicate expressions must be pure** or dynamic topology is silently lost.
14. **Do not inline `Each` over security names** in VT code — creates synthetic `~Cast` with bad lifetime.
15. **Omitted default args ≠ explicitly passed defaults** — different graph nodes.
16. **Phantom diddles are deprecated** — use side-effect diddles.
17. **Do not mutate main-graph nodes during on-graph evaluation** — can leave valid parents on invalid children.
