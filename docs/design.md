# Design and trust boundaries

## Separation of responsibilities

The JSON ledger owns commitment state. Linear is an external projection. The
Python package plans and validates; Hermes retrieves source authorization and
performs work. Nothing in a generated plan or issue grants permission to act.

The public package was extracted from an existing personal workflow. It retains
the core policy while making previously implicit boundaries visible. It does
not promise to infer every forgotten task from conversations: capture depends
on the agent following the capture instructions.

## Record model

Schema version 1 contains `updated_at` and a `candidates` array. Each candidate has:

| Field | Contract |
|---|---|
| `stable_id` | Unique lowercase letters/digits/`.`/`_`/`:`/`-`, 3–128 characters; source-derived |
| `owner`, `source.session_id` | Nonempty and immutable through capture updates |
| `summary`, `why_unresolved`, `next_action` | Nonempty task data |
| `status` | `open`, `waiting`, `blocked`, `resolved`, `canceled`, `parked`, or `snoozed` |
| `priority` | Integer 1 (urgent) through 4 (low) |
| `revision` | Increments on a material capture or status change |
| `first_seen_at`, `last_changed_at` | Timezone-aware ISO timestamps |
| `linear` | Issue identity, exact target binding, acknowledged revision/status/time |

Only explicit `status` changes reopen terminal items. Snoozing has no implicit
expiry. An unsynced terminal item produces no remote create; a previously synced
terminal item generates a closure. Resolved maps to Done; canceled and parked map
to Canceled. Snoozed items produce neither sync actions nor recovery nominations;
their existing remote issue is left as-is.

Ranking improves effective priority once per seven unresolved days, bounded at
urgent. The original priority field is preserved in the remote payload. Open
items rank ahead of waiting, then blocked items for recovery. Ties use first-seen
time and exact ID. A plan includes at most three creates and all necessary
updates/closures; it is not a persistent daily rate limiter.

## Persistence

Each local mutation holds an exclusive lock adjacent to the resolved ledger
path. Contending writers fail instead of silently overwriting another process.
Writes validate first, flush and fsync a temporary file, then atomically replace
the ledger. A failed replacement leaves the previous ledger intact. Exact capture
replay does not write at all. Read-only commands never initialize missing state.

Use a local filesystem and one canonical path. Cloud-sync folders, network shares,
hard-linked aliases, and multiple machines writing a shared file are not supported
coordination mechanisms. Keep operational state on a local disk even if source
code is synced. The lock is not a distributed lock or a guarantee against a power
failure. A killed process can leave a lock behind: verify that no writer remains,
back up and validate the ledger, then manually remove only that stale lock.

## External sync protocol

Markers use SHA-256 of the stable ID under the `hermes-closeout-id` namespace.
The adapter must search all remote pages for this exact marker before creating.
The package cannot see search results and cannot guarantee remote uniqueness.

`record-sync` accepts a normalized readback from a trusted adapter. It checks the
current revision, all managed fields, original issue identity, target binding,
and that the same issue has not been assigned to another candidate. It does not
make a network request, cryptographically authenticate receipts, or prove that
someone actually fetched Linear. The offline demo deliberately uses mock receipts.

The caller must serialize the complete remote search/write/readback sequence.
The file lock is held only for local mutation, not across remote operations.
Remote deduplication, tool authentication, permission to send private task text
to Linear, and protection from prompt injection belong to the integration.

## Preflight and recovery

Preflight reads one validated ledger snapshot and evaluates both gates. It skips
the model only when no synchronization and no active recovery candidate remain.
Missing or malformed state produces a bounded diagnostic wake; it never fabricates
an empty ledger. Waiting/blocked work can still wake the agent for review; suppressing
unchanged notifications is the agent workflow's responsibility.

Any outstanding sync action blocks recovery nomination. Once reconciled, the
selector nominates at most one item. That is a nomination, not a claim, lease,
authorization, or executed action. A live agent must reconcile source consent,
current issue state, latest revision, and exclusive execution ownership again.

Attempts and their evidence stay in the canonical task checkpoint referenced by
the candidate. This release does not introduce a second attempt database or
enforce retry counts. The supplied prompt makes this obligation explicit.
