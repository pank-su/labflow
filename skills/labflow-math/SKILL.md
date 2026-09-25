---
name: labflow-math
description: Solve and document reproducible mathematical work.
version: 0.2.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tasks, mathematics, numerical-methods, data-analysis]
    related_skills: [labflow, labflow-context, labflow-self-review]
---

# Labflow Mathematics

Perform the mathematical, numerical, statistical, or data-analysis portion of an
task in a reproducible way. Use Jupyter, Python, symbolic algebra, and
plotting skills when useful, but do not require one fixed library or notebook format.

## When to Use

- The context requires formulas, derivations, numerical methods, statistics, tables, or plots.

## Procedure

1. Read the context and identify the exact mathematical objectives.
2. Restate variables, units, assumptions, and input values before calculating.
3. Select a reproducible notebook or script and record dependencies.
4. Implement the calculation with intermediate values visible.
5. Check dimensions, domains, convergence, tolerances, and edge cases where relevant.
6. Save tables as data files and figures as image files under `math/`.
7. Write `math/MATH_RESULTS.md` with formulas, method, results, and limitations.

## Rules

- Do not hide calculations inside a final number.
- Do not round intermediate values unless the source requires it.
- Label estimated, simulated, and exact values distinctly.
- Preserve the task's notation, units, and requested output representation; define necessary changes. Record whether a dimensionless result is a fraction or a percentage instead of choosing silently.
- Separate internal precision from displayed rounding. Generate the table and prose numbers from the same saved calculation output, not independent manual copies.
- For a calculation report, show one numerical substitution for each distinct formula or stage type unless the task asks for answers only. Do not repeat every table row or substitute a redundant end-to-end check for worked examples.
- Never fabricate a graph, table, or numerical result.

## Output Contract

```text
math/solution.ipynb or math/solve.py
math/formulas.md
math/MATH_RESULTS.md
math/results.csv       # when tabular results exist
math/figures/          # when figures are required
```

## Self-Review Handoff

Run the notebook or script from a clean environment. Compare key values against
an independent check, limiting case, or hand calculation when one is available.
