# Local release validation — 2026-10-06

## Local-first update — v0.2.0

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
