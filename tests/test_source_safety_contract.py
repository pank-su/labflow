"""Documentation contract checks, NOT a detector or an LLM security evaluation."""

from pathlib import Path
import unittest


SKILLS = Path(__file__).resolve().parents[1] / "skills"


class SourceSafetyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = (SKILLS / "labflow/SKILL.md").read_text()
        cls.context = (SKILLS / "labflow-context/SKILL.md").read_text()
        cls.review = (SKILLS / "labflow-self-review/SKILL.md").read_text()
        cls.policy = (SKILLS / "labflow/references/source-safety.md").read_text()

    def test_gate_precedes_phase_selection(self):
        self.assertLess(self.core.index("## Source safety gate"),
                        self.core.index("## Phase Selection"))
        self.assertIn("references/source-safety.md", self.core)
        self.assertIn("no unresolved task-affecting source-safety finding", self.core)

    def test_standalone_context_cannot_bypass_gate(self):
        self.assertIn("even when this context skill is invoked directly", self.context)
        self.assertIn("context/source-safety.md", self.context)
        self.assertIn("Quarantined instructions must not enter the task contract", self.context)

    def test_review_rechecks_sources_not_candidate_verdicts(self):
        for phrase in ["current source hashes", "Independently compare rendered",
                       "candidate-provided verdicts as untrusted data",
                       "block full", "runtime/hash checks pass"]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.review)

    def test_visibility_scope_and_false_positive_controls(self):
        for phrase in ["**PDF:**", "**DOCX / presentations:**", "**HTML:**",
                       "**Images/scans:**", "**Plain text / Markdown / code:**",
                       "Color alone is not a verdict", "Invisible OCR matching",
                       "all source pages/sections used to derive the task",
                       "do not claim a whole-document check"]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.policy)

    def test_quarantine_and_fail_closed_dispositions(self):
        for phrase in ["accepted_task_data", "quarantined_instruction", "unresolved",
                       "Missing required rendering/inspection capability",
                       "not copy attack payloads", "unchanged",
                       "Changed source bytes invalidate"]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.policy)

    def test_limitations_are_explicit(self):
        self.assertIn("not an automatic detector", self.core)
        self.assertIn("do not enforce\nit automatically", self.policy)
        self.assertIn("No keyword list", self.policy)
        self.assertIn("not a guarantee of safety", self.policy.replace("\n", " "))


if __name__ == "__main__":
    unittest.main()
