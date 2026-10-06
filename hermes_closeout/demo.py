"""Offline fictional walkthrough. No accounts, credentials, or network calls."""

import json
import tempfile
from pathlib import Path

from . import core

TARGET = {"team": "DEMO", "project": "fictional-closeout-project",
          "labels": ["agent:demo", "followup-escalation"]}


def run():
    with tempfile.TemporaryDirectory(prefix="hermes-closeout-demo-") as directory:
        path = Path(directory) / "ledger.json"
        core.initialize(path)
        print("1. Empty morning:", json.dumps(core.preflight(path, TARGET)))
        fields = dict(stable_id="demo:session-001:delivery", summary="Deliver the sample report",
                      why_unresolved="Draft exists; verification and delivery remain",
                      next_action="Verify the fictional report against its acceptance criteria",
                      owner="demo", source_session="fictional-session-001", priority=3)
        core.add(path, **fields)
        core.add(path, **fields)
        print("2. Capture replay:", len(core.load(path)["candidates"]), "commitment, revision 1")
        plan = core.plan_sync(core.load(path), TARGET)
        print("3. Sync plan:", len(plan["create"]), "create; recovery waits for readback")
        print("   DEMO ONLY: simulating an external readback; no Linear request is made.")
        action = plan["create"][0]
        receipt = {"stable_id": action["stable_id"], "revision": action["revision"],
                   "issue_id": "fictional-issue-001", "issue_url": "https://example.com/issues/001",
                   "payload": action["payload"]}
        core.record_sync(path, TARGET, receipt)
        selected = core.recovery(core.load(path), TARGET)
        print("4. Recovery nominee:", selected["candidate"]["summary"], "(authorization still required)")
        core.set_status(path, fields["stable_id"], "resolved")
        action = core.plan_sync(core.load(path), TARGET)["close"][0]
        receipt.update(revision=action["revision"], payload=action["payload"])
        core.record_sync(path, TARGET, receipt)
        print("5. Verified closeout recorded:", json.dumps(core.preflight(path, TARGET)))
        print("Temporary demo data removed on exit. No live agent or service was contacted.")


if __name__ == "__main__":
    run()
