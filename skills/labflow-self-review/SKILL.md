---
name: labflow-self-review
description: Review code, report appearance, and requirement coverage.
version: 0.2.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tasks, self-review, code-quality, visual-review, requirements]
    related_skills: [labflow, labflow-context, labflow-coding, labflow-math, labflow-report]
---

# Labflow Self-Review

Review an academic candidate against its source requirements. Produce findings
and a decision, not repairs or an approval inferred from the parent's claims.
This is a review procedure; its Markdown checker validates a limited contract,
not the truth of calculations, command execution, or image inspection.

## When to Use

- Independently review a full academic deliverable or publication candidate.
- Recheck a corrected candidate after substantive findings.
- For a bounded local text/format revision, apply only the affected checks;
  do not restart a whole-project review or imply full approval.

## Review scope and applicability

The parent supplies the workspace, exact source/task and template paths,
`context/artifact-contract.md`, accepted exceptions, changed files, and a
candidate fingerprint covering source inputs and delivered artifacts. Exclude
review-owned outputs from that fingerprint and recompute it before accepting
the result. A Git revision alone omits untracked source and generated PDFs.

For full approval use a fresh subagent through `delegate_task`. The reviewer
must inspect evidence independently. If delegation is unavailable or prohibited,
perform useful local checks but state that independent approval remains blocked.
Do not recursively delegate from a reviewer.

All four dimensions must be addressed, but only applicable work is required:
requirements, code, mathematics/artifacts, visual report appearance. A CSV-only
task does not require inventing a PDF; a prose-only task does not require code.
Write `Not applicable: <source-grounded reason>` in an inapplicable dimension.
A missing required tool or failed check is blocked, not not-applicable.

## Procedure

### 1. Establish scope and requirement coverage

Read the original task, `context/TASK.md`, `context/context.yaml`, the checklist,
and artifact contract. Compare each requirement with implementation, calculation,
report section, and evidence. Record source locators. Do not promote historical
teacher advice or reviewer preferences into new requirements.

Done: every explicit requirement is represented; each omission is a finding or
an explicit accepted scope exception, not silently dropped.

### 2. Review code and execution

Inspect central source files. Run applicable build, tests, formatter and a
representative execution. Check boundaries, failure cases, placeholder or
hardcoded results, error handling, and task/language constraints. Record actual
commands, exit codes and logs. `SKIPPED` never means passed.

Do not rewrite source, data, notebooks, report files, lockfiles or baselines,
including untracked files. Use read-only/check modes; write generated outputs
only to a temporary directory or `artifacts/self-review/`. Run commands that may
mutate inputs in an isolated copy and report that location.

Done: each executed check has actual output, and reviewed inputs are unchanged.

### 3. Review mathematics and artifacts

Rerun calculations where available. Check source values, notation, dimensions,
units, domains, intermediate precision, displayed rounding, tolerances and
independent checks. Compare numbers in prose/tables with saved calculation data.
Verify requested worked examples, not merely the final table. For CSV/data-only
outputs, check encoding, delimiters, dimensions, missing values and cited evidence.

Done: reported claims match real artifacts; unsupported claims are not approved.

### 4. Review the actual delivered report

Inspect the exact compiled candidate, not only a fresh potentially different
rebuild. For a full report, enumerate every page and visually inspect every page
using `vision_analyze` or an available viewer. A contact sheet is an overview,
not proof of readable tables/formulas. Record page number, render path and finding
in Visual Evidence. A rebuild can test reproducibility but does not replace
inspection of the delivered bytes.

For a bounded revision, inspect changed pages and every page affected by reflow,
contents, references or numbering. Describe that limited coverage accurately.

Check clipping, accidental blank pages, typography, page breaks, headings,
metadata, complete listings when required, captions/labels/in-text references,
formula rendering, and result-based conclusions. Use the current artifact
contract, not another task's font-size or template exception. Required visual
inspection without an available viewer/vision tool remains blocked.

Done: enumerated inspected pages match the required review scope.

### 5. Write findings and verdict

Write `SELF_REVIEW.md` at the agreed workspace path with these exact headings:

```markdown
# Self-Review

## Scope

## Requirement Coverage

| ID | Requirement | Evidence | Status | Finding |
|---|---|---|---|---|

## Checks Executed

| Check | Command or tool | Exit status | Evidence | Status |
|---|---|---|---|---|

## Code Review

## Mathematics and Artifacts

## Visual Report Review

## Visual Evidence

## Changes Requested

## Blockers

## Final Status

Final Status: passed
```

This is a structure, not a completed review. Fill every section and both tables
with real evidence. In the final file, do not wrap the contract in fenced code
blocks or HTML comments. Put lengthy command output in linked log files.

Each required finding has a severity (`blocker`, `major`, `minor`), path/location,
violated requirement, and concrete correction. Optional advice goes in an
optional `## Suggestions` section and does not block acceptance by itself.

Use `passed`, `changes_requested`, or `blocked` for requirement/verdict status.
For a passed review, every requirement row must say `passed` with Finding `None.`;
Changes Requested and Blockers must each contain only `None.`. Checks Executed
must contain at least one real check; every row must say `passed` with exit `0`.
For tools that do not expose exit codes, use `not_applicable` in Exit status,
not a fabricated zero. This never permits skipping the check itself. Table cells
must be nonempty, with explicit leading/trailing pipes on every table row;
store commands containing literal pipes in a referenced log
rather than introducing ambiguous Markdown table delimiters.

Use exactly one literal status line, alone under `## Final Status`. For failed
or blocked reviews, preserve findings and actual failed/skipped checks honestly.

## Parent verification and recovery

Resolve `<skill-root>` from the loaded skill location. Through `terminal`, run:

```text
python3 <skill-root>/scripts/check_self_review.py <workspace>/SELF_REVIEW.md --require-passed
```

Without `--require-passed`, the checker provides legacy shape validation only,
useful for reading blocked/changes-requested reviews; it is not an approval gate.
With the flag it rejects empty/ambiguous sections, malformed/missing tables,
nonpassing requirement/check rows and outstanding finding sections. It does not
open linked evidence, recompute the candidate fingerprint, verify claimed command
execution, or judge prose/visual correctness. The parent must do those checks.
Do not claim it is a semantic verifier or security sandbox.

A failed/missing/misplaced/stale review never counts as passed. After fixes,
archive the old verdict with its candidate identity and review the new candidate.
Do not edit a candidate while a reviewer is using it. After a fix/review cycle,
separate real blockers from scope-expanding suggestions; escalate persistent
blockers with bounded choices rather than launching an endless review loop.
Stop requests remain in force when late asynchronous results arrive.

## Verification

Full independent approval requires source-grounded coverage, real applicable
checks, full required visual evidence, unchanged candidate identity, and a
successful `--require-passed` contract check. Local revision verification,
independent approval, delivery, and publication are separate states.
