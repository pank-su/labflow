"""Offline behavioral tests: all data are synthetic, no model/network calls."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "skills/labflow/scripts/labflow.py"


class RuntimeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "work"
        self.root.mkdir()
        self.registry = self.base / "registry"
        self.ledger = self.base / "batch.json"
        self.put("inputs/task.txt", "Compute σ.\nKeep σ notation.\n")
        self.put("out/result.txt", "Result σ = 1.\n")

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            value if isinstance(value, str) else json.dumps(value), encoding="utf-8"
        )
        return path

    def cli(self, command, *args, ok=True):
        run = subprocess.run(
            [
                sys.executable,
                str(CLI),
                command,
                "--root",
                str(self.root),
                *map(str, args),
            ],
            capture_output=True,
            text=True,
        )
        if ok:
            self.assertEqual(run.returncode, 0, run.stderr)
            return json.loads(run.stdout)
        self.assertNotEqual(run.returncode, 0, run.stdout)
        self.assertNotIn("Traceback", run.stderr)
        return run

    def source_spec(self):
        return {
            "version": 1,
            "entries": [
                {
                    "id": "R1",
                    "source": {
                        "path": "inputs/task.txt",
                        "locator": {"lines": [1, 2]},
                        "quote": "Compute σ.",
                    },
                    "target": {
                        "path": "out/result.txt",
                        "locator": {"lines": [1, 1]},
                        "quote": "Result σ = 1.",
                    },
                    "transform": "derived",
                    "reason": "Synthetic fixture calculation",
                    "notation": ["σ"],
                }
            ],
        }

    def seal(self, spec=None):
        self.put("context/source-spec.json", spec or self.source_spec())
        return self.cli(
            "sources-seal",
            "--spec",
            "context/source-spec.json",
            "--output",
            "context/source-map.json",
        )

    def contract(self, scope="publication"):
        return {
            "version": 1,
            "scope": scope,
            "owner": "implementer",
            "inputs": ["inputs", "context"],
            "outputs": ["out"],
            "requirements": ["R1"],
            "source_map": "context/source-map.json",
            "reviewers": ["academic"] if scope != "revision" else [],
            "pages": [],
        }

    def freeze(self, contract=None):
        self.seal()
        self.put("context/candidate.json", contract or self.contract())
        return self.cli(
            "freeze",
            "--registry",
            self.registry,
            "--contract",
            "context/candidate.json",
        )["candidate"]

    def verify(self, candidate, approved=False, ok=True):
        return self.cli(
            "verify",
            "--registry",
            self.registry,
            "--candidate",
            candidate,
            *(["--approved"] if approved else []),
            ok=ok,
        )

    def bundle(self, candidate, status="passed", name="review-1"):
        import runpy

        bundle = self.base / name
        bundle.mkdir(exist_ok=True)
        review = runpy.run_path(
            str(Path(__file__).with_name("test_self_review_contract.py"))
        )["VALID_REVIEW"]
        (bundle / "SELF_REVIEW.md").write_text(review, encoding="utf-8")
        (bundle / "run.log").write_text(
            "Synthetic execution evidence: OK", encoding="utf-8"
        )
        verdict = {
            "version": 1,
            "candidate": candidate,
            "status": status,
            "coverage": ["R1"],
            "pages": [],
            "report": "SELF_REVIEW.md",
            "checks": [
                {
                    "name": "fixture",
                    "status": "passed",
                    "exit_status": 0,
                    "evidence": ["run.log"],
                }
            ],
        }
        (bundle / "verdict.json").write_text(json.dumps(verdict), encoding="utf-8")
        return bundle

    def attest(
        self, candidate, bundle, reviewer="independent-1", slot="academic", ok=True
    ):
        return self.cli(
            "review",
            "--registry",
            self.registry,
            "--candidate",
            candidate,
            "--slot",
            slot,
            "--reviewer-id",
            reviewer,
            "--bundle",
            bundle,
            ok=ok,
        )


class CandidateTests(RuntimeCase):
    def test_declared_output_scope_cannot_be_empty_or_unrelated_to_map(self):
        self.seal()
        (self.root / "empty-output").mkdir()
        contract = self.contract()
        contract["outputs"] = ["empty-output"]
        self.put("context/candidate.json", contract)
        self.cli(
            "freeze",
            "--registry",
            self.registry,
            "--contract",
            "context/candidate.json",
            ok=False,
        )
        self.put("empty-output/unrelated.txt", "Unrelated artifact")
        self.cli(
            "freeze",
            "--registry",
            self.registry,
            "--contract",
            "context/candidate.json",
            ok=False,
        )

    def test_new_file_missing_file_and_contract_change_invalidate(self):
        candidate = self.freeze()
        new = self.put("inputs/untracked.txt", "new untracked source")
        self.verify(candidate, ok=False)
        new.unlink()
        output = self.root / "out/result.txt"
        saved = output.read_bytes()
        output.unlink()
        self.verify(candidate, ok=False)
        output.write_bytes(saved)
        self.verify(candidate)
        contract = self.contract("revision")
        self.put("context/candidate.json", contract)
        self.verify(candidate, ok=False)

    def test_registry_tampering_and_in_workspace_registry_rejected(self):
        candidate = self.freeze()
        record = self.registry / (candidate + ".json")
        data = json.loads(record.read_text())
        data["contract"]["scope"] = "revision"
        record.write_text(json.dumps(data))
        self.verify(candidate, ok=False)
        self.cli(
            "freeze",
            "--registry",
            self.root / "state",
            "--contract",
            "context/candidate.json",
            ok=False,
        )

    def test_revision_never_becomes_full_approval(self):
        candidate = self.freeze(self.contract("revision"))
        self.verify(candidate)
        self.verify(candidate, approved=True, ok=False)

    def test_bad_verdicts_do_not_approve(self):
        candidate = self.freeze()
        for mutation in (
            "identity",
            "candidate",
            "unknown",
            "skipped",
            "bool",
            "coverage",
            "empty",
            "markdown",
        ):
            with self.subTest(mutation=mutation):
                bundle = self.bundle(candidate, name=mutation)
                path = bundle / "verdict.json"
                verdict = json.loads(path.read_text())
                if mutation == "candidate":
                    verdict["candidate"] = "0" * 64
                if mutation == "unknown":
                    verdict["status"] = "success"
                if mutation == "skipped":
                    verdict["checks"][0]["status"] = "skipped"
                if mutation == "bool":
                    verdict["checks"][0]["exit_status"] = False
                if mutation == "coverage":
                    verdict["coverage"] = ["R2"]
                if mutation == "empty":
                    (bundle / "run.log").write_text("")
                if mutation == "markdown":
                    (bundle / "SELF_REVIEW.md").write_text("Final Status: passed")
                path.write_text(json.dumps(verdict))
                self.attest(
                    candidate,
                    bundle,
                    reviewer="implementer"
                    if mutation == "identity"
                    else "independent-1",
                    ok=False,
                )
                self.verify(candidate, approved=True, ok=False)

    def test_review_evidence_mutation_revokes_approval(self):
        candidate = self.freeze()
        bundle = self.bundle(candidate)
        self.attest(candidate, bundle)
        self.verify(candidate, approved=True)
        (bundle / "run.log").write_text("Changed evidence")
        self.verify(candidate, approved=True, ok=False)

    def test_reviewer_slots_need_distinct_identities_and_full_page_scope(self):
        contract = self.contract()
        contract["reviewers"] = ["code", "academic"]
        contract["pages"] = [1, 2]
        candidate = self.freeze(contract)
        for slot in contract["reviewers"]:
            bundle = self.bundle(candidate, name=slot)
            path = bundle / "verdict.json"
            verdict = json.loads(path.read_text())
            verdict["pages"] = [1, 2] if slot == "academic" else []
            path.write_text(json.dumps(verdict))
            self.attest(candidate, bundle, reviewer="same-person", slot=slot)
        self.verify(candidate, approved=True, ok=False)
        self.attest(candidate, self.base / "academic", reviewer="second-person")
        self.verify(candidate, approved=True)

    def test_current_independent_review_approves_and_interruption_revokes(self):
        candidate = self.freeze()
        self.attest(candidate, self.bundle(candidate))
        self.verify(candidate, approved=True)
        self.attest(
            candidate, self.bundle(candidate, status="interrupted", name="interrupted")
        )
        self.verify(candidate, approved=True, ok=False)

    def test_freeze_binds_untracked_source_and_generated_artifact(self):
        candidate = self.freeze()
        self.verify(candidate)
        self.verify(candidate, approved=True, ok=False)
        self.put("out/result.txt", "Changed output")
        self.verify(candidate, ok=False)


class BatchCase(RuntimeCase):
    def batch(self, command, *args, ok=True):
        return self.cli("batch-" + command, "--ledger", self.ledger, *args, ok=ok)

    def initialize(self, items=None):
        items = items or [
            {
                "id": "notes",
                "scope": "revision",
                "sources": ["inputs/task.txt"],
                "outputs": ["out/notes.md"],
                "phases": ["notes", "verify"],
            },
            {
                "id": "second",
                "scope": "revision",
                "sources": ["inputs/second.txt"],
                "outputs": ["out/second.md"],
                "phases": ["notes", "verify"],
            },
        ]
        self.put("batch-spec.json", {"version": 1, "items": items})
        return self.batch("init", "--spec", "batch-spec.json")

    def phase_bundle(self, name, status="passed"):
        bundle = self.base / name
        bundle.mkdir(exist_ok=True)
        (bundle / "action.log").write_text("Synthetic tool output: " + status)
        (bundle / "result.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "exit_status": 0 if status == "passed" else 1,
                    "evidence": ["action.log"],
                }
            )
        )
        return bundle


class BatchTests(BatchCase):
    def test_verified_delivery_resumes_without_repeating_work(self):
        self.initialize()
        started = self.batch("begin", "--id", "notes")
        ticket = started["ticket"]
        self.assertEqual(started["phases"], ["notes", "verify"])
        self.put("out/notes.md", "Synthetic notes from supplied input")
        for phase in started["phases"]:
            self.batch(
                "step",
                "--id",
                "notes",
                "--ticket",
                ticket,
                "--phase",
                phase,
                "--bundle",
                self.phase_bundle(phase),
            )
        self.batch("finish", "--id", "notes", "--ticket", ticket)
        self.assertEqual(
            self.batch("preflight")["items"]["notes"]["status"], "verified"
        )
        receipt = self.base / "receipt.json"
        receipt.write_text(
            json.dumps(
                {"status": "delivered", "channel": "local", "reference": "out/notes.md"}
            )
        )
        self.batch("deliver", "--id", "notes", "--receipt", receipt)
        current = self.batch("preflight")
        self.assertEqual(current["ready"], [])
        self.assertEqual(current["items"]["notes"]["status"], "delivered")
        self.assertFalse(current["complete"])
        self.batch("begin", "--id", "notes", ok=False)
        self.put("inputs/task.txt", "Changed input")
        self.assertEqual(self.batch("preflight")["ready"], ["notes"])

    def test_stop_invalidates_late_callbacks_even_after_resume(self):
        self.initialize()
        ticket = self.batch("begin", "--id", "notes")["ticket"]
        self.batch("stop")
        self.assertEqual(self.batch("preflight")["ready"], [])
        self.batch(
            "step",
            "--id",
            "notes",
            "--ticket",
            ticket,
            "--phase",
            "notes",
            "--bundle",
            self.phase_bundle("late"),
            ok=False,
        )
        self.batch("resume")
        replacement = self.batch("begin", "--id", "notes")["ticket"]
        self.assertNotEqual(ticket, replacement)
        self.batch("finish", "--id", "notes", "--ticket", ticket, ok=False)
        self.assertEqual(self.batch("preflight")["items"]["notes"]["status"], "running")

    def test_full_batch_requires_bound_current_approval(self):
        self.initialize(
            [
                {
                    "id": "csv",
                    "scope": "full",
                    "sources": ["inputs/task.txt"],
                    "outputs": ["out/result.txt"],
                    "phases": ["context", "math", "verify", "review"],
                }
            ]
        )
        ticket = self.batch("begin", "--id", "csv")["ticket"]
        for phase in ("context", "math", "verify"):
            self.batch(
                "step",
                "--id",
                "csv",
                "--ticket",
                ticket,
                "--phase",
                phase,
                "--bundle",
                self.phase_bundle("full-" + phase),
            )
        proof = self.phase_bundle("full-review")
        self.batch(
            "step",
            "--id",
            "csv",
            "--ticket",
            ticket,
            "--phase",
            "review",
            "--bundle",
            proof,
            ok=False,
        )
        candidate = self.freeze()
        self.batch(
            "bind",
            "--id",
            "csv",
            "--ticket",
            ticket,
            "--registry",
            self.registry,
            "--candidate",
            candidate,
        )
        self.batch(
            "step",
            "--id",
            "csv",
            "--ticket",
            ticket,
            "--phase",
            "review",
            "--bundle",
            proof,
            ok=False,
        )
        self.attest(candidate, self.bundle(candidate))
        self.batch(
            "step",
            "--id",
            "csv",
            "--ticket",
            ticket,
            "--phase",
            "review",
            "--bundle",
            proof,
        )
        self.batch("finish", "--id", "csv", "--ticket", ticket)
        self.assertEqual(self.batch("preflight")["items"]["csv"]["status"], "verified")
        self.attest(
            candidate,
            self.bundle(candidate, status="interrupted", name="late-interrupted"),
        )
        self.assertEqual(self.batch("preflight")["items"]["csv"]["status"], "ready")

    def test_failed_items_require_retry_and_skipped_is_not_complete(self):
        self.initialize()
        ticket = self.batch("begin", "--id", "notes")["ticket"]
        self.batch(
            "step",
            "--id",
            "notes",
            "--ticket",
            ticket,
            "--phase",
            "notes",
            "--bundle",
            self.phase_bundle("failed", status="failed"),
        )
        self.assertEqual(self.batch("preflight")["items"]["notes"]["status"], "failed")
        self.batch("begin", "--id", "notes", ok=False)
        self.batch("retry", "--id", "notes")
        self.assertEqual(self.batch("preflight")["ready"], ["notes"])
        self.batch("skip", "--id", "notes", "--reason", "Explicit caller exclusion")
        result = self.batch("preflight")
        self.assertEqual(result["items"]["notes"]["status"], "skipped")
        self.assertFalse(result["complete"])
        self.batch("retry", "--id", "notes")
        self.assertEqual(self.batch("preflight")["ready"], ["notes"])

    def test_missing_independent_input_does_not_block_ready_item(self):
        self.initialize()
        plan = self.batch("preflight")
        self.assertEqual(plan["ready"], ["notes"])
        self.assertEqual(plan["items"]["second"]["status"], "blocked")
        self.put("inputs/second.txt", "Second independent note")
        self.assertEqual(self.batch("preflight")["ready"], ["notes", "second"])


class SourceMapTests(RuntimeCase):
    def test_pdf_page_locator_selects_actual_page(self):
        import pymupdf

        doc = pymupdf.open()
        doc.new_page().insert_text((50, 50), "Wrong page")
        doc.new_page().insert_text((50, 50), "Compute x.")
        doc.save(self.root / "inputs/task.pdf")
        doc.close()
        self.put("out/result.txt", "Result x = 1.")
        spec = self.source_spec()
        entry = spec["entries"][0]
        entry["source"] = {
            "path": "inputs/task.pdf",
            "locator": {"pages": [2, 2]},
            "quote": "Compute x.",
        }
        entry["target"]["quote"] = "Result x = 1."
        entry["notation"] = ["x"]
        self.seal(spec)
        self.cli(
            "sources-check", "--map", "context/source-map.json", "--requirements", "R1"
        )

    def test_bad_source_contracts_fail_without_creating_map(self):
        for mutation in (
            "missing",
            "quote",
            "notation",
            "duplicate",
            "escape",
            "unknown",
        ):
            with self.subTest(mutation=mutation):
                spec = self.source_spec()
                item = spec["entries"][0]
                if mutation == "missing":
                    item["source"]["path"] = "inputs/missing.txt"
                if mutation == "quote":
                    item["source"]["quote"] = "Invented quote"
                if mutation == "notation":
                    item["notation"] = ["UNSUPPORTED_SYMBOL"]
                if mutation == "duplicate":
                    spec["entries"].append(copy.deepcopy(item))
                if mutation == "escape":
                    item["source"]["path"] = "../outside.txt"
                if mutation == "unknown":
                    item["transform"] = "repair-source"
                self.put("context/source-spec.json", spec)
                self.cli(
                    "sources-seal",
                    "--spec",
                    "context/source-spec.json",
                    "--output",
                    "context/map.json",
                    ok=False,
                )
                self.assertFalse((self.root / "context/map.json").exists())

    def test_sealed_map_binds_real_fragments_and_detects_changed_source(self):
        self.seal()
        args = ("--map", "context/source-map.json", "--requirements", "R1")
        result = self.cli("sources-check", *args)
        self.assertEqual(result["requirements"], ["R1"])
        self.put("inputs/task.txt", "Changed source.\n")
        self.cli("sources-check", *args, ok=False)


if __name__ == "__main__":
    unittest.main()
