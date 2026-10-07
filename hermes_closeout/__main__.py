"""Command-line entry point. Global path flags precede the command."""

import argparse
import json
import sys
from pathlib import Path

from . import core


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track unfinished Hermes commitments without model calls.")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--target", type=Path,
                        help="Enable Linear sync with this target JSON; omit for local recovery. Required for plan/sync-status/record-sync and linked ledgers.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "list", "plan", "sync-status", "recovery", "preflight"):
        commands.add_parser(name)
    add = commands.add_parser("add")
    for name in ("stable-id", "summary", "why-unresolved", "next-action", "owner", "source-session"):
        add.add_argument("--" + name, required=True)
    add.add_argument("--priority", type=int, choices=(1, 2, 3, 4), default=3)
    status = commands.add_parser("status")
    status.add_argument("--stable-id", required=True)
    status.add_argument("--status", choices=sorted(core.STATUSES), required=True)
    sync = commands.add_parser("record-sync")
    sync.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        target = None
        if args.command in {"plan", "sync-status", "recovery", "preflight", "record-sync"}:
            if args.target is None and args.command in {"plan", "sync-status", "record-sync"}:
                raise ValueError("--target is required")
            if args.target is not None:
                target = json.loads(args.target.read_text(encoding="utf-8"))
                core.validate_target(target)
        if args.command == "init":
            result = core.initialize(args.ledger)
        elif args.command == "list":
            result = core.load(args.ledger)
        elif args.command == "add":
            result = core.add(args.ledger, **{k: v for k, v in vars(args).items()
                                             if k not in {"ledger", "target", "command"}})
        elif args.command == "status":
            result = core.set_status(args.ledger, args.stable_id, args.status)
        elif args.command == "record-sync":
            result = core.record_sync(args.ledger, target, json.loads(args.receipt.read_text(encoding="utf-8")))
        elif args.command == "plan":
            result = core.plan_sync(core.load(args.ledger), target)
        elif args.command == "sync-status":
            result = core.sync_status(core.load(args.ledger), target)
        elif args.command == "recovery":
            result = core.recovery(core.load(args.ledger), target)
        else:
            result = core.preflight(args.ledger, target)
    except (OSError, ValueError, TypeError, KeyError):
        if args.command == "preflight":
            result = {"wakeAgent": True, "context": {"status": "error",
                      "error": "Closeout state or configuration could not be validated. Do not execute recovery."}}
        else:
            print("Closeout command failed: check inputs, state, target, and writer lock.", file=sys.stderr)
            return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
