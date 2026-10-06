# Provenance

Hermes TaskWatch packages a custom commitment-tracking workflow
for Hermes Agent. The original components were a ledger manager, a combined
morning preflight, and agent operating instructions. They are custom workflow
code; this repo does not vendor the Hermes Agent runtime.

Retained concepts: accepted-commitment capture, stable IDs, a JSON ledger, revisions,
active/terminal/snoozed statuses, exact SHA-256 markers, Linear projection,
three-create batches, bounded priority aging, one-item recovery selection, and
a quiet empty-morning gate.

Public extraction changes: explicit paths and target settings; required immutable
source/owner identity; stricter input and receipt validation; local writer locking;
explicit initialization; sync-before-recovery; and offline examples/tests.

Version 0.2.0 adds local-only recovery as the default. Linear remains optional;
sync-before-recovery still applies whenever it is enabled. Existing issue bindings
cannot be silently bypassed by removing the target configuration.

No production ledger, conversation transcript, account identifier, credential,
private issue link, machine path, or business record is part of the intended
distribution. Example identities are fictional. Existing private ledger files
are not drop-in compatible because public target bindings and marker names differ.

Hermes Agent is developed by [Nous Research](https://github.com/NousResearch/hermes-agent).
This project relies on its documented script gate interface and remains independent
of its maintainers. The public extraction has its own validation scope; historical
results from the private setup are not presented as release test results.
