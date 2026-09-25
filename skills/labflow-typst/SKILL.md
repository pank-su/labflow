---
name: labflow-typst
description: Generate a complete context-driven Typst report structure.
version: 0.3.0
author: Vasilii Pankov (pank-su), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [typst, reports, gost, tasks, templates]
    related_skills: [labflow-context, labflow-report, labflow-self-review]
---

# Typst Report

Optional report adapter for labflow. It uses one shared Typst structure derived
from a course project and a mathematical foundations lab. The initializer reads
the task context and creates the complete project skeleton; the agent does
not invent title-page metadata, directories, or section names.

## When to Use

- The task requests a Typst report.
- A project needs a repeatable GOST-style baseline without a university-specific template.

Do not use it when an institutional template is explicitly required and must be preserved.
For GUAP, use `labflow-guap` and its protected generator instead. Never run this
initializer or `--force` over a protected GUAP project: the body is editable only in
`index.typ`, while title metadata is changed only by that generator's `title` command.

## Prerequisites

- `context/context.yaml` created by `labflow-context`.
- Python 3.10+ for the initializer script. YAML input additionally needs PyYAML; JSON input uses only the standard library. Check the actual interpreter, not a remembered system version. A reproducible invocation is `terminal(command="uv run --python 3.11 --with pyyaml python <skill-root>/scripts/init_typst.py --context context/context.yaml --output-dir .")` when uv is installed.
- Typst CLI for compilation; initialization itself does not require Typst.

## How to Run

Run the initializer from the project root through the `terminal` tool:

The checkout command below uses the repository path. After installation, resolve
the directory containing this `SKILL.md` as `<skill-root>` and run
`scripts/init_typst.py` from that skill directory.

```bash
python skills/labflow-typst/scripts/init_typst.py \
  --context context/context.yaml \
  --output-dir .
```

Compile the generated report:

```bash
typst compile docs/index.typ docs/report.pdf
```

Use `--force` only when the generated files may be replaced intentionally and a recoverable copy exists. It overwrites generated content and is not a migration command. The initializer refuses a target inside a project marked `.labflow-protected` or `.guap`, including nested targets, even with `--force`. Other institutional templates must be recognized during context selection; marker detection is not a universal sandbox.

## Generated Structure

```text
docs/
├── index.typ
├── content.typ
└── lib/
    ├── context.typ
    ├── gost.typ
    └── titlepage.typ

artifacts/
data/
images/
math/
src/
tests/
```

## Procedure

1. Run `labflow-context` and resolve blocking questions first.
2. Run `init_typst.py --context context/context.yaml --output-dir .`.
3. Fill `docs/content.typ` from `context/TASK.md`, code, mathematics, and real artifacts.
4. Keep `docs/lib/context.typ`, `gost.typ`, and `titlepage.typ` as generated infrastructure unless the adapter itself must be extended.
5. Compile the report with Typst.
6. Pass the complete project to `labflow-self-review` for code, requirements, mathematics, and visual review.

Completion criterion: the script creates every listed directory and file from the
context, and the generated report compiles after its explicit placeholders are filled.

## Rules

- The context is the only source for title-page metadata.
- Missing metadata remains empty; it is never replaced with GUAP, a group, a teacher, a city, or a date by default.
- Section names come from `deliverables.report_sections` when provided; otherwise the script uses only the shared lab/coursework outline.
- Do not place university-specific behavior in the core template.
- Do not claim a PDF exists unless Typst compilation succeeded.
