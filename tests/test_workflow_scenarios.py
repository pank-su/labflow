"""End-to-end caller scenarios with real local tool executions, not an LLM eval."""

import json
import subprocess
import sys
from test_runtime import BatchCase, CLI

sys.path.insert(0, str(CLI.parent))
import lf_batch


class WorkflowScenarios(BatchCase):
    def executor(self, calls):
        def execute(item_id, phase, ticket):
            calls.append((item_id, phase))
            bundle = self.base / ("execution-" + str(len(calls)))
            bundle.mkdir()
            target = self.root / (
                "out/notes.md" if item_id == "notes" else "out/second.md"
            )
            source = self.root / (
                "inputs/task.txt" if item_id == "notes" else "inputs/second.txt"
            )
            if phase == "notes":
                code = "from pathlib import Path; import sys; p=Path(sys.argv[2]); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(Path(sys.argv[1]).read_text())"
            elif phase == "verify":
                code = 'from pathlib import Path; import sys; assert Path(sys.argv[1]).read_bytes()==Path(sys.argv[2]).read_bytes(); print("VERIFIED")'
            else:
                raise AssertionError("Unexpected expensive phase: " + phase)
            run = subprocess.run(
                [sys.executable, "-c", code, str(source), str(target)],
                capture_output=True,
                text=True,
            )
            (bundle / "action.log").write_text(
                json.dumps(
                    {
                        "returncode": run.returncode,
                        "stdout": run.stdout,
                        "stderr": run.stderr,
                    }
                )
            )
            (bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "passed" if run.returncode == 0 else "failed",
                        "exit_status": run.returncode,
                        "evidence": ["action.log"],
                    }
                )
            )
            return bundle

        return execute

    def csv_executor(self, calls, stop_at_review=False):
        def execute(item_id, phase, ticket):
            calls.append(phase)
            bundle = self.base / ("csv-" + phase)
            bundle.mkdir()
            if phase == "context":
                self.put(
                    "context/TASK.md",
                    "Synthetic requirement R1: sum supplied data using σ.",
                )
                code = 'print("Context saved")'
            elif phase == "math":
                code = "from pathlib import Path; import csv; values=[int(r['value']) for r in csv.DictReader(Path('inputs/data.csv').open())]; Path('out/result.csv').write_text('symbol,value\\nσ,'+str(sum(values))+'\\n'); print(sum(values))"
            elif phase == "verify":
                code = "from pathlib import Path; import csv; values=[int(r['value']) for r in csv.DictReader(Path('inputs/data.csv').open())]; rows=list(csv.DictReader(Path('out/result.csv').open())); assert rows==[{'symbol':'σ','value':str(sum(values))}]; print('CSV VERIFIED')"
            elif phase == "review":
                spec = self.source_spec()
                spec["entries"][0]["target"] = {
                    "path": "out/result.csv",
                    "locator": {"lines": [2, 2]},
                    "quote": (self.root / "out/result.csv").read_text().splitlines()[1],
                }
                self.seal(spec)
                self.put("context/candidate.json", self.contract())
                candidate = self.cli(
                    "freeze",
                    "--registry",
                    self.registry,
                    "--contract",
                    "context/candidate.json",
                )["candidate"]
                self.batch(
                    "bind",
                    "--id",
                    item_id,
                    "--ticket",
                    ticket,
                    "--registry",
                    self.registry,
                    "--candidate",
                    candidate,
                )
                if stop_at_review:
                    self.batch("stop")
                else:
                    self.attest(
                        candidate, self.bundle(candidate)
                    )  # Explicit synthetic reviewer fixture.
                code = 'print("Synthetic review callback finished")'
            else:
                raise AssertionError("CSV must not invoke report/OCR: " + phase)
            run = subprocess.run(
                [sys.executable, "-c", code],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            (bundle / "action.log").write_text(
                json.dumps(
                    {
                        "stdout": run.stdout,
                        "stderr": run.stderr,
                        "returncode": run.returncode,
                    }
                )
            )
            (bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "passed" if run.returncode == 0 else "failed",
                        "exit_status": run.returncode,
                        "evidence": ["action.log"],
                    }
                )
            )
            return bundle

        return execute

    def init_csv(self):
        self.put("inputs/data.csv", "value\n2\n3\n")
        self.initialize(
            [
                {
                    "id": "csv",
                    "scope": "full",
                    "sources": ["inputs"],
                    "outputs": ["out/result.csv"],
                    "phases": ["context", "math", "verify", "review"],
                }
            ]
        )

    def test_csv_workflow_executes_math_without_fabricating_pdf(self):
        self.init_csv()
        calls = []
        state = lf_batch.run_ready(self.root, self.ledger, self.csv_executor(calls))
        self.assertEqual(calls, ["context", "math", "verify", "review"])
        self.assertEqual(state["items"]["csv"]["status"], "verified")
        self.assertFalse(list(self.root.rglob("*.pdf")))
        lf_batch.run_ready(self.root, self.ledger, self.csv_executor(calls))
        self.assertEqual(len(calls), 4)
        self.put("inputs/data.csv", "value\n4\n5\n")
        self.assertEqual(self.batch("preflight")["ready"], ["csv"])

    def test_stop_during_review_rejects_late_success_and_delivery(self):
        self.init_csv()
        calls = []
        state = lf_batch.run_ready(
            self.root, self.ledger, self.csv_executor(calls, stop_at_review=True)
        )
        self.assertEqual(calls, ["context", "math", "verify", "review"])
        self.assertTrue(state["paused"])
        self.assertEqual(state["items"]["csv"]["status"], "ready")
        self.assertFalse(state["complete"])
        lf_batch.run_ready(self.root, self.ledger, self.csv_executor(calls))
        self.assertEqual(len(calls), 4)

    def test_bounded_heading_rebuild_does_not_touch_code(self):
        import pymupdf

        sentinel = self.put("src/unrelated.py", "UNCHANGED_CODE_SENTINEL")
        before = sentinel.read_bytes()
        self.put("inputs/edit.txt", "Replace OldHeading with NewHeading only")
        self.put("docs/index.typ", "= OldHeading\nUnchanged body.")
        self.initialize(
            [
                {
                    "id": "heading",
                    "scope": "revision",
                    "sources": ["inputs/edit.txt"],
                    "outputs": ["docs/index.typ", "docs/report.pdf"],
                    "phases": ["report", "verify"],
                }
            ]
        )
        calls = []

        def execute(item_id, phase, ticket):
            calls.append(phase)
            bundle = self.base / ("heading-" + phase)
            bundle.mkdir()
            if phase == "report":
                source = self.root / "docs/index.typ"
                source.write_text(
                    source.read_text().replace("OldHeading", "NewHeading")
                )
                run = subprocess.run(
                    [
                        "typst",
                        "compile",
                        str(source),
                        str(self.root / "docs/report.pdf"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
            else:
                with pymupdf.open(self.root / "docs/report.pdf") as doc:
                    text = "".join(page.get_text() for page in doc)
                    self.assertIn("NewHeading", text)
                    self.assertIn("Unchanged body.", text)
                    self.assertNotIn("OldHeading", text)
                    for i, page in enumerate(doc):
                        page.get_pixmap().save(bundle / f"page-{i + 1}.png")
            (bundle / "action.log").write_text("Synthetic heading check completed")
            (bundle / "result.json").write_text(
                json.dumps(
                    {"status": "passed", "exit_status": 0, "evidence": ["action.log"]}
                )
            )
            return bundle

        state = lf_batch.run_ready(self.root, self.ledger, execute)
        self.assertEqual(calls, ["report", "verify"])
        self.assertEqual(sentinel.read_bytes(), before)
        self.assertEqual(state["items"]["heading"]["status"], "verified")
        self.assertIn("not full approval", state["items"]["heading"]["reason"])

    def test_unavailable_source_invokes_no_executor(self):
        (self.root / "inputs/task.txt").unlink()
        self.initialize()
        calls = []
        state = lf_batch.run_ready(self.root, self.ledger, self.executor(calls))
        self.assertEqual(calls, [])
        self.assertTrue(
            all(item["status"] == "blocked" for item in state["items"].values())
        )
        self.assertFalse((self.root / "out/notes.md").exists())

    def test_two_independent_notes_resume_only_new_input(self):
        self.initialize()
        calls = []
        lf_batch.run_ready(self.root, self.ledger, self.executor(calls))
        self.put("inputs/second.txt", "Independent second source")
        state = lf_batch.run_ready(self.root, self.ledger, self.executor(calls))
        self.assertEqual(
            calls,
            [
                ("notes", "notes"),
                ("notes", "verify"),
                ("second", "notes"),
                ("second", "verify"),
            ],
        )
        self.assertTrue(
            all(item["status"] == "verified" for item in state["items"].values())
        )
        self.assertFalse(
            state["complete"]
        )  # Verified files do not fabricate delivery receipts.

    def test_noop_calls_zero_tools_and_missing_item_stays_pending(self):
        self.initialize()
        self.assertTrue(
            hasattr(lf_batch, "run_ready"), "trusted caller dispatcher not implemented"
        )
        calls = []
        result = lf_batch.run_ready(self.root, self.ledger, self.executor(calls))
        self.assertEqual(calls, [("notes", "notes"), ("notes", "verify")])
        self.assertEqual(result["items"]["notes"]["status"], "verified")
        self.assertEqual(result["items"]["second"]["status"], "blocked")
        self.assertFalse(result["complete"])
        lf_batch.run_ready(self.root, self.ledger, self.executor(calls))
        self.assertEqual(len(calls), 2)
        self.assertFalse(list(self.root.rglob("*.pdf")))
        self.assertFalse((self.root / "out/second.md").exists())
