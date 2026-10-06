# Verification

Run `python -m unittest discover -s tests -v` and `python -m hermes_closeout.demo`.
Tests use temporary directories and fictional records. They never access live
Hermes sessions, credentials, Linear, or your actual ledger.

The suite covers exact replay and immutable source identity; material revisions;
terminal and snoozed exclusions; malformed and missing-state diagnostics; priority
aging and the three-create plan cap; sync-before-recovery; one-item nomination;
review-only waiting; stale and mismatched readbacks; issue rebinding/duplication;
closure and return to silence; writer contention; atomic-replace failure; and the CLI/demo.

Each failure test asserts an observable result, including preservation of the
previous bytes when a mutation is rejected. Remote receipt tests deliberately
mutate identity or managed fields to exercise rejection. Demo receipts are
synthetic and are not evidence of live integration.

GitHub Actions defines a Windows/Linux matrix on Python 3.11/3.14. Local checks
on the author's current platform do not establish that the other matrix entries
have passed. No live scheduler, Linear transport, model behavior evaluation, or
unattended execution is covered by these deterministic tests. Validate the
workflow in a dedicated test project before enabling recovery.
