"""Example Hermes pre-check. Install the package in this script's Python first."""

import json
import os
from pathlib import Path

try:
    from hermes_closeout.core import preflight, validate_target

    ledger = Path(os.environ["HERMES_CLOSEOUT_LEDGER"])
    if not ledger.is_absolute():
        raise ValueError("absolute paths required")
    target = None
    if "HERMES_CLOSEOUT_TARGET" in os.environ:
        target_path = Path(os.environ["HERMES_CLOSEOUT_TARGET"])
        if not target_path.is_absolute():
            raise ValueError("absolute paths required")
        target = json.loads(target_path.read_text(encoding="utf-8"))
        # An explicitly configured null/invalid target must never select local mode.
        validate_target(target)
    result = preflight(ledger, target)
except (ImportError, OSError, ValueError, TypeError, KeyError):
    result = {"wakeAgent": True, "context": {"status": "error",
              "error": "Closeout gate setup or state is invalid. Do not execute recovery."}}

print(json.dumps(result, sort_keys=True))
