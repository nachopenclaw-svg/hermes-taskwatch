# Local release validation

## Linear setup and queue reporting — v0.2.1 — 2026-10-07

| Check | Result |
|---|---|
| Python 3.14.3, Windows unittest suite | 29 tests passed |
| Local and simulated-Linear demos | Passed from source and installed wheel |
| Wheel build and isolated installation outside checkout | Passed; package metadata and module version are 0.2.1 |
| Installed CLI, six-item status and preflight | Six pending, three planned creates, three deferred; recovery blocked; local mode unchanged |
| Pre-change control | Two new reporting tests failed because v0.2.0 exposed no full-queue summary; passed after implementation |
| Independent code, test, and workflow review | Accepted; no actionable findings |
| Local Markdown links and diff whitespace | Passed |

The target format, ledger schema, and capped `plan` arrays are unchanged. The new
read-only `sync-status` command and additive Linear preflight/recovery fields
count outstanding local acknowledgments; they cannot prove remote absence or
classify remote failures. A stale module version constant was aligned with the
distribution version.

The installer guide and morning prompt now require live destination-team label
checks before writes, evidence-based diagnosis, and stopping on shared setup
failures. This is an adapter workflow requirement, not a new automatic remote
validator. Static scenario review covered wrong-team and unknown labels, batch
stops, uncertain write outcomes, and six-item reporting. Live Hermes/Linear and
model behavior evaluations were not run; no model evaluation harness is configured.
The author’s live labels, ledger, and job were not changed. Remote CI is recorded
separately by GitHub Actions.

## Local-first update — v0.2.0 — 2026-10-06

| Check | Result |
|---|---|
| Python 3.14.3, Windows unittest suite | 27 tests passed |
| Local and simulated-Linear demos | Both passed from source and installed wheel |
| Wheel build and isolated installation | Passed using build isolation |
| Installed CLI and example gate outside checkout | Local empty/active flows and Linear sync gate passed |
| Pre-change control | New local CLI test failed on v0.1.0 because target-free preflight returned an error; passes with this update |
| Independent code, test, and prompt review | Accepted; no actionable findings |
| Local Markdown links and diff whitespace | Passed |

Schema version 1 and existing Linear command arguments are retained. Local mode
does not fabricate sync receipts. Missing configuration on a linked ledger and
explicit invalid target files still block recovery. The existing safeguards for
identity, readback, cancellation, source authorization, and exclusive execution
ownership remain in place.

Live Hermes execution, optional Linear transport, unattended recovery, and model
behavior evaluations were not run. The repository has no configured live model
evaluation harness; prompt review was static. Remote CI results are recorded by
GitHub Actions separately. No private production state or running schedule was changed.

## Initial extraction — v0.1.0

Scope: public extraction v0.1.0, local artifact only.

| Check | Result |
|---|---|
| Python 3.14.3, Windows unittest suite | 22 tests passed |
| Offline fictional walkthrough | Passed from source and installed wheel |
| Wheel build and isolated virtual-environment installation | Passed |
| Installed command outside the checkout | Help and demo passed |
| Installed example gate | Empty state skipped; missing setup produced diagnostic wake |
| Independent review | Accepted after identity, URL, label-order, and packaging fixes |
| Local Markdown links | No broken local targets found |
| Distribution-source privacy scan | No matches for known private machine/account identifiers or tested credential patterns |

The privacy scan is a targeted check, not proof against every possible secret
format. The package was built from source code and fictional examples; production
state and conversations were not included.

Review regression probes first demonstrated duplicate persisted issue identities
and relative HTTPS URLs passing validation. After correction, both are rejected
without modifying the ledger. Reordered target labels now remain equivalent.
An independently specified full payload assertion also protects marker, owner,
source, next action, and managed fields from being omitted together by planner
and receipt code.

Not run: live Hermes/Linear end-to-end integration, unattended recovery/model
evaluation, and the remote GitHub Actions matrix. Do not treat this local report
as evidence of a deployed schedule, real remote delivery, or Linux validation.
