from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills/labflow-self-review/scripts/check_self_review.py"
HEADINGS = "\n".join(
    [
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
    ]
)


BODIES = {
    "## Requirement Coverage": "| ID | Requirement | Evidence | Status | Finding |\n|---|---|---|---|---|\n| R1 | Required output | artifacts/run.txt | passed | None |",
    "## Checks Executed": "| Check | Command or tool | Exit status | Evidence | Status |\n|---|---|---|---|---|\n| Run | python solve.py | 0 | artifacts/run.txt | passed |",
    "## Changes Requested": "None.",
    "## Blockers": "None.",
    "## Final Status": "Final Status: passed",
}
VALID_REVIEW = "\n".join(
    heading + "\n\n" + BODIES.get(heading, "Reviewed with saved evidence.")
    for heading in HEADINGS.splitlines()
)


class SelfReviewContractTests(unittest.TestCase):
    def test_rejects_missing_right_table_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            text = VALID_REVIEW.replace(
                "| Run | python solve.py | 0 | artifacts/run.txt | passed |",
                "| Run | python solve.py | 0 | artifacts/run.txt | passedX",
            )
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_rejects_empty_edge_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            text = VALID_REVIEW.replace(
                "| Run | python solve.py | 0 | artifacts/run.txt | passed |",
                "|| Run | python solve.py | 0 | artifacts/run.txt | passed ||",
            )
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("table", result.stderr)

    def test_rejects_skipped_checks_and_empty_tables(self) -> None:
        candidates = [
            VALID_REVIEW.replace(
                "| 0 | artifacts/run.txt | passed |",
                "| 0 | artifacts/run.txt | skipped |",
            ),
            VALID_REVIEW.replace(
                "| 0 | artifacts/run.txt | passed |",
                "| 7 | artifacts/run.txt | passed |",
            ),
            VALID_REVIEW.replace(
                "| Run | python solve.py | 0 | artifacts/run.txt | passed |", ""
            ),
            VALID_REVIEW.replace(
                "| R1 | Required output | artifacts/run.txt | passed | None |", ""
            ),
            VALID_REVIEW + "\nFinal Status: passed\n",
        ]
        for index, text in enumerate(candidates):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "SELF_REVIEW.md"
                path.write_text(text, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CHECKER), str(path), "--require-passed"],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_accepts_inapplicable_dimensions_without_inventing_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            text = VALID_REVIEW.replace("| 0 |", "| not_applicable |").replace(
                "## Code Review\n\nReviewed with saved evidence.",
                "## Code Review\n\nNot applicable: task requires prose only.",
            )
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_hidden_or_ambiguous_review_structure(self) -> None:
        candidates = [
            "```markdown\n" + VALID_REVIEW + "\n```",
            "<!--\n" + VALID_REVIEW + "\n-->",
            "## Blockers\n\nMissing data.\n" + VALID_REVIEW,
            VALID_REVIEW.replace(
                "## Final Status\n\nFinal Status: passed",
                "Final Status: passed\n\n## Final Status\n\nSee above.",
            ),
        ]
        for index, text in enumerate(candidates):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "SELF_REVIEW.md"
                path.write_text(text, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CHECKER), str(path), "--require-passed"],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_passed_rejects_unresolved_requirements_and_findings(self) -> None:
        candidates = [
            VALID_REVIEW.replace("| passed | None |", "| blocked | Missing data |"),
            VALID_REVIEW.replace(
                "## Blockers\n\nNone.", "## Blockers\n\nMissing dataset."
            ),
            VALID_REVIEW.replace(
                "## Changes Requested\n\nNone.",
                "## Changes Requested\n\nmajor: wrong formula.",
            ),
        ]
        for text in candidates:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "SELF_REVIEW.md"
                path.write_text(text, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CHECKER), str(path), "--require-passed"],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_require_passed_rejects_failed_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            path.write_text(
                VALID_REVIEW.replace(
                    "| 0 | artifacts/run.txt | passed |",
                    "| 1 | artifacts/run.txt | failed |",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check", result.stderr.lower())

    def test_require_passed_rejects_empty_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            path.write_text(HEADINGS + "\nFinal Status: passed\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("empty section", result.stderr)

    def test_accepts_passed_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            path.write_text(VALID_REVIEW, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_missing_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            path.write_text(
                "## Scope\n## Final Status\nFinal Status: passed\n", encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing headings", result.stderr)

    def test_require_passed_rejects_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_REVIEW.md"
            path.write_text(HEADINGS + "\nFinal Status: blocked\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-passed"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
