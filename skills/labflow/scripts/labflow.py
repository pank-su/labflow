#!/usr/bin/env python3
"""Local Labflow state CLI. No network, commands from data, or automatic submission."""

import argparse
import json
from pathlib import Path
import sys
import lf_sources
import lf_candidate
import lf_batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("sources-seal", "sources-check"):
        p = sub.add_parser(command)
        p.add_argument("--root", type=Path, required=True)
        if command == "sources-seal":
            p.add_argument("--spec", required=True)
            p.add_argument("--output", required=True)
        else:
            p.add_argument("--map", required=True)
            p.add_argument("--requirements", nargs="+", required=True)
    for command in ("freeze", "verify", "review"):
        p = sub.add_parser(command)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--registry", type=Path, required=True)
        if command == "freeze":
            p.add_argument("--contract", required=True)
        else:
            p.add_argument("--candidate", required=True)
            if command == "verify":
                p.add_argument("--approved", action="store_true")
            else:
                p.add_argument("--slot", required=True)
                p.add_argument("--reviewer-id", required=True)
                p.add_argument("--bundle", type=Path, required=True)
    for command in (
        "batch-init",
        "batch-preflight",
        "batch-begin",
        "batch-step",
        "batch-finish",
        "batch-deliver",
        "batch-stop",
        "batch-resume",
        "batch-bind",
        "batch-retry",
        "batch-skip",
        "batch-permit",
        "batch-abort",
    ):
        p = sub.add_parser(command)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--ledger", type=Path, required=True)
        if command == "batch-init":
            p.add_argument("--spec", required=True)
        elif command not in ("batch-preflight", "batch-stop", "batch-resume"):
            p.add_argument("--id", required=True)
            if command in (
                "batch-step",
                "batch-finish",
                "batch-bind",
                "batch-permit",
                "batch-abort",
            ):
                p.add_argument("--ticket", required=True)
            if command == "batch-permit":
                p.add_argument("--phase", required=True)
            if command == "batch-step":
                p.add_argument("--phase", required=True)
                p.add_argument("--bundle", type=Path, required=True)
            if command == "batch-bind":
                p.add_argument("--registry", type=Path, required=True)
                p.add_argument("--candidate", required=True)
            if command in ("batch-skip", "batch-abort"):
                p.add_argument("--reason", required=True)
            if command == "batch-deliver":
                p.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "sources-seal":
            result = lf_sources.seal(args.root, args.spec, args.output)
        elif args.command == "sources-check":
            result = lf_sources.check(args.root, args.map, args.requirements)
        elif args.command == "freeze":
            result = lf_candidate.freeze(args.root, args.registry, args.contract)
        elif args.command == "review":
            result = lf_candidate.attest(
                args.root,
                args.registry,
                args.candidate,
                args.slot,
                args.reviewer_id,
                args.bundle,
            )
        elif args.command == "batch-init":
            result = lf_batch.initialize(args.root, args.ledger, args.spec)
        elif args.command == "batch-preflight":
            result = lf_batch.preflight(args.root, args.ledger)
        elif args.command.startswith("batch-"):
            options = {
                key: value
                for key, value in vars(args).items()
                if key not in ("root", "ledger", "command")
            }
            result = lf_batch.action(
                args.root, args.ledger, args.command.removeprefix("batch-"), **options
            )
        else:
            lf_candidate.verify(args.root, args.registry, args.candidate, args.approved)
            result = {
                "candidate": args.candidate,
                "state": "approved" if args.approved else "fingerprint_verified",
            }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
