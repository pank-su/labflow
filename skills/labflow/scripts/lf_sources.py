"""Hash-bound source/target fragments. Derived semantics require human review."""

import copy
from lf_common import fields, require, text, names, inside, file_hash, load, save, sha


def fragment(root, endpoint, sealed):
    fields(endpoint, ["path", "locator", "quote"] + (["sha256"] if sealed else []))
    path = inside(root, endpoint["path"])
    actual = file_hash(path)
    if sealed:
        require(
            actual == sha(endpoint["sha256"]),
            "source/target changed: " + endpoint["path"],
        )
    locator = endpoint["locator"]
    require(
        type(locator) is dict and set(locator) in ({"lines"}, {"pages"}),
        "invalid locator",
    )
    kind = next(iter(locator))
    span = locator[kind]
    require(
        type(span) is list
        and len(span) == 2
        and all(type(n) is int for n in span)
        and 1 <= span[0] <= span[1],
        "invalid line locator",
    )
    if kind == "pages":
        require(
            path.suffix.lower() == ".pdf" and span[1] - span[0] < 50,
            "unsupported PDF range",
        )
        try:
            import pymupdf
        except ImportError as exc:
            raise ValueError(
                "PDF locators require PyMuPDF; use uv run --with pymupdf"
            ) from exc
        try:
            with pymupdf.open(path) as doc:
                require(
                    not doc.is_encrypted and span[1] <= len(doc) <= 2000,
                    "PDF unavailable or page outside file",
                )
                selected = "".join(
                    doc[i].get_text() for i in range(span[0] - 1, span[1])
                )
        except RuntimeError as exc:
            raise ValueError("PDF extraction failed") from exc
    else:
        require(path.suffix.lower() != ".pdf", "PDF requires page locator")
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        require(span[1] <= len(lines), "line locator outside file")
        selected = "".join(lines[span[0] - 1 : span[1]])
    quote = text(endpoint["quote"])
    require(quote in selected, "quote not found at locator")
    return actual, quote


def validate(root, data, sealed=True, expected=None):
    fields(data, ["version", "entries"])
    require(
        type(data["version"]) is int and data["version"] == 1,
        "unsupported source map version",
    )
    require(
        type(data["entries"]) is list and 0 < len(data["entries"]) <= 4096,
        "invalid entries",
    )
    ids = []
    for entry in data["entries"]:
        fields(entry, ["id", "source", "target", "transform", "reason", "notation"])
        ids.append(text(entry["id"]))
        require(
            entry["transform"] in ("verbatim", "notation-preserving", "derived"),
            "unsupported transform",
        )
        text(entry["reason"])
        names(entry["notation"], empty=True)
        source_hash, source_quote = fragment(root, entry["source"], sealed)
        target_hash, target_quote = fragment(root, entry["target"], sealed)
        if entry["transform"] == "verbatim":
            require(source_quote == target_quote, "verbatim fragment differs")
        for token in entry["notation"]:
            require(
                token in source_quote and token in target_quote,
                "notation missing or changed",
            )
        if not sealed:
            entry["source"]["sha256"] = source_hash
            entry["target"]["sha256"] = target_hash
    names(ids)
    if expected is not None:
        names(expected)
        require(set(ids) == set(expected), "source map requirement coverage differs")
    return sorted(ids)


def seal(root, spec, output):
    data = copy.deepcopy(load(inside(root, spec)))
    validate(root, data, sealed=False)
    save(inside(root, output), data)
    return {
        "source_map": output,
        "requirements": sorted(e["id"] for e in data["entries"]),
    }


def check(root, path, expected):
    return {"requirements": validate(root, load(inside(root, path)), expected=expected)}
