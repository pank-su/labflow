#!/usr/bin/env python3
"""Create the complete Typst project structure from task context."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, cast


KIND_NAMES = {
    "lab": "Лабораторная работа",
    "coursework": "Курсовой проект",
    "practical": "Практическая работа",
}

DEFAULT_SECTIONS = {
    "coursework": [
        "Введение",
        "Анализ предметной области",
        "Разработка требований к программе",
        "Разработка программы",
        "Кодирование и отладка программы",
        "Тестирование",
        "Выводы",
    ],
    "lab": [
        "Цель работы",
        "Вариант задания",
        "Выполнение работы",
        "Выводы",
    ],
    "practical": [
        "Цель работы",
        "Исходные данные и требования",
        "Выполнение работы",
        "Результаты",
        "Выводы",
    ],
}

GENERATED_RELATIVE = (
    "docs/index.typ",
    "docs/content.typ",
    "docs/lib/context.typ",
    "docs/lib/gost.typ",
    "docs/lib/titlepage.typ",
)
STRUCTURE_DIRS = ("artifacts", "data", "images", "math", "src", "tests")


def load_context(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"context file does not exist: {path}")
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
        else:
            import yaml  # type: ignore[import-not-found]

            value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except ModuleNotFoundError as exc:
        raise SystemExit("YAML context requires PyYAML; use JSON or install pyyaml") from exc
    except Exception as exc:
        raise SystemExit(f"cannot parse context {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("context must contain a top-level mapping")
    return value


def value(context: dict[str, Any], metadata: dict[str, Any], key: str) -> str:
    raw = metadata.get(key, context.get(key, ""))
    if raw is None:
        return ""
    if isinstance(raw, (list, dict)):
        return ""
    return str(raw).strip()


def typst_string(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def normalize_kind(raw: str) -> str:
    kind = raw.lower()
    if "course" in kind or "курсов" in kind:
        return "coursework"
    if "lab" in kind or "лаборатор" in kind:
        return "lab"
    return "practical"


def sections_for(context: dict[str, Any], kind: str) -> list[str]:
    deliverables = context.get("deliverables")
    if isinstance(deliverables, dict):
        sections = deliverables.get("report_sections")
        if isinstance(sections, list) and all(isinstance(item, str) and item.strip() for item in sections):
            return [item.strip() for item in sections]
    return DEFAULT_SECTIONS[kind]


def make_content(sections: list[str]) -> str:
    chunks = []
    for section in sections:
        chunks.append(
            f"= {section}\n\n"
            "// Заполнить только по context/TASK.md, исходным данным и сохранённым артефактам.\n"
            "// Не добавлять значения или выводы, которых нет в материалах проекта.\n"
        )
    return "\n".join(chunks) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context_path = args.context.resolve()
    output = args.output_dir.resolve()
    # Marker detection only: institutional layout and metadata stay in adapters.
    for directory in (output, *output.parents):
        for marker_name in (".labflow-protected", ".guap"):
            marker = directory / marker_name
            if marker.exists() or marker.is_symlink():
                raise SystemExit(f"refusing to initialize inside protected project: {directory}; use its adapter")
    context = load_context(context_path)
    metadata_raw = context.get("metadata")
    metadata: dict[str, Any] = (
        cast(dict[str, Any], metadata_raw) if isinstance(metadata_raw, dict) else {}
    )

    raw_kind = value(context, metadata, "kind")
    title = value(context, metadata, "title")
    if not raw_kind or not title:
        missing = [name for name, item in (("kind", raw_kind), ("title", title)) if not item]
        raise SystemExit("context is missing required fields: " + ", ".join(missing))

    kind = normalize_kind(raw_kind)
    template_root = Path(__file__).resolve().parents[1] / "templates" / "gost"
    generated = [output / relative for relative in GENERATED_RELATIVE]
    if not args.force:
        existing = [str(path.relative_to(output)) for path in generated if path.exists()]
        if existing:
            raise SystemExit("refusing to overwrite existing generated files: " + ", ".join(existing) + "; use --force")

    docs_lib = output / "docs" / "lib"
    docs_lib.mkdir(parents=True, exist_ok=True)
    for filename in ("gost.typ", "titlepage.typ"):
        shutil.copy2(template_root / "lib" / filename, docs_lib / filename)

    metadata_values = {
        "KIND": KIND_NAMES[kind],
        "TITLE": title,
        "SUBJECT": value(context, metadata, "subject"),
        "AUTHOR": value(context, metadata, "author"),
        "GROUP": value(context, metadata, "group"),
        "UNIVERSITY": value(context, metadata, "university"),
        "FACULTY": value(context, metadata, "faculty"),
        "DEPARTMENT": value(context, metadata, "department"),
        "TEACHER": value(context, metadata, "teacher"),
        "CITY": value(context, metadata, "city"),
        "DATE": value(context, metadata, "date"),
    }
    context_typ = (template_root / "lib" / "context.typ").read_text(encoding="utf-8")
    for key, raw in metadata_values.items():
        context_typ = context_typ.replace(f"__{key}__", typst_string(raw))
    (docs_lib / "context.typ").write_text(context_typ, encoding="utf-8")

    index = (template_root / "index.typ").read_text(encoding="utf-8")
    (output / "docs" / "index.typ").write_text(index, encoding="utf-8")
    sections = sections_for(context, kind)
    (output / "docs" / "content.typ").write_text(make_content(sections), encoding="utf-8")

    created: list[str] = []
    for relative in GENERATED_RELATIVE:
        path = output / relative
        created.append(str(path.relative_to(output)))
    for directory in STRUCTURE_DIRS:
        path = output / directory
        path.mkdir(parents=True, exist_ok=True)
        keep = path / ".gitkeep"
        keep.touch(exist_ok=True)
        created.append(str(keep.relative_to(output)))

    missing_metadata = [
        name
        for name in ("subject", "author", "group", "university", "faculty", "department", "teacher", "city", "date")
        if not value(context, metadata, name)
    ]
    result = {"kind": kind, "created": created, "missing_metadata": missing_metadata}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
