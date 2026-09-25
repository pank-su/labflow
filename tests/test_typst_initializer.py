from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/labflow-typst/scripts/init_typst.py"


CONTEXT = """
kind: lab
title: Test lab
subject: Test subject
metadata:
  author: Student
  group: M412
  university: Test university
  city: Test city
deliverables:
  report_sections:
    - Цель работы
    - Выполнение работы
    - Выводы
"""


class TypstInitializerTests(unittest.TestCase):
    def test_refuses_protected_project_even_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".guap").mkdir()
            (root / ".guap/lock.json").write_text("protected", encoding="utf-8")
            context = root / "context.json"
            context.write_text(
                json.dumps({"kind": "lab", "title": "Test"}), encoding="utf-8"
            )
            for output in (root, root / "nested"):
                for flags in ([], ["--force"]):
                    with self.subTest(output=output, flags=flags):
                        result = subprocess.run(
                            [
                                sys.executable,
                                str(SCRIPT),
                                "--context",
                                str(context),
                                "--output-dir",
                                str(output),
                                *flags,
                            ],
                            capture_output=True,
                            text=True,
                        )
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("protected", result.stderr)
                        self.assertFalse((output / "docs").exists())
            self.assertEqual((root / ".guap/lock.json").read_text(), "protected")

    def test_generic_protection_marker_and_sibling_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "protected"
            protected.mkdir()
            (protected / ".labflow-protected").touch()
            context = root / "context.json"
            context.write_text(
                json.dumps({"kind": "practical", "title": "Control"}), encoding="utf-8"
            )
            for output, expected in ((protected, False), (root / "sibling", True)):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--context",
                        str(context),
                        "--output-dir",
                        str(output),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode == 0, expected, result.stderr)
                self.assertEqual((output / "docs/index.typ").exists(), expected)

    def test_creates_full_lab_structure_from_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / "context.yaml"
            context.write_text(CONTEXT, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--context",
                    str(context),
                    "--output-dir",
                    tmp,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            output = json.loads(result.stdout)
            self.assertEqual(output["kind"], "lab")
            for relative in (
                "docs/index.typ",
                "docs/content.typ",
                "docs/lib/context.typ",
                "docs/lib/gost.typ",
                "docs/lib/titlepage.typ",
                "artifacts/.gitkeep",
                "data/.gitkeep",
                "images/.gitkeep",
                "math/.gitkeep",
                "src/.gitkeep",
                "tests/.gitkeep",
            ):
                self.assertTrue((root / relative).exists(), relative)
            context_typ = (root / "docs/lib/context.typ").read_text(encoding="utf-8")
            self.assertIn("Test lab", context_typ)
            self.assertIn("Лабораторная работа", context_typ)
            content = (root / "docs/content.typ").read_text(encoding="utf-8")
            self.assertIn("= Цель работы", content)

    def test_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / "context.yaml"
            context.write_text(CONTEXT, encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--context",
                    str(context),
                    "--output-dir",
                    tmp,
                ],
                check=True,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--context",
                    str(context),
                    "--output-dir",
                    tmp,
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
