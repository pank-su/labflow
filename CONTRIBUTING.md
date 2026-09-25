# Contributing

Keep the core skills university- and template-agnostic. Put format-specific
behavior under an optional skill or adapter.

Before committing:

```bash
uv run --python 3.11 --with pyyaml --with pymupdf python -m unittest discover -s tests -v
uv run --python 3.11 --with pyyaml python skills/labflow-typst/scripts/init_typst.py --help
```

Typst is required by the workflow regression suite. Compile a generated smoke
report and inspect its pages. PyMuPDF checks actual PDF fragments and typography.
Do not skip missing dependencies or add real student data/private task files.
