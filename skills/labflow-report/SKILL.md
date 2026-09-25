---
name: labflow-report
description: Compose a report from verified task artifacts.
version: 0.2.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tasks, reports, documentation, evidence]
    related_skills: [labflow, labflow-context, labflow-coding, labflow-math, labflow-self-review]
---

# Labflow Report

Compose the requested report from the task context and verified artifacts.
The skill is format-neutral: use a report adapter or an optional formatter skill
for Typst, LaTeX, DOCX, Markdown, or PDF.

## When to Use

- A lab, practical, calculation work, or course project requires a written report.

## Procedure

1. Read `context/TASK.md`, `context/context.yaml`, and the requirements checklist.
2. Read code and mathematical result summaries, not just filenames.
3. Select the requested report format; if none is specified, use Markdown.
4. Build a requirement-to-evidence matrix before drafting.
5. Write the report in the required section order.
6. Include formulas, code excerpts, tables, and figures only from real artifacts.
7. Keep source-quality notes, unresolved questions, and execution limitations in `context/` or `evidence/`. Put a limitation in the submitted report only when it materially changes the interpretation of a result or the task explicitly requires it; an unresolved correctness blocker prevents final delivery rather than being hidden.
8. Save the source at the path selected by the project or report adapter (`report/` only as a neutral default), and compile/render it when the format supports compilation.

## Rules

- The report describes completed work; it must not become a second solver.
- Never invent outputs, screenshots, citations, or passed checks.
- Keep raw source code and raw data outside the report unless explicitly requested.
- Do not assume a title-page format, university, GOST, or fixed Typst template.
- Preserve the provenance of every important numerical claim in the evidence matrix. Keep debugging notes, source-file inventories, QA status, and agent workflow out of submitted prose unless requested; retain required academic citations and material limitations.
- Use typography from the current artifact contract. Do not transfer a font-size exception from one task type to unrelated reports.
- Conclusions answer the task with the actual computed or observed result; they are not a list of actions the agent performed.
- Every required table and figure has a caption, label, and explicit reference in prose. When complete source listings are required, include the exact current source automatically; excerpts do not satisfy that requirement.

## Output Contract

```text
report/<report-source>          # format chosen by the project
report/requirements-matrix.md
```

A compiled artifact such as `report/report.pdf` is required only when the
task explicitly requests it or the selected adapter supports it.

## Self-Review Handoff

Check that every required section exists, every referenced file exists, and each
important result points to a saved artifact or execution log. Hand off to
`labflow-self-review` instead of declaring success yourself.
