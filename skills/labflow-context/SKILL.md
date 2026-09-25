---
name: labflow-context
description: Extract requirements and constraints from an task.
version: 0.2.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tasks, requirements, planning, context]
    related_skills: [labflow, labflow-self-review]
---

# Labflow Context

Convert an task brief, methodology, or course-project specification into a
structured, source-grounded context. This skill discovers what must be done; it
does not implement the solution or write the final report.

## When to Use

- Before coding or mathematical work on a lab, practical, or course project.
- When the task is spread across PDFs, images, source files, and user notes.

## Procedure

1. Inventory every input file and record its path and type.
2. Extract readable text from the methodology; use an OCR skill for scanned pages.
3. Identify the objective, tasks, variant, inputs, constraints, algorithms, and deliverables.
4. Separate explicit requirements from assumptions and unresolved questions.
5. Write `context/TASK.md` in human-readable form.
6. Write `context/context.yaml` with the following stable top-level fields:
   `kind`, `title`, `subject`, `variant`, `objective`, `inputs`, `requirements`,
   `constraints`, `deliverables`, and `open_questions`.
7. Write `context/open_questions.md`; use an empty list when nothing is missing.
8. Create a requirement checklist mapping each requirement to a planned artifact and a review method, with an exact source locator (page, table, task item, or user correction).
9. Record `context/artifact-contract.md`: request scope (full/revision/publication), required deliverable paths and audience, authoritative template, changed pages/dependencies, notation, units, displayed precision, worked-example expectations, and explicit exceptions. Inherit project/adapter paths instead of creating a parallel directory layout.
10. Classify open questions as blocking or nonblocking. Preserve a suspicious source value literally, record its location and possible interpretation internally, and block only when the uncertainty prevents a correct result. Never silently repair it or promote a hypothesis into a requirement.

## Rules

- Never select a variant or input value by guessing.
- Preserve exact formulas, file extensions, and required section names.
- Mark contradictions between sources instead of silently resolving them.
- Do not add university-specific defaults unless the source explicitly provides them.
- Do not modify the methodology or user-provided data.

## Output Contract

```text
context/TASK.md
context/context.yaml
context/open_questions.md
context/requirements-checklist.md
context/artifact-contract.md
```

Completion means each explicit requirement has an identifier and a planned
review method. Unknown values must appear in `open_questions.md`.

The context is the only source for report metadata. It may include optional
metadata such as `author`, `group`, `university`, `faculty`, `department`,
`teacher`, and `city`. Empty or missing values must remain empty; neither the
agent nor a generator may invent them.

Use `templates/artifact-contract.md` as a compact starting point; fill only from actual sources.

## Machine-readable provenance

For runtime-managed work, retain the checklist IDs and populate the Labflow
`source-spec.json` template after the actual target fragments exist. The parent
seals it with `sources-seal`, then checks exact ID coverage before freezing the
candidate. Use real source lines/PDF pages and preserve explicit notation tokens;
missing input is blocked, not a substitute from a similar topic. Hashes do not
prove the semantics of derived text or calculations. See the `labflow` runtime reference.

## Self-Review Handoff

Compare the checklist against the original source. Confirm that every required
input, output, restriction, and report section appears in the generated context.
