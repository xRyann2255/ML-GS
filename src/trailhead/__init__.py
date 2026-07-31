"""Trailhead — repo walkthrough generator.

Five stages plus a command runner, and only stage 3 touches a model:

    1 survey   deterministic  file tree, import edges, entry points, git churn
    2 map      deterministic  collapse to modules, lay out the graph
      runner   deterministic  real subprocess execution, real exit codes
    3 narrate  MODEL          prose as claims carrying verbatim quotes
    4 verify   deterministic  resolve quotes to lines, hash, delete what fails
    5 render   deterministic  verified.json -> one self-contained HTML file

Everything that CHECKS anything is ordinary Python. A model cannot verify
itself, so nothing under stages 1, 2, 4, 5 or the runner may reach a provider.

`textio` sits underneath all of them: one reader, one path key, one sha256
recipe. Import it, never re-implement it.

The generator's output contract is docs/verified-contract.md.
"""

#: Stamped into `report.tool_version` by verify.assemble and read by the page's
#: shell() — decision #27. Bump it when the emitted payload changes shape, not
#: when the prose changes.
TOOL_VERSION = "0.4.0"

#: Kept in lockstep with TOOL_VERSION so the two can never disagree about which
#: build produced a bundle.
__version__ = TOOL_VERSION
