"""Parent-owned candidate registry. Pin expected ID outside reviewer output."""

from pathlib import Path
import subprocess
import sys
from lf_common import (
    fields,
    require,
    names,
    text,
    digest,
    sha,
    load,
    save,
    inside,
    outside,
    snapshot,
    locked,
)
import lf_sources


def capture(root, contract_path):
    root = Path(root).resolve(strict=True)
    contract = load(inside(root, contract_path))
    fields(
        contract,
        [
            "version",
            "scope",
            "owner",
            "inputs",
            "outputs",
            "requirements",
            "source_map",
            "reviewers",
            "pages",
        ],
    )
    require(
        type(contract["version"]) is int and contract["version"] == 1,
        "unsupported contract version",
    )
    require(contract["scope"] in ("full", "revision", "publication"), "unknown scope")
    text(contract["owner"])
    for key in ("inputs", "outputs", "requirements"):
        names(contract[key])
    names(contract["reviewers"], empty=contract["scope"] == "revision")
    require(len(contract["reviewers"]) <= 8, "too many reviewers")
    for slot in contract["reviewers"]:
        require(
            slot.isascii() and slot.replace("-", "").isalnum(), "invalid reviewer slot"
        )
    pages = contract["pages"]
    require(
        type(pages) is list
        and len(pages) <= 2000
        and all(type(n) is int and 1 <= n <= 2000 for n in pages)
        and len(pages) == len(set(pages)),
        "invalid visual page scope",
    )
    source_map = load(inside(root, contract["source_map"]))
    lf_sources.validate(root, source_map, expected=contract["requirements"])
    for boundary in contract["inputs"] + contract["outputs"]:
        snapshot(root, [boundary])  # Every declared required scope must contain files.
    for entry in source_map["entries"]:
        for side, scopes in (
            ("source", contract["inputs"]),
            ("target", contract["outputs"]),
        ):
            path = entry[side]["path"]
            require(
                any(path == scope or path.startswith(scope + "/") for scope in scopes),
                "source-map endpoint outside declared " + side + " scope",
            )
    paths = (
        contract["inputs"]
        + contract["outputs"]
        + [contract_path, contract["source_map"]]
    )
    paths += [
        e[side]["path"] for e in source_map["entries"] for side in ("source", "target")
    ]
    files = snapshot(root, list(dict.fromkeys(paths)))
    require(
        load(inside(root, contract_path)) == contract, "contract changed during capture"
    )
    return {
        "version": 1,
        "root": str(root),
        "contract_path": contract_path,
        "contract": contract,
        "files": files,
    }


def freeze(root, registry, contract_path):
    registry = outside(root, registry)
    manifest = capture(root, contract_path)
    candidate = digest(manifest)
    path = registry / (candidate + ".json")
    if path.exists():
        require(load(path) == manifest, "registry collision")
    else:
        save(path, manifest)
    return {
        "candidate": candidate,
        "files": len(manifest["files"]),
        "state": "fingerprint_verified",
    }


def bundle_check(bundle, candidate, contract):
    bundle = Path(bundle).resolve(strict=True)
    verdict = load(inside(bundle, "verdict.json"))
    fields(
        verdict,
        ["version", "candidate", "status", "coverage", "pages", "report", "checks"],
    )
    require(
        type(verdict["version"]) is int and verdict["version"] == 1,
        "unsupported verdict version",
    )
    require(sha(verdict["candidate"]) == candidate, "review is for another candidate")
    require(
        verdict["status"] in ("passed", "changes_requested", "blocked", "interrupted"),
        "unknown review status",
    )
    names(verdict["coverage"], empty=True)
    pages = verdict["pages"]
    require(
        type(pages) is list
        and len(pages) <= 2000
        and all(type(n) is int and 1 <= n <= 2000 for n in pages)
        and len(pages) == len(set(pages)),
        "invalid reviewed pages",
    )
    checks = verdict["checks"]
    require(type(checks) is list and len(checks) <= 256, "invalid checks")
    paths = ["verdict.json"]
    labels = []
    for check in checks:
        fields(check, ["name", "status", "exit_status", "evidence"])
        labels.append(text(check["name"]))
        require(
            check["status"] in ("passed", "failed", "blocked", "skipped"),
            "unknown check status",
        )
        require(
            type(check["exit_status"]) is int
            or check["exit_status"] == "not_applicable",
            "invalid exit status",
        )
        names(check["evidence"])
        paths += check["evidence"]
        if verdict["status"] == "passed":
            require(
                check["status"] == "passed"
                and check["exit_status"] in (0, "not_applicable"),
                "nonpassing check",
            )
    names(labels, empty=True)
    if verdict["report"] is not None:
        paths.append(text(verdict["report"]))
    if verdict["status"] == "passed":
        require(
            checks and set(verdict["coverage"]) == set(contract["requirements"]),
            "review coverage incomplete",
        )
        require(verdict["report"] is not None, "review report missing")
        report = inside(bundle, verdict["report"])
        checker = (
            Path(__file__).resolve().parents[2]
            / "labflow-self-review/scripts/check_self_review.py"
        )
        require(checker.is_file(), "install sibling labflow-self-review skill")
        result = subprocess.run(
            [sys.executable, str(checker), str(report), "--require-passed"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        require(result.returncode == 0, "Markdown review did not pass strict checker")
        section = (
            report.read_text(encoding="utf-8")
            .split("## Requirement Coverage\n", 1)[1]
            .split("\n## ", 1)[0]
        )
        ids = [
            line.strip()[1:-1].split("|")[0].strip()
            for line in section.splitlines()
            if line.strip().startswith("|")
        ][2:]
        names(ids)
        require(
            set(ids) == set(contract["requirements"]),
            "Markdown/contract coverage differs",
        )
    for path in paths:
        require(inside(bundle, path).stat().st_size > 0, "empty review evidence")
    return {"verdict": verdict, "files": snapshot(bundle, list(dict.fromkeys(paths)))}


def review_history(registry, candidate, slot):
    folder = registry / "reviews" / candidate / slot
    if not folder.exists():
        return []
    files = sorted(folder.iterdir())
    require(
        len(files) <= 9999
        and [p.name for p in files]
        == [f"{i:06d}.json" for i in range(1, len(files) + 1)],
        "invalid or incomplete review journal",
    )
    return files


def attest(root, registry, candidate, slot, reviewer, bundle):
    registry = outside(root, registry)
    manifest = verify(root, registry, candidate)
    contract = manifest["contract"]
    require(slot in contract["reviewers"], "unexpected reviewer slot")
    require(
        text(reviewer) != contract["owner"], "reviewer must differ from implementer"
    )
    bundle = outside(root, bundle)
    payload = bundle_check(bundle, candidate, contract)
    record = {
        "candidate": candidate,
        "reviewer": reviewer,
        "bundle": str(bundle),
        **payload,
    }
    with locked(registry / "review-journal"):
        verify(root, registry, candidate)
        history = review_history(registry, candidate, slot)
        save(
            registry / "reviews" / candidate / slot / f"{len(history) + 1:06d}.json",
            record,
        )
    return {
        "candidate": candidate,
        "slot": slot,
        "status": payload["verdict"]["status"],
    }


def check_approval(root, registry, candidate, manifest):
    contract = manifest["contract"]
    require(contract["scope"] != "revision", "bounded revision is not full approval")
    identities = []
    pages = set()
    for slot in contract["reviewers"]:
        history = review_history(registry, candidate, slot)
        require(history, "independent reviews missing: " + slot)
        record = load(history[-1])
        fields(record, ["candidate", "reviewer", "bundle", "verdict", "files"])
        require(record["candidate"] == candidate, "review journal candidate mismatch")
        require(record["reviewer"] != contract["owner"], "self review cannot approve")
        payload = bundle_check(outside(root, record["bundle"]), candidate, contract)
        require(
            payload == {"verdict": record["verdict"], "files": record["files"]},
            "review evidence changed",
        )
        require(payload["verdict"]["status"] == "passed", "latest review did not pass")
        identities.append(record["reviewer"])
        pages.update(payload["verdict"]["pages"])
    names(identities)
    require(
        pages == set(contract["pages"]), "visual coverage differs from frozen scope"
    )


def approval_stamp(root, registry, candidate):
    """Cheap revocation check AFTER approval: hashes only, no extraction/reviewer."""
    registry = outside(root, registry)
    manifest = load(registry / (sha(candidate) + ".json"))
    require(
        digest(manifest) == candidate and manifest["root"] == str(Path(root).resolve()),
        "invalid candidate identity",
    )
    paths = list(
        dict.fromkeys(
            manifest["contract"]["inputs"]
            + manifest["contract"]["outputs"]
            + list(manifest["files"])
        )
    )
    require(snapshot(root, paths) == manifest["files"], "candidate changed")
    proofs = {
        "registry": snapshot(registry, [candidate + ".json", "reviews/" + candidate]),
        "bundles": {},
    }
    for slot in manifest["contract"]["reviewers"]:
        history = review_history(registry, candidate, slot)
        require(history, "review missing")
        record = load(history[-1])
        proofs["bundles"][slot] = snapshot(
            outside(root, record["bundle"]), list(record["files"])
        )
    return digest(proofs)


def verify(root, registry, candidate, approved=False):
    registry = outside(root, registry)
    manifest = load(registry / (sha(candidate) + ".json"))
    require(digest(manifest) == candidate, "registry manifest changed")
    require(
        str(Path(root).resolve()) == manifest["root"], "candidate workspace differs"
    )
    require(capture(root, manifest["contract_path"]) == manifest, "candidate changed")
    if approved:
        check_approval(root, registry, candidate, manifest)
    return manifest
