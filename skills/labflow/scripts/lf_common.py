"""Small, bounded, local-only primitives; not an OS security sandbox."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MAX_JSON = 2 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_FILES = 4096


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, required, optional=()):
    require(
        type(value) is dict
        and set(required) <= value.keys()
        and value.keys() <= set(required) | set(optional),
        "invalid object fields",
    )


def text(value):
    require(
        type(value) is str
        and 0 < len(value) <= 4096
        and not any(ord(c) < 32 or ord(c) == 127 for c in value),
        "expected nonempty plain string",
    )
    return value


def names(value, empty=False):
    require(type(value) is list and len(value) <= MAX_FILES, "invalid list")
    require(empty or value, "empty list")
    for item in value:
        text(item)
    require(len(value) == len(set(value)), "duplicate entries")
    return value


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(value):
    require(
        type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "invalid SHA-256"
    )
    return value


def no_links(path):
    path = Path(path).absolute()
    require(
        not any(p.is_symlink() for p in (path, *path.parents)),
        "symlinks are unsupported",
    )
    return path


def inside(root, relative):
    text(relative)
    require(
        not relative.startswith("/")
        and "\\" not in relative
        and ":" not in relative
        and all(p not in ("", ".", "..") for p in relative.split("/")),
        "unsafe relative path",
    )
    root = Path(root).resolve(strict=True)
    path = no_links(root / relative)
    require(path.resolve().is_relative_to(root), "path escapes root")
    return path


def outside(root, path):
    path = Path(path)
    path = no_links(path.parent.resolve() / path.name)
    require(
        not path.is_relative_to(Path(root).resolve()), "state must be outside workspace"
    )
    return path


def file_hash(path):
    path = no_links(path)
    require(
        path.is_file() and path.stat().st_size <= MAX_FILE, "missing or oversized file"
    )
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            require(total <= MAX_FILE, "file exceeds limit")
            h.update(chunk)
    return h.hexdigest()


def load(path):
    path = no_links(path)
    require(path.stat().st_size <= MAX_JSON, "JSON exceeds limit")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite JSON number")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=constant,
    )


def save(path, value, replace=False):
    path = no_links(path)
    data = canonical(value)
    require(len(data) <= MAX_JSON, "JSON exceeds limit")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not replace:
        with os.fdopen(
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        return
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def locked(path):
    path = no_links(str(path) + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def snapshot(root, selections):
    names(selections)
    result = {}
    total = 0

    def visit(path):
        nonlocal total
        no_links(path)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            require(path.is_file(), "missing input or non-regular file")
            rel = path.relative_to(Path(root).resolve()).as_posix()
            if rel not in result:
                require(len(result) < MAX_FILES, "file count exceeds limit")
                total += path.stat().st_size
                require(total <= 256 * 1024 * 1024, "snapshot exceeds size limit")
                result[rel] = file_hash(path)

    for selection in selections:
        visit(inside(root, selection))
    require(result, "empty snapshot")
    return result
