# Hermes TaskWatch

**Keep unfinished agent commitments from disappearing between sessions.**

Agent work can span multiple conversations, tool calls, and restarts. A draft gets
written, a tool fails, or a task pauses for input. The conversation moves on, while
the original commitment still has unfinished steps.

Hermes TaskWatch gives those commitments a persistent record outside the current
chat. It helps track situations such as:

- **Work that looks finished but is not delivered:** a report exists, but still
  needs verification or the final handoff to the user.
- **Interrupted execution:** a tool failure or ended session leaves a task partly
  complete, with a specific next step still outstanding.
- **Waiting or blocked work:** a commitment depends on user input or an external
  condition and needs review before anything resumes.
- **Unreconciled completion:** the work is done, but its closeout issue still needs
  to be updated and the remote result checked.

The supplied capture instructions tell Hermes to record accepted, unfinished
work with its owner, original source session, what remains, and the next action.
That gives a later session a concrete starting point for checking the original
request and continuing within its approved scope. Explicitly canceled, parked,
or snoozed items stay out of recovery selection.

TaskWatch works locally by default: no Linear account or other task tracker is
required. It nominates at most one unfinished commitment for your Hermes review
job. Hermes then verifies current authorization and task state before acting.
If there is no active recovery work, the preflight lets the scheduled job skip
the model call. Linear synchronization is an optional integration; when enabled,
pending issue updates must be reconciled before recovery.

Capture depends on the agent following the supplied instructions; this release
does not automatically discover forgotten promises by scanning old conversations.
The repo provides the tracking code, an offline demo, and integration instructions
for building that follow-through into your own setup.

Built from a working Hermes commitment-tracking workflow.
This is an independent community project, not an official Nous Research product.

## Try it in 30 seconds

Python 3.11 or later. From this repository, run:

```console
python -m hermes_closeout.demo
```

No installation, accounts, API keys, or model calls needed. The default demo uses
fictional data in a temporary directory, entirely locally:

```text
1. Empty morning: {"wakeAgent": false}
2. Capture replay: 1 commitment, revision 1
3. Local review: no external tracker or sync receipt required
4. Recovery nominee: Deliver the sample report (authorization still required)
5. Demo closeout recorded: {"wakeAgent": false}
Temporary demo data removed on exit. No live agent or service was contacted.
```

To explore optional Linear synchronization, run
`python -m hermes_closeout.demo --linear`. That demo simulates external readback;
it makes no Linear requests. Both demos simulate task completion, not execution
or verification of a real report.

## What it does

- **Persists accepted commitments:** owner, source session, unresolved work, next action, and revision.
- **Deduplicates exact capture:** replaying the same stable ID does not create another task or reopen canceled work.
- **Nominates one recovery item locally:** no remote tracker or receipt required; waiting and blocked items are review-only.
- **Optionally plans Linear synchronization:** create, update, or close actions with exact identity markers and bounded creation batches.
- **Checks optional sync receipts:** stale revisions, changed issue identities, and mismatched managed fields are rejected; outstanding sync blocks recovery in Linear mode.
- **Skips empty mornings:** its read-only preflight emits Hermes's `wakeAgent` protocol without calling a model.

```mermaid
flowchart LR
    A[Accepted commitment] --> B[Local ledger]
    B --> C[Deterministic preflight]
    C -->|Nothing pending| D[Skip agent]
    C -->|Work or error| E[Hermes review]
    E -->|Local mode| G[Verify original authorization]
    E -->|Linear enabled| F[Sync and verify Linear]
    F --> G[Verify original authorization]
    G --> H[Recover at most one item]
    H --> B
```

**The package supplies the ledger and gates.** Your Hermes agent retrieves the
original request, verifies permission, and executes the task. If you enable Linear,
your configured Linear tools perform external synchronization. This release includes the integration
instructions; it does not include a Linear API client, conversation scanner,
scheduler installer, or autonomous task runner. A local receipt cannot prove that
a remote read actually occurred.

## Start a ledger

Optionally install the command with `python -m pip install .`. Runtime dependencies:
Python's standard library only. All commands below also work directly from the checkout.

```console
python -m hermes_closeout --ledger state/closeout.json init
python -m hermes_closeout --ledger state/closeout.json add --stable-id "demo:session-001:report" --summary "Deliver report" --why-unresolved "Verification and delivery remain" --next-action "Check the report against acceptance criteria" --owner "demo" --source-session "fictional-session-001"
python -m hermes_closeout --ledger state/closeout.json list
python -m hermes_closeout --ledger state/closeout.json recovery
python -m hermes_closeout --ledger state/closeout.json preflight
```

No target file is needed for this local workflow. `recovery` returns a candidate
to review; it does not execute the task. Both `state/` and `local/` are ignored by Git.

Use `status --stable-id ID --status resolved` only after the outcome is verified
and delivered. Other statuses are `open`, `waiting`, `blocked`, `canceled`,
`parked`, and `snoozed`. Changing status is an explicit operator action;
capture replay alone never reopens an item.

## Optional Linear integration

Supply `--target PATH` to enable Linear synchronization for `preflight` and
`recovery`. The `plan` and `record-sync` commands always require a target:

```console
python -m hermes_closeout --ledger state/closeout.json --target examples/linear-target.json plan
python -m hermes_closeout --ledger state/closeout.json --target examples/linear-target.json preflight
```

`examples/linear-target.json` is fictional. For real use, copy it to
`local/linear-target.json` and supply your team's, project's, and labels' canonical
identifiers as described in [Hermes integration](docs/hermes-integration.md).
Before any live batch, that guide requires checking that the project and every
required issue label are available to the destination team through the job's
actual Linear connection. A label with the same name in another team is not
enough. The offline planner cannot check remote scope or permissions.
The same ledger can start locally and later use Linear; existing active items
will then require sync and readback before recovery.

Use `sync-status` with the same ledger and target to report all pending sync IDs
and counts, including creates deferred by the three-item plan cap. These are local
acknowledgment counts, not evidence that an issue is absent from Linear.

Existing Linear commands and schedules keep working with their target configured.
A ledger with any recorded Linear issue refuses target-free recovery, even when
the issue is closed or snoozed. Removing configuration must not bypass outstanding
sync. To use local-only tracking separately, initialize a new local ledger; this
release does not detach existing issues or provide an automatic migration off Linear.
Other external trackers are not yet supported.

## Connect to Hermes

Follow the [integration guide](docs/hermes-integration.md). It includes local-only
setup, capture rules, a morning recovery prompt, and optional Linear readback.

Hermes supports script gates that skip the agent when they emit
`{"wakeAgent": false}`. This project uses that existing interface; it does not
modify Hermes. See the [official scheduled-task documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/#skipping-the-agent-entirely-wakeagent).

## Reliability and limits

Writes use a process lock and atomic replacement. Unknown or malformed state
wakes the agent with an error instead of silently declaring the queue empty.
See [design and trust boundaries](docs/design.md) for the state model and
[test coverage](docs/testing.md) for what is verified.

This is an early extraction. Both offline flows are runnable; live Hermes execution
and optional Linear integration need validation in the installer's environment. Notifications,
retry history, authorization checks, and execution ownership are enforced by the
integration workflow, not by a hidden background service.

## Development

The project and repository are named **Hermes TaskWatch**. The Python distribution
and command remain `hermes-closeout`, and the module remains `hermes_closeout`,
so existing integrations keep working. Ledger formats, environment variables,
and Linear identity markers are unchanged by the branding update.

```console
python -m unittest discover -s tests -v
python -m hermes_closeout.demo
python -m hermes_closeout.demo --linear
```

CI is configured for Python 3.11 and 3.14 on Linux and Windows. A configured
matrix is not evidence those jobs have run. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Origin and license

The original workflow combined source-time commitment capture, a persistent
ledger, a Linear closeout queue, and a morning recovery agent. This extraction
keeps its exact-ID tracking, status model, bounded aging, sync gates, and
empty-morning preflight. It removes machine-specific configuration and adds
stronger local validation and write protection. See [provenance](docs/provenance.md).

[MIT license](LICENSE).
