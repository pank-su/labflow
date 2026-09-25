---
name: labflow
description: Run a reproducible workflow for academic tasks.
version: 0.2.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tasks, labs, coursework, workflow, reproducibility]
    related_skills: [labflow-context, labflow-coding, labflow-math, labflow-report, labflow-self-review]
---

# Labflow

Run a university-agnostic workflow for labs, practical tasks, calculation
works, and course projects. This skill owns phase ordering, artifact contracts,
blocking questions, and completion gates; specialist skills own their domains.
It does not prescribe a university, language, report format, or project template.

## When to Use

- A user provides a methodology, task, course-project brief, or dataset.
- A task needs a traceable path from requirements to code, calculations, and report.
- Existing specialist skills should be reused when available.

Do not use it for a one-line calculation or an isolated code fix with no task context.

## Prerequisites

- The task source and all available input files are present in the workspace.
- The workspace is writable.
- If a required input is missing, record it in `context/open_questions.md` instead of guessing.

## Phase Selection

First distinguish a full academic deliverable from a bounded revision to an existing
artifact. For a bounded text, heading, or slide correction, read the current source
and applicable contract, execute only the affected phase, and verify the rebuilt
artifact plus dependent contents/pagination. Do not rebuild unrelated code or launch
whole-project reviews solely for a cosmetic edit. State that the revision is verified,
not that the full project is independently approved. Any changed candidate invalidates
prior full publication approval; fresh required reviews remain mandatory before
commit/push. A full deliverable follows all phases below. GUAP-specific source/style
rules are in the separate `labflow-guap` adapter; keep this skill university-agnostic.

1. Run `labflow-context` first for a new full deliverable; reuse and update current context for a bounded revision.
2. Run `labflow-coding` when the context requires software or simulations.
3. Run `labflow-math` when formulas, numerical methods, statistics, or data analysis are required.
4. Run `labflow-report` when a report is requested or required.
5. For a full deliverable or publication candidate, launch a fresh subagent with `labflow-self-review` before claiming independent completion. For a bounded local revision, verify the changed artifact and all affected pages/dependencies; do not launch whole-project review unless the change affects correctness or publication is requested. A missing independent-review capability leaves full approval blocked, but does not prevent delivery of a clearly labeled locally verified revision.

Use matching external skills for PDF extraction, a programming language, testing,
Jupyter, Typst, LaTeX, DOCX, or PDF when they are available. Treat them as
capabilities, not hard dependencies. If one is unavailable, use the fallback
procedure and record the limitation.

## Procedure

### 1. Establish the workspace

For automated or batch runs, do a cheap source/deduplication preflight before domain work: distinguish no new input, inaccessible input, and unprocessed changed input. An access failure is not a no-change result. Load specialist skills only for applicable phases. A discovered source is not processed until its required artifacts are built and verified. For batches, record each requested item and its own result; one successful item cannot mark the batch complete. Scheduling, authentication and submission policy belong to the caller/adapter, not this core.

Inspect the available files and create only neutral directories: `context/`,
`src/`, `tests/`, `math/`, `artifacts/`, `report/`, and `evidence/` as needed.
Completion criterion: every input file has a known path and no source file was modified.

### 2. Build the context

Run `labflow-context`. It must produce `context/TASK.md`,
`context/context.yaml`, and `context/open_questions.md`.
Completion criterion: requirements, constraints, inputs, outputs, and unresolved questions are explicit.

### 3. Resolve blockers

Ask the user only for information that blocks a correct result: missing variant,
missing dataset, ambiguous output requirement, or inaccessible source.
Completion criterion: every blocking question is answered or explicitly accepted as a blocker.

### 4. Produce domain artifacts

Run coding and/or mathematics specialists. Keep code, calculations, logs, figures,
and tables outside the report source.
Completion criterion: every required domain result has a reproducible command or notebook and a saved output.

### 5. Assemble the report

Run `labflow-report`. Choose the requested format through an adapter; do not
assume Typst, GOST, a title page, or a fixed directory layout.
Completion criterion: the report references only existing artifacts and contains no invented results.

### 6. Run the self-review

Use `delegate_task` to launch a fresh subagent with the `labflow-self-review`
skill. Give it the exact workspace path and require four independent review
dimensions: requirement coverage, code quality and behavior, mathematics and
artifacts, and visual report appearance. The subagent must write `SELF_REVIEW.md`
in that workspace.

After delegation, the parent agent must validate the review artifact with
`<skill-root>/scripts/check_self_review.py <workspace>/SELF_REVIEW.md --require-passed`,
resolving `<skill-root>` from `labflow-self-review` rather than assuming a checkout.
Read the linked evidence and compare the candidate fingerprint separately: the
checker validates structure and explicit statuses, not the truth of the review. Reject a missing,
malformed, or misplaced file. If the status is `changes_requested`, fix every
finding in the responsible phase and launch a new fresh review subagent. If the
status is `blocked`, resolve the missing input or tool, ask the user when needed,
or keep the task blocked. Never claim completion while it remains blocked.

Generated PDFs, rendered images, test outputs, notebook caches, and logs may be
written under a temporary directory or `artifacts/self-review/`. The subagent
must not rewrite tracked source files, source data, notebooks, or report sources
while reviewing them.

Completion criterion: the parent validates `SELF_REVIEW.md` and it contains the
required sections, executed checks, visual evidence, requirement coverage, and
the literal line `Final Status: passed`.

## Rules

- Do not invent missing values, variants, execution results, or citations.
- Prefer the task source and user-provided data over general knowledge.
- Keep planning, implementation, mathematics, writing, and self-review separate.
- Preserve raw outputs so important claims can be checked.
- Do not call a task complete without real execution and self-review output.
- Never overwrite user files without an explicit reason and a recoverable copy.
- If a specialist skill has stronger domain rules, follow those rules inside its phase.

## Failure Recovery

If a phase fails, preserve its logs, state the failing phase, and retry only after
identifying the cause. Do not silently skip a failed compile, test, or calculation.

Before review, freeze and fingerprint candidate inputs, including untracked source
and generated deliverables; exclude review-owned outputs to avoid a circular hash.
Give reviewers the authoritative template source, requirement contract and explicit
exceptions. A previous Git revision is not automatically the user's template baseline.
Keep separate states for build verified, review passed, locally delivered and published.
Interrupted, missing or stale verdicts never count as passed. Preserve superseded
reviews with their candidate identity rather than overwriting historical evidence.

Only functional defects require failing regression tests. Editorial findings require
source corrections, compilation and visual verification, not fabricated tests. After
one fix/review cycle, classify new findings as blockers versus optional suggestions.
If reviews continue to expand scope, report the exact remaining blocker and seek a
bounded decision rather than launching an unbounded loop. Never waive a real blocker
merely to finish. Give short progress updates during long runs. Honor stop requests;
a late asynchronous result does not authorize resuming stopped work.

## Completion

A full deliverable is complete only when:

- `context/TASK.md` exists;
- All required code and mathematics artifacts exist;
- Required commands or notebooks were executed;
- The report format was compiled or rendered when applicable;
- `SELF_REVIEW.md` has final status `passed` and no unresolved blocking finding.
