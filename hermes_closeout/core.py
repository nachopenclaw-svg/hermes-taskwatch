"""Portable commitment ledger and morning gate for Hermes Agent.

No network, model calls, or task execution. Integrators own external readback
and authorization. See docs/design.md for the protocol and trust boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ACTIVE = {"open", "waiting", "blocked"}
TERMINAL = {"resolved": "Done", "canceled": "Canceled", "parked": "Canceled"}
STATUSES = ACTIVE | set(TERMINAL) | {"snoozed"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")


def now_utc():
    return datetime.now(timezone.utc)


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("required text is missing")
    return value.strip()


def _timestamp(value):
    stamp = datetime.fromisoformat(_text(value))
    if stamp.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return stamp


def validate_target(target):
    if not isinstance(target, dict) or set(target) != {"team", "project", "labels"}:
        raise ValueError("target requires team, project, and labels")
    _text(target["team"])
    _text(target["project"])
    labels = target["labels"]
    if not isinstance(labels, list) or not labels:
        raise ValueError("target labels must be a nonempty list")
    for label in labels:
        _text(label)
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate target labels")


def canonical_target(target):
    validate_target(target)
    return {**target, "labels": sorted(target["labels"])}


def validate(ledger):
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1:
        raise ValueError("unsupported ledger schema")
    _timestamp(ledger.get("updated_at"))
    candidates = ledger.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    seen = set()
    issue_ids = set()
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("candidate must be an object")
        sid = item.get("stable_id")
        if not isinstance(sid, str) or not ID_PATTERN.fullmatch(sid) or sid in seen:
            raise ValueError("invalid or duplicate stable ID")
        seen.add(sid)
        if item.get("status") not in STATUSES:
            raise ValueError("invalid status")
        for key in ("summary", "why_unresolved", "next_action", "owner"):
            _text(item.get(key))
        source = item.get("source")
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        _text(source.get("session_id"))
        if type(item.get("priority")) is not int or item["priority"] not in {1, 2, 3, 4}:
            raise ValueError("priority must be 1 through 4")
        if type(item.get("revision")) is not int or item["revision"] < 1:
            raise ValueError("revision must be a positive integer")
        _timestamp(item.get("first_seen_at"))
        _timestamp(item.get("last_changed_at"))
        sync = item.get("linear")
        if not isinstance(sync, dict):
            raise ValueError("linear must be an object")
        revision = sync.get("synced_revision")
        if type(revision) is not int or not 0 <= revision <= item["revision"]:
            raise ValueError("invalid synchronized revision")
        if sync.get("issue_id") is not None:
            _text(sync["issue_id"])
            if sync["issue_id"] in issue_ids:
                raise ValueError("duplicate issue identity")
            issue_ids.add(sync["issue_id"])
            url = urlparse(_text(sync.get("issue_url")))
            if url.scheme != "https" or not url.netloc:
                raise ValueError("issue URL must be absolute HTTPS")
            validate_target(sync.get("target"))
            _timestamp(sync.get("synced_at"))
            if sync.get("synced_status") not in {"Todo", "Done", "Canceled"}:
                raise ValueError("invalid synchronized status")
        elif revision != 0 or sync.get("synced_status") is not None:
            raise ValueError("synchronized record has no issue identity")


def load(path):
    ledger = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(ledger)
    return ledger


@contextmanager
def writer_lock(path):
    """Single writer, fail closed on contention. Never auto-break stale locks."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("ledger locked; verify the writer has stopped before removing its lock") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def _save(path, ledger):
    validate(ledger)
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def initialize(path):
    with writer_lock(path):
        if Path(path).exists():
            return load(path)
        ledger = {"schema_version": 1, "updated_at": now_utc().isoformat(), "candidates": []}
        _save(path, ledger)
        return ledger


def _find(ledger, stable_id):
    for item in ledger["candidates"]:
        if item["stable_id"] == stable_id:
            return item
    raise ValueError("unknown stable ID")


def add(path, *, stable_id, summary, why_unresolved, next_action, owner, source_session, priority=3):
    """Capture/update an exact commitment. Replaying capture never reopens it."""
    if not isinstance(stable_id, str) or not ID_PATTERN.fullmatch(stable_id):
        raise ValueError("invalid stable ID")
    material = {"summary": _text(summary), "why_unresolved": _text(why_unresolved),
                "next_action": _text(next_action), "owner": _text(owner),
                "priority": priority, "source": {"session_id": _text(source_session)}}
    with writer_lock(path):
        ledger = load(path)
        stamp = now_utc().isoformat()
        item = next((x for x in ledger["candidates"] if x["stable_id"] == stable_id), None)
        if item is None:
            item = {"stable_id": stable_id, **material, "status": "open", "revision": 1,
                    "first_seen_at": stamp, "last_changed_at": stamp,
                    "linear": {"issue_id": None, "issue_url": None, "synced_revision": 0,
                               "synced_status": None, "synced_at": None}}
            ledger["candidates"].append(item)
        else:
            if item["owner"] != material["owner"] or item["source"] != material["source"]:
                raise ValueError("owner and source session are immutable")
            if all(item[k] == v for k, v in material.items()):
                return item
            item.update(material)
            item["revision"] += 1
            item["last_changed_at"] = stamp
        ledger["updated_at"] = stamp
        _save(path, ledger)
        return item


def set_status(path, stable_id, status):
    if status not in STATUSES:
        raise ValueError("invalid status")
    with writer_lock(path):
        ledger = load(path)
        item = _find(ledger, stable_id)
        if item["status"] != status:
            item["status"] = status
            item["revision"] += 1
            item["last_changed_at"] = ledger["updated_at"] = now_utc().isoformat()
            _save(path, ledger)
        return item


def marker(stable_id):
    return "<!-- hermes-closeout-id=" + hashlib.sha256(stable_id.encode()).hexdigest() + " -->"


def _rank(item, now):
    days = max(0, (now - _timestamp(item["first_seen_at"])).days)
    return max(1, item["priority"] - days // 7), _timestamp(item["first_seen_at"]), item["stable_id"]


def _action(item, target):
    state = TERMINAL.get(item["status"], "Todo")
    kind = "close" if item["status"] in TERMINAL else ("update" if item["linear"]["issue_id"] else "create")
    description = (f"{marker(item['stable_id'])}\n\n"
                   f"Context: {item['summary']}\n\nWhy unresolved: {item['why_unresolved']}\n\n"
                   f"Next action: {item['next_action']}\n\nOwner: {item['owner']}\n\n"
                   f"Source session: {item['source']['session_id']}\n\n"
                   f"Stable ID: {item['stable_id']}\n\nRevision: {item['revision']}\n")
    return {"action": kind, "stable_id": item["stable_id"], "revision": item["revision"],
            "issue_id": item["linear"]["issue_id"], "exact_marker": marker(item["stable_id"]),
            "payload": {**target, "labels": sorted(target["labels"]),
                        "title": ("[Closeout] " + item["summary"])[:240], "description": description,
                        "priority": item["priority"], "state": state}}


def plan_sync(ledger, target, *, now=None):
    """Read-only plan; up to three creates per invocation, not a daily quota."""
    validate(ledger)
    target = canonical_target(target)
    now = now or now_utc()
    actions = {"create": [], "update": [], "close": []}
    for item in sorted(ledger["candidates"], key=lambda x: _rank(x, now)):
        sync = item["linear"]
        if sync["issue_id"] and canonical_target(sync["target"]) != target:
            raise ValueError("configured target differs from recorded issue target")
        if item["status"] == "snoozed":
            continue
        if item["status"] in TERMINAL and not sync["issue_id"]:
            continue
        state = TERMINAL.get(item["status"], "Todo")
        if sync["synced_revision"] == item["revision"] and sync["synced_status"] == state:
            continue
        action = _action(item, target)
        actions[action["action"]].append(action)
    actions["create"] = actions["create"][:3]
    return actions


def record_sync(path, target, receipt):
    """Check a normalized external readback; this does not perform that readback."""
    target = canonical_target(target)
    with writer_lock(path):
        ledger = load(path)
        item = _find(ledger, receipt["stable_id"])
        if item["status"] == "snoozed":
            raise ValueError("snoozed candidate cannot acknowledge sync")
        if type(receipt["revision"]) is not int or receipt["revision"] != item["revision"]:
            raise ValueError("stale readback revision")
        sync = item["linear"]
        issue_id = _text(receipt["issue_id"])
        issue_url = _text(receipt["issue_url"])
        if sync["issue_id"] and (sync["issue_id"] != issue_id or canonical_target(sync["target"]) != target):
            raise ValueError("issue identity or target changed")
        if urlparse(issue_url).scheme != "https" or not urlparse(issue_url).netloc:
            raise ValueError("issue URL must be absolute HTTPS")
        if receipt["payload"] != _action(item, target)["payload"]:
            raise ValueError("external readback does not match managed payload")
        for other in ledger["candidates"]:
            if other["stable_id"] != item["stable_id"] and other["linear"]["issue_id"] == issue_id:
                raise ValueError("issue already belongs to another candidate")
        item["linear"] = {"issue_id": issue_id, "issue_url": issue_url,
                          "target": target, "synced_revision": item["revision"],
                          "synced_status": receipt["payload"]["state"], "synced_at": now_utc().isoformat()}
        ledger["updated_at"] = now_utc().isoformat()
        _save(path, ledger)
        return item


def recovery(ledger, target, *, now=None):
    """Nominate at most one item; execution and live reconciliation are external."""
    actions = plan_sync(ledger, target, now=now)
    if any(actions.values()):
        return {"candidate": None, "reason": "synchronize and read back outstanding actions first"}
    ready = [x for x in ledger["candidates"] if x["status"] in ACTIVE]
    ranks = {"open": 0, "waiting": 1, "blocked": 2}
    ready.sort(key=lambda x: (ranks[x["status"]], *_rank(x, now or now_utc())))
    if not ready:
        return {"candidate": None, "reason": "no active commitments"}
    item = ready[0]
    return {"candidate": item, "mode": "verify_authorization" if item["status"] == "open" else "review_only",
            "deferred_count": len(ready) - 1}


def preflight(path, target, *, now=None):
    try:
        ledger = load(path)
        actions = plan_sync(ledger, target, now=now)
        selected = recovery(ledger, target, now=now)
    except (OSError, ValueError, TypeError, KeyError):
        return {"wakeAgent": True, "context": {"status": "error",
                "error": "Closeout state or configuration could not be validated. Do not execute recovery."}}
    if not any(actions.values()) and selected["candidate"] is None:
        return {"wakeAgent": False}
    return {"wakeAgent": True, "context": {"status": "ready", "actions": actions, "recovery": selected}}
