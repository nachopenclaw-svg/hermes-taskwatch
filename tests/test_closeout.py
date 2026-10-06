import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from hermes_closeout import core

ROOT = Path(__file__).resolve().parents[1]
TARGET = {"team": "TEST", "project": "test-project", "labels": ["agent:test", "followup-escalation"]}


class CloseoutTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "ledger.json"
        core.initialize(self.path)

    def add(self, sid="test:session:report", **overrides):
        fields = dict(stable_id=sid, summary="Deliver report", why_unresolved="Delivery remains",
                      next_action="Check report then deliver", owner="test", source_session="test-session", priority=3)
        fields.update(overrides)
        return core.add(self.path, **fields)

    def receipt(self, sid="test:session:report", kind="create"):
        actions = core.plan_sync(core.load(self.path), TARGET)[kind]
        action = next(x for x in actions if x["stable_id"] == sid)
        return dict(stable_id=sid, revision=action["revision"], issue_id="issue-" + sid,
                    issue_url="https://example.com/issue/1", payload=action["payload"])

    def test_empty_gate_is_silent_and_read_only(self):
        before = self.path.read_bytes()
        self.assertEqual(core.preflight(self.path, TARGET), {"wakeAgent": False})
        self.assertEqual(self.path.read_bytes(), before)

    def test_capture_replay_is_byte_identical(self):
        self.add()
        before = self.path.read_bytes()
        self.add()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(core.load(self.path)["candidates"]), 1)

    def test_material_change_increments_revision_without_changing_first_seen(self):
        first = self.add()
        changed = self.add(next_action="Deliver verified report")
        self.assertEqual(changed["revision"], 2)
        self.assertEqual(changed["first_seen_at"], first["first_seen_at"])

    def test_owner_and_source_cannot_be_reassigned(self):
        self.add()
        before = self.path.read_bytes()
        for fields in ({"owner": "other"}, {"source_session": "other"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.add(**fields)
        self.assertEqual(self.path.read_bytes(), before)

    def test_replay_never_reopens_resolved_canceled_parked_or_snoozed(self):
        self.add()
        for status in ("resolved", "canceled", "parked", "snoozed"):
            core.set_status(self.path, "test:session:report", status)
            self.add()
            ledger = core.load(self.path)
            self.assertEqual(ledger["candidates"][0]["status"], status)
            self.assertIsNone(core.recovery(ledger, TARGET)["candidate"])
            self.assertFalse(any(core.plan_sync(ledger, TARGET).values()))

    def test_missing_or_corrupt_state_wakes_with_bounded_error_without_mutation(self):
        for data in (b"not json private secret", b"[]", b'{"schema_version": 99}',
                     b'{"schema_version":1,"updated_at":"2026-01-01T00:00:00Z","candidates":[42]}'):
            self.path.write_bytes(data)
            payload = core.preflight(self.path, TARGET)
            self.assertTrue(payload["wakeAgent"])
            self.assertEqual(payload["context"]["status"], "error")
            self.assertNotIn("private secret", json.dumps(payload))
            self.assertEqual(self.path.read_bytes(), data)
        self.path.unlink()
        self.assertEqual(core.preflight(self.path, TARGET)["context"]["status"], "error")
        self.assertFalse(self.path.exists())

    def test_invalid_capture_does_not_write(self):
        before = self.path.read_bytes()
        for fields in ({"priority": True}, {"priority": 0}, {"summary": " "},
                       {"source_session": ""}, {"sid": "UPPER ID"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.add(**fields)
            self.assertEqual(self.path.read_bytes(), before)

    def test_duplicate_ids_and_naive_timestamps_are_rejected(self):
        self.add()
        ledger = core.load(self.path)
        duplicate = copy.deepcopy(ledger)
        duplicate["candidates"].append(copy.deepcopy(duplicate["candidates"][0]))
        with self.assertRaises(ValueError):
            core.validate(duplicate)
        ledger["candidates"][0]["first_seen_at"] = "2026-01-01T00:00:00"
        with self.assertRaises(ValueError):
            core.validate(ledger)

    def test_priority_aging_and_three_create_plan_cap(self):
        for sid, priority in (("test:old", 4), ("test:urgent", 1), ("test:medium", 3), ("test:low", 4)):
            self.add(sid, priority=priority)
        ledger = core.load(self.path)
        for item in ledger["candidates"]:
            item["first_seen_at"] = "2026-01-30T00:00:00+00:00"
        ledger["candidates"][0]["first_seen_at"] = "2026-01-01T00:00:00+00:00"
        actions = core.plan_sync(ledger, TARGET, now=datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertEqual([x["stable_id"] for x in actions["create"]], ["test:old", "test:urgent", "test:medium"])

    def test_unsynced_work_cannot_be_nominated(self):
        self.add()
        self.assertIsNone(core.recovery(core.load(self.path), TARGET)["candidate"])
        self.assertTrue(core.preflight(self.path, TARGET)["wakeAgent"])

    def test_planned_payload_preserves_independently_specified_managed_fields(self):
        self.add()
        action = core.plan_sync(core.load(self.path), TARGET)["create"][0]
        expected_marker = "<!-- hermes-closeout-id=4ae8e8e8bf8cc40bb6c19dc998107d6c84968a4e289c18527b0e18ea2bb59382 -->"
        self.assertEqual(action, {
            "action": "create", "stable_id": "test:session:report", "revision": 1,
            "issue_id": None, "exact_marker": expected_marker,
            "payload": {
                "team": "TEST", "project": "test-project", "labels": ["agent:test", "followup-escalation"],
                "title": "[Closeout] Deliver report", "priority": 3, "state": "Todo",
                "description": expected_marker + "\n\nContext: Deliver report\n\nWhy unresolved: Delivery remains\n\n"
                "Next action: Check report then deliver\n\nOwner: test\n\nSource session: test-session\n\n"
                "Stable ID: test:session:report\n\nRevision: 1\n"}})

    def test_corrupt_persisted_issue_identity_or_url_blocks_preflight(self):
        for sid in ("test:first", "test:second"):
            self.add(sid)
            core.record_sync(self.path, TARGET, self.receipt(sid))
        original = core.load(self.path)
        for defect in ("duplicate", "relative_url"):
            ledger = copy.deepcopy(original)
            if defect == "duplicate":
                ledger["candidates"][1]["linear"]["issue_id"] = ledger["candidates"][0]["linear"]["issue_id"]
            else:
                ledger["candidates"][0]["linear"]["issue_url"] = "https:relative"
            self.path.write_text(json.dumps(ledger), encoding="utf-8")
            before = self.path.read_bytes()
            self.assertEqual(core.preflight(self.path, TARGET)["context"]["status"], "error")
            self.assertEqual(self.path.read_bytes(), before)

    def test_target_label_order_is_not_identity(self):
        self.add()
        core.record_sync(self.path, TARGET, self.receipt())
        reordered = {**TARGET, "labels": list(reversed(TARGET["labels"]))}
        self.assertFalse(any(core.plan_sync(core.load(self.path), reordered).values()))
        self.assertEqual(core.recovery(core.load(self.path), reordered)["candidate"]["stable_id"], "test:session:report")

    def test_exact_sync_enables_one_nominee_and_unsynced_change_blocks_it(self):
        for sid in ("test:first", "test:second"):
            self.add(sid)
            core.record_sync(self.path, TARGET, self.receipt(sid))
        selected = core.recovery(core.load(self.path), TARGET)
        self.assertEqual(selected["candidate"]["stable_id"], "test:first")
        self.assertEqual(selected["deferred_count"], 1)
        self.add("test:second", next_action="Review a new revision")
        self.assertIsNone(core.recovery(core.load(self.path), TARGET)["candidate"])

    def test_waiting_is_review_only_and_open_takes_precedence(self):
        self.add("test:waiting", priority=1)
        core.set_status(self.path, "test:waiting", "waiting")
        core.record_sync(self.path, TARGET, self.receipt("test:waiting"))
        self.assertEqual(core.recovery(core.load(self.path), TARGET)["mode"], "review_only")
        self.add("test:open", priority=4)
        core.record_sync(self.path, TARGET, self.receipt("test:open"))
        self.assertEqual(core.recovery(core.load(self.path), TARGET)["candidate"]["stable_id"], "test:open")

    def test_stale_receipt_and_payload_drift_leave_ledger_unchanged(self):
        self.add()
        receipt = self.receipt()
        for key, value in (("team", "wrong"), ("project", "wrong"), ("labels", ["extra"]),
                           ("state", "Done"), ("description", "missing marker"), ("priority", 1)):
            bad = copy.deepcopy(receipt)
            bad["payload"][key] = value
            before = self.path.read_bytes()
            with self.subTest(key=key), self.assertRaises(ValueError):
                core.record_sync(self.path, TARGET, bad)
            self.assertEqual(self.path.read_bytes(), before)
        self.add(next_action="Changed after remote write")
        with self.assertRaisesRegex(ValueError, "stale"):
            core.record_sync(self.path, TARGET, receipt)

    def test_recorded_issue_cannot_be_rebound_or_shared(self):
        self.add()
        receipt = self.receipt()
        core.record_sync(self.path, TARGET, receipt)
        changed = copy.deepcopy(receipt)
        changed["issue_id"] = "different-issue"
        with self.assertRaises(ValueError):
            core.record_sync(self.path, TARGET, changed)
        self.add("test:other")
        other = self.receipt("test:other")
        other["issue_id"] = receipt["issue_id"]
        with self.assertRaises(ValueError):
            core.record_sync(self.path, TARGET, other)
        bad_target = {**TARGET, "project": "different"}
        with self.assertRaises(ValueError):
            core.plan_sync(core.load(self.path), bad_target)

    def test_terminal_sync_closes_exact_issue_and_restores_silence(self):
        self.add()
        receipt = self.receipt()
        core.record_sync(self.path, TARGET, receipt)
        core.set_status(self.path, "test:session:report", "resolved")
        action = core.plan_sync(core.load(self.path), TARGET)["close"][0]
        self.assertEqual(action["issue_id"], receipt["issue_id"])
        self.assertEqual(action["payload"]["state"], "Done")
        self.assertIsNone(core.recovery(core.load(self.path), TARGET)["candidate"])
        core.record_sync(self.path, TARGET, self.receipt(kind="close"))
        self.assertEqual(core.preflight(self.path, TARGET), {"wakeAgent": False})

    def test_lock_contention_refuses_writer_and_preserves_state(self):
        before = self.path.read_bytes()
        with core.writer_lock(self.path):
            with self.assertRaisesRegex(ValueError, "locked"):
                self.add()
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_atomic_replace_preserves_previous_ledger_and_removes_temp(self):
        before = self.path.read_bytes()
        with patch("hermes_closeout.core.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.add()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_cli_contract_and_missing_target_diagnostic(self):
        command = [sys.executable, "-m", "hermes_closeout", "--ledger", str(self.path)]
        result = subprocess.run(command + ["preflight"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["context"]["status"], "error")
        result = subprocess.run(command + ["--target", str(ROOT / "examples/linear-target.json"), "preflight"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"wakeAgent": False})

    def test_offline_demo_runs_end_to_end(self):
        result = subprocess.run([sys.executable, "-m", "hermes_closeout.demo"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('5. Verified closeout recorded: {"wakeAgent": false}', result.stdout)
        self.assertIn("simulating an external readback", result.stdout)


if __name__ == "__main__":
    unittest.main()
