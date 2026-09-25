"""Single-owner batch ledger. Preflight hashes inputs without loading domain tools."""

from pathlib import Path
import secrets
import lf_candidate
from lf_common import (
    fields,
    require,
    names,
    text,
    load,
    save,
    inside,
    outside,
    snapshot,
    file_hash,
    locked,
)

PHASES = ("context", "code", "math", "notes", "report", "verify", "review")


def overlaps(a, b):
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def validate_spec(root, spec):
    fields(spec, ["version", "items"])
    require(
        type(spec["version"]) is int and spec["version"] == 1,
        "unsupported batch version",
    )
    require(
        type(spec["items"]) is list and 0 < len(spec["items"]) <= 256,
        "invalid batch size",
    )
    ids, outputs = [], []
    for item in spec["items"]:
        fields(item, ["id", "scope", "sources", "outputs", "phases"])
        ids.append(text(item["id"]))
        require(
            item["scope"] in ("full", "revision", "publication"), "unknown item scope"
        )
        for key in ("sources", "outputs", "phases"):
            names(item[key])
        for path in item["sources"] + item["outputs"]:
            inside(root, path)
        require(
            all(phase in PHASES for phase in item["phases"])
            and "verify" in item["phases"],
            "invalid phase plan",
        )
        require(
            item["phases"] == sorted(item["phases"], key=PHASES.index),
            "phase plan out of order",
        )
        if item["scope"] != "revision":
            require(
                item["phases"][0] == "context" and item["phases"][-1] == "review",
                "full item needs context and review",
            )
        require(
            not any(overlaps(a, b) for a in item["sources"] for b in item["outputs"]),
            "outputs overlap source scope",
        )
        for output in item["outputs"]:
            require(
                not any(overlaps(output, other) for other in outputs),
                "overlapping batch outputs",
            )
            outputs.append(output)
    names(ids)


def reset(item, status, reason):
    item.update(
        status=status,
        reason=reason,
        ticket=None,
        steps=[],
        binding=None,
        outputs={},
        receipt=None,
    )
    item["generation"] += 1


def refresh(root, state):
    for item in state["items"].values():
        if item["status"] == "skipped":
            continue
        try:
            current = snapshot(root, item["spec"]["sources"])
        except (OSError, ValueError) as exc:
            if item["status"] != "blocked":
                reset(item, "blocked", str(exc))
            item["reason"] = str(exc)
            continue
        if current != item["source"] or item["status"] == "blocked":
            reset(item, "ready", "source available or changed")
            item["source"] = current
        if item["status"] in ("verified", "delivered"):
            try:
                require(
                    snapshot(root, item["spec"]["outputs"]) == item["outputs"],
                    "output changed",
                )
                check_steps(root, item)
                if item["binding"]:
                    require(
                        lf_candidate.approval_stamp(root, **item["binding"])
                        == item["approval_stamp"],
                        "approval revoked",
                    )
                if item.get("receipt"):
                    require(
                        file_hash(item["receipt"]["path"]) == item["receipt"]["sha256"],
                        "delivery receipt changed",
                    )
            except (OSError, ValueError) as exc:
                reset(item, "ready", str(exc))
    return summary(state)


def summary(state):
    return {
        "paused": state["paused"],
        "ready": [
            key
            for key, item in state["items"].items()
            if item["status"] == "ready" and not state["paused"]
        ],
        "items": {
            key: {"status": item["status"], "reason": item["reason"]}
            for key, item in state["items"].items()
        },
        "complete": bool(state["items"])
        and all(item["status"] == "delivered" for item in state["items"].values()),
    }


def initialize(root, ledger, spec_path):
    root = Path(root).resolve(strict=True)
    ledger = outside(root, ledger)
    spec = load(inside(root, spec_path))
    validate_spec(root, spec)
    state = {
        "version": 1,
        "root": str(root),
        "spec_path": spec_path,
        "spec_hash": file_hash(inside(root, spec_path)),
        "paused": False,
        "items": {},
    }
    for item in spec["items"]:
        state["items"][item["id"]] = {
            "spec": item,
            "source": None,
            "status": "ready",
            "reason": "",
            "generation": 0,
            "ticket": None,
            "steps": [],
            "binding": None,
            "outputs": {},
        }
    result = refresh(root, state)
    save(ledger, state)
    return result


def read_state(root, ledger):
    state = load(ledger)
    fields(state, ["version", "root", "spec_path", "spec_hash", "paused", "items"])
    require(
        type(state["version"]) is int
        and state["version"] == 1
        and type(state["paused"]) is bool,
        "invalid ledger",
    )
    require(state["root"] == str(Path(root).resolve()), "ledger workspace differs")
    require(
        file_hash(inside(root, state["spec_path"])) == state["spec_hash"],
        "batch spec changed; initialize a new ledger",
    )
    return state


def phase_result(root, bundle):
    bundle = outside(root, bundle)
    result = load(inside(bundle, "result.json"))
    fields(result, ["status", "exit_status", "evidence"])
    require(
        result["status"] in ("passed", "failed", "blocked", "skipped"),
        "unknown phase result",
    )
    require(
        type(result["exit_status"]) is int or result["exit_status"] == "not_applicable",
        "invalid exit status",
    )
    names(result["evidence"], empty=result["status"] != "passed")
    if result["status"] == "passed":
        require(
            result["exit_status"] in (0, "not_applicable"), "nonzero exit cannot pass"
        )
    paths = list(dict.fromkeys(["result.json"] + result["evidence"]))
    for path in paths:
        require(inside(bundle, path).stat().st_size > 0, "empty phase evidence")
    return {"bundle": str(bundle), "result": result, "files": snapshot(bundle, paths)}


def check_steps(root, item):
    for step in item["steps"]:
        require(
            phase_result(root, step["proof"]["bundle"]) == step["proof"],
            "phase evidence changed",
        )


def active(state, item, ticket):
    require(
        not state["paused"]
        and item["status"] == "running"
        and item["ticket"] == ticket
        and ticket,
        "stopped, unavailable or stale ticket",
    )


def action(root, ledger, operation, **args):
    ledger = outside(root, ledger)
    with locked(ledger):
        state = read_state(root, ledger)
        refresh(root, state)
        try:
            if operation in ("stop", "resume"):
                state["paused"] = operation == "stop"
                if state["paused"]:
                    for current in state["items"].values():
                        if current["status"] == "running":
                            reset(current, "ready", "stopped; old ticket revoked")
                return summary(state)
            require(args["id"] in state["items"], "unknown batch item")
            item = state["items"][args["id"]]
            if operation in ("retry", "skip"):
                if operation == "retry":
                    require(
                        item["status"] in ("failed", "blocked", "skipped"),
                        "item does not need retry",
                    )
                    reset(item, "ready", "explicit retry")
                    refresh(root, state)
                else:
                    reset(item, "skipped", text(args["reason"]))
                return summary(state)
            if operation == "begin":
                require(
                    not state["paused"] and item["status"] == "ready",
                    "item is not ready",
                )
                item.update(
                    status="running",
                    ticket=secrets.token_hex(16),
                    steps=[],
                    reason="executing",
                )
                item["generation"] += 1
                return {"ticket": item["ticket"], "phases": item["spec"]["phases"]}
            if operation == "deliver":
                require(
                    not state["paused"] and item["status"] == "verified",
                    "only verified item can be delivered",
                )
                receipt_path = outside(root, args["receipt"])
                receipt = load(receipt_path)
                fields(receipt, ["status", "channel", "reference"])
                require(receipt["status"] == "delivered", "delivery did not succeed")
                text(receipt["channel"])
                text(receipt["reference"])
                if receipt["channel"] == "local":
                    require(
                        receipt["reference"] in item["spec"]["outputs"],
                        "local receipt targets another output",
                    )
                item.update(
                    status="delivered",
                    reason="delivery receipt recorded",
                    receipt={
                        "path": str(receipt_path),
                        "sha256": file_hash(receipt_path),
                    },
                )
                return summary(state)
            active(state, item, args["ticket"])
            check_steps(root, item)
            if operation == "abort":
                item.update(status="failed", reason=text(args["reason"]), ticket=None)
                return summary(state)
            if operation == "permit":
                phases = item["spec"]["phases"]
                require(
                    len(item["steps"]) < len(phases)
                    and args["phase"] == phases[len(item["steps"])],
                    "phase not authorized",
                )
                return {
                    "id": args["id"],
                    "phase": args["phase"],
                    "ticket": item["ticket"],
                }
            if operation == "bind":
                manifest = lf_candidate.verify(
                    root, args["registry"], args["candidate"]
                )
                require(
                    manifest["contract"]["scope"] != "revision",
                    "full candidate required for review phase",
                )
                bound = snapshot(
                    root, item["spec"]["sources"] + item["spec"]["outputs"]
                )
                require(
                    all(
                        manifest["files"].get(path) == value
                        for path, value in bound.items()
                    ),
                    "candidate does not cover batch item",
                )
                item["binding"] = {
                    "registry": str(outside(root, args["registry"])),
                    "candidate": args["candidate"],
                }
                return summary(state)
            if operation == "step":
                phases = item["spec"]["phases"]
                require(
                    len(item["steps"]) < len(phases)
                    and args["phase"] == phases[len(item["steps"])],
                    "phase out of order",
                )
                proof = phase_result(root, args["bundle"])
                if args["phase"] == "review" and proof["result"]["status"] == "passed":
                    require(item["binding"], "independent candidate binding required")
                    lf_candidate.verify(root, **item["binding"], approved=True)
                item["steps"].append({"phase": args["phase"], "proof": proof})
                if proof["result"]["status"] != "passed":
                    item.update(
                        status="failed",
                        reason=args["phase"] + ": " + proof["result"]["status"],
                        ticket=None,
                    )
            elif operation == "finish":
                if (
                    item["spec"]["scope"] != "revision"
                    or "review" in item["spec"]["phases"]
                ):
                    require(item["binding"], "full independent approval required")
                    lf_candidate.verify(root, **item["binding"], approved=True)
                    item["approval_stamp"] = lf_candidate.approval_stamp(
                        root, **item["binding"]
                    )
                require(
                    [step["phase"] for step in item["steps"]] == item["spec"]["phases"],
                    "phases incomplete",
                )
                item.update(
                    outputs=snapshot(root, item["spec"]["outputs"]),
                    status="verified",
                    ticket=None,
                    reason="independently verified"
                    if item["binding"]
                    else "local revision verified; not full approval",
                )
            else:
                raise ValueError("unsupported operation")
            return summary(state)
        finally:
            save(ledger, state, replace=True)


def run_ready(root, ledger, executor):
    """Trusted Python caller hook. Never import or execute a runner named in source data.

    executor(item_id, phase, ticket) returns an outside-workspace result bundle.
    It owns actual tool calls. Verification is not delivery; caller records a receipt.
    """
    for item_id in preflight(root, ledger)["ready"]:
        current = preflight(root, ledger)
        if current["paused"]:
            break
        if item_id not in current["ready"]:
            continue
        started = action(root, ledger, "begin", id=item_id)
        ticket = started["ticket"]
        try:
            for phase in started["phases"]:
                action(root, ledger, "permit", id=item_id, ticket=ticket, phase=phase)
                bundle = executor(item_id, phase, ticket)
                action(
                    root,
                    ledger,
                    "step",
                    id=item_id,
                    ticket=ticket,
                    phase=phase,
                    bundle=bundle,
                )
            action(root, ledger, "finish", id=item_id, ticket=ticket)
        except Exception as exc:
            try:
                action(
                    root,
                    ledger,
                    "abort",
                    id=item_id,
                    ticket=ticket,
                    reason="executor/check failed: " + type(exc).__name__,
                )
            except (ValueError, OSError):
                pass  # A stop or failed step already revoked ownership; never revive it.
    return preflight(root, ledger)


def preflight(root, ledger):
    ledger = outside(root, ledger)
    with locked(ledger):
        state = read_state(root, ledger)
        result = refresh(root, state)
        save(ledger, state, replace=True)
        return result
