"""Offline fictional walkthrough. No accounts, credentials, or network calls."""

import argparse
import json
import tempfile
from pathlib import Path

from . import core

TARGET = {"team": "DEMO", "project": "fictional-closeout-project",
          "labels": ["agent:demo", "followup-escalation"]}


def run(*, linear=False):
    target = TARGET if linear else None
    with tempfile.TemporaryDirectory(prefix="hermes-closeout-demo-") as directory:
        path = Path(directory) / "ledger.json"
        core.initialize(path)
        print("1. Empty morning:", json.dumps(core.preflight(path, target)))
        fields = dict(stable_id="demo:session-001:delivery", summary="Deliver the sample report",
                      why_unresolved="Draft exists; verification and delivery remain",
                      next_action="Verify the fictional report against its acceptance criteria",
                      owner="demo", source_session="fictional-session-001", priority=3)
        core.add(path, **fields)
        core.add(path, **fields)
        print("2. Capture replay:", len(core.load(path)["candidates"]), "commitment, revision 1")
        if linear:
            plan = core.plan_sync(core.load(path), target)
            print("3. Sync plan:", len(plan["create"]), "create; recovery waits for readback")
            print("   DEMO ONLY: simulating an external readback; no Linear request is made.")
            action = plan["create"][0]
            receipt = {"stable_id": action["stable_id"], "revision": action["revision"],
                       "issue_id": "fictional-issue-001", "issue_url": "https://example.com/issues/001",
                       "payload": action["payload"]}
            core.record_sync(path, target, receipt)
        else:
            print("3. Local review: no external tracker or sync receipt required")
        selected = core.recovery(core.load(path), target)
        print("4. Recovery nominee:", selected["candidate"]["summary"], "(authorization still required)")
        core.set_status(path, fields["stable_id"], "resolved")
        if linear:
            action = core.plan_sync(core.load(path), target)["close"][0]
            receipt.update(revision=action["revision"], payload=action["payload"])
            core.record_sync(path, target, receipt)
        print("5. Demo closeout recorded:", json.dumps(core.preflight(path, target)))
        print("Temporary demo data removed on exit. No live agent or service was contacted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linear", action="store_true", help="Demonstrate optional Linear sync with simulated receipts")
    run(linear=parser.parse_args().linear)
