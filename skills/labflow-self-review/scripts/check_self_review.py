#!/usr/bin/env python3
"""Validate the machine-checkable contract of SELF_REVIEW.md."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = (
    "## Scope",
    "## Requirement Coverage",
    "## Checks Executed",
    "## Code Review",
    "## Mathematics and Artifacts",
    "## Visual Report Review",
    "## Visual Evidence",
    "## Changes Requested",
    "## Blockers",
    "## Final Status",
)
STATUS_RE = re.compile(
    r"^Final Status:\s*(passed|changes_requested|blocked)\s*$", re.MULTILINE
)


def table_rows(section: str, header: list[str]) -> list[list[str]]:
    lines = [
        line.strip() for line in section.splitlines() if line.strip().startswith("|")
    ]
    if any(not line.endswith("|") for line in lines):
        raise ValueError("table rows require explicit leading and trailing pipes")
    cells = [[cell.strip() for cell in line[1:-1].split("|")] for line in lines]
    if len(cells) < 3 or cells[0] != header:
        raise ValueError("missing table header or data rows")
    if len(cells[1]) != len(header) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in cells[1]
    ):
        raise ValueError("malformed table separator")
    rows = cells[2:]
    if any(len(row) != len(header) or not all(row) for row in rows):
        raise ValueError("malformed or empty table cell")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    args = parser.parse_args()

    if not args.review.is_file():
        print(f"ERROR: review file does not exist: {args.review}", file=sys.stderr)
        return 1

    text = args.review.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        print("ERROR: missing headings: " + ", ".join(missing), file=sys.stderr)
        return 1

    statuses = STATUS_RE.findall(text)
    if len(statuses) != 1:
        print(
            "ERROR: expected exactly one literal 'Final Status: ...' line",
            file=sys.stderr,
        )
        return 1

    status = statuses[0]
    if args.require_passed and status != "passed":
        print(f"ERROR: final status is {status}, expected passed", file=sys.stderr)
        return 2

    if args.require_passed:
        if "<!--" in text or re.search(r"^[ \t]*(?:`{3,}|~{3,})", text, re.MULTILINE):
            print(
                "ERROR: approval contract must not contain comments or fenced blocks",
                file=sys.stderr,
            )
            return 1
        headings = list(re.finditer(r"^## [^\n]+$", text, re.MULTILINE))
        names = [match.group() for match in headings]
        if any(names.count(heading) != 1 for heading in REQUIRED_HEADINGS):
            print(
                "ERROR: expected exactly one of each required heading", file=sys.stderr
            )
            return 1
        sections = {
            match.group(): text[
                match.end() : headings[i + 1].start()
                if i + 1 < len(headings)
                else len(text)
            ].strip()
            for i, match in enumerate(headings)
        }
        empty = [heading for heading in REQUIRED_HEADINGS if not sections.get(heading)]
        if empty:
            print("ERROR: empty section: " + ", ".join(empty), file=sys.stderr)
            return 1

        if sections["## Final Status"] != "Final Status: passed":
            print(
                "ERROR: literal status must be the only content of Final Status",
                file=sys.stderr,
            )
            return 1
        try:
            coverage = table_rows(
                sections["## Requirement Coverage"],
                ["ID", "Requirement", "Evidence", "Status", "Finding"],
            )
            if any(
                row[3] != "passed" or row[4] not in ("None", "None.")
                for row in coverage
            ):
                raise ValueError(
                    "requirements must be passed with no unresolved findings"
                )
            for heading in ("## Changes Requested", "## Blockers"):
                if sections[heading] not in ("None", "None."):
                    raise ValueError(
                        f"{heading} must contain only None. for a passed review"
                    )
            checks = table_rows(
                sections["## Checks Executed"],
                ["Check", "Command or tool", "Exit status", "Evidence", "Status"],
            )
            if any(
                row[4] != "passed" or row[2] not in ("0", "not_applicable")
                for row in checks
            ):
                raise ValueError(
                    "every check must be passed with exit 0 (not_applicable only for tools without exit codes)"
                )
        except ValueError as exc:
            print(f"ERROR: checks: {exc}", file=sys.stderr)
            return 1

    print(f"SELF_REVIEW_VALID status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
