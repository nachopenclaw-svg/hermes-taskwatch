# Hermes integration

The offline demos are complete without Hermes. A live integration needs a Hermes
installation with script-gated cron and access to the source sessions for captured
work. Local-only operation is the default and needs no task tracker. If you choose
Linear, also provide tools that can search, update, and read back its issues.
This guide is a setup recipe, not a claim that a schedule or connection is installed.

## 1. Install and choose local paths

Install this checkout into the Python environment your gate will use:

```console
python -m pip install .
```

Choose an absolute path for a private ledger. Initialize
the ledger with `python -m hermes_closeout --ledger ABSOLUTE_LEDGER_PATH init`.
Read commands intentionally do not create a missing ledger.

Run `python -m hermes_closeout --ledger ABSOLUTE_LEDGER_PATH preflight` without
`--target` for local review. Empty state returns `{"wakeAgent": false}`. After
capture, `recovery` can nominate one commitment without an external sync receipt.
This nomination is not permission to execute it.

The ledger can contain private task text;
keep it outside public source control and restrict filesystem access appropriately.

## 2. Add capture instructions to your agent

Adapt [the capture snippet](../examples/capture-instructions.md) to your absolute
paths and chosen owner. Merge it into your existing agent instructions instead
of replacing them. Capture explicit accepted work at checkpoints when some
required work remains. An example source ID is `hermes:SESSION:COMMITMENT`;
encode it into the accepted lowercase ID alphabet or hash stable source IDs.
The original session pointer must remain retrievable separately.

Use a stable ID per commitment, not per tool call or title. Updating an existing
ID preserves the owner and original source session. Keep failed approaches and
attempt history in the canonical task checkpoint; link it in `why_unresolved`
and record the next step in `next_action`.

## 3. Optional: synchronize with Linear through your existing tools

**Skip this section for local-only operation.** No target file, API key, fake
issue, or simulated receipt is needed for local recovery.

Copy `examples/linear-target.json` to your chosen private config path. `team`
and `project` must be the canonical identifiers your Linear tools return; use
IDs where supported. `labels` must use the same canonical representation in
every readback. Choose a dedicated closeout project and ownership labels.
The planner treats these as opaque, exact values and does not resolve names.
Keep account credentials in your existing Linear tool configuration; this package
neither reads nor stores credentials.

Pass `--target ABSOLUTE_TARGET_PATH` to `plan`, `record-sync`, `preflight`, and
`recovery`. Supplying a target enables Linear mode; all sync safeguards remain.
An explicitly configured missing, malformed, or null target produces an error,
never a fallback to local mode. Active local commitments will require synchronization
if you later enable Linear on their ledger.

Once any candidate has a recorded Linear issue, omitting the target fails closed,
including for closed or snoozed candidates. Existing Linear schedules must keep
`HERMES_CLOSEOUT_TARGET` set. This release does not detach issue bindings; initialize
a separate ledger for new local-only work instead of deleting sync metadata.

`plan` prints an object with `create`, `update`, and `close` arrays. It performs
no network requests. Use one synchronization owner; the local lock covers only
local writes, not the entire remote transaction.

For each planned action:

1. Search all result pages for `exact_marker`. Zero matches permits a create;
   one match can be reused only after verifying ownership and target identity;
   multiple matches are an error. Never match an issue by similar title.
2. For updates/closures, verify the recorded issue ID, marker, project, team,
   and required label set before any remote mutation. Do not take over an issue
   whose ownership drifted. A terminal item with no recorded issue is not created.
3. Apply the planned `payload`. The adapter maps canonical team/project/label
   identifiers to the actual Linear tool schema.
4. Fetch the exact issue again. Normalize its actual returned fields into a
   receipt file. Do not fabricate a receipt by copying the plan: that would
   validate your intention rather than the remote result.
5. Run `record-sync --receipt ABSOLUTE_RECEIPT_PATH` with the same `--ledger`
   and `--target`. A rejected receipt leaves local state unchanged. If the
   local revision changed during the remote call, obtain a fresh plan and
   reconcile the same remote issue before continuing.

Receipt shape (all values must come from the current action and fresh readback):

```json
{
  "stable_id": "demo:session-001:report",
  "revision": 1,
  "issue_id": "returned-issue-id",
  "issue_url": "https://example.com/actual-returned-issue-url",
  "payload": {
    "team": "returned-canonical-team",
    "project": "returned-canonical-project",
    "labels": ["returned-label-a", "returned-label-b"],
    "title": "actual returned title",
    "description": "actual returned description including exact marker",
    "priority": 3,
    "state": "Todo"
  }
}
```

Sort receipt labels lexicographically; no extra labels are allowed in the
managed set. Payload fields must match exactly, including description whitespace.
`stable_id` and `revision` refer to the action whose readback you verified.

Each plan contains at most three creates. This is a **per-plan cap**, not a daily
quota. Run one scheduled batch if you want the original bounded morning cadence.
Repeated plans can nominate another batch after successful sync.

## 4. Wire the morning gate

Use [examples/hermes_gate.py](../examples/hermes_gate.py) as the pre-check script.
Set its environment variables in the scheduler's execution environment:

| Variable | Value |
|---|---|
| `HERMES_CLOSEOUT_LEDGER` | Absolute ledger path |
| `HERMES_CLOSEOUT_TARGET` | Optional absolute Linear target JSON path; leave unset for local-only use |

Unset the optional variable entirely for local mode; an empty string is an invalid
configured path. A ready preflight includes `context.mode` (`local` or `linear`)
and empty action arrays in local mode. An empty queue emits only `{"wakeAgent": false}`.

The Python environment executing the script must have this package installed.
Test the script manually with that same environment. Empty validated state must
print exactly `{"wakeAgent": false}`; a missing ledger setting or invalid configured
target must wake with an error. Do not treat a diagnostic wake as permission to resume work.

Ask Hermes to create **one** morning job in your chosen timezone using its
supported scheduling interface, that script, and the adapted
[morning prompt](../examples/morning-prompt.md). Include the absolute ledger,
Python executable, source-retrieval instructions, and target only if using Linear
in the prompt. Choose the matching local or Linear instructions in that template.
Avoid overlapping manual recovery and scheduled recovery. The package does not
claim or lease tasks on behalf of an executor.

The `script`/`wakeAgent` contract is documented in
[Hermes scheduled tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/#skipping-the-agent-entirely-wakeagent).
Verify the contract with your installed release and its cron tools. This repo
does not pin or rewrite your model, provider, notifications, or scheduler files.

## 5. Validate before enabling unattended work

Use a temporary ledger and fictional source session. In local mode, verify a complete
capture → nomination → authorized completion → local resolution cycle. For Linear,
also use a dedicated test project and verify sync, readback, and remote closure.
Then check replay, cancellation, changed revision, malformed state, and an empty
morning. In Linear mode also check duplicate remote markers and missing target
configuration. Confirm the schedule's delivery behavior
and source lookup, rather than relying only on a successful command exit.

Do not import a private production ledger as test data. Existing private ledgers
need a deliberate migration: the public format requires source IDs and verified
target bindings, and uses a new marker namespace.
