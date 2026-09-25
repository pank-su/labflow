# Contributing

Keep the core skills university- and template-agnostic. Put format-specific
behavior under an optional skill or adapter.

Before committing:

```bash
uv run --python 3.11 --with pyyaml python -m unittest discover -s tests -v
uv run --python 3.11 --with pyyaml python skills/labflow-typst/scripts/init_typst.py --help
```

If Typst is installed, compile a generated smoke report and confirm that the PDF
is non-empty. Do not add real student data or private task files.
