# Contributing

Keep changes focused on commitment capture, state integrity, synchronization
contracts, and bounded recovery gates. Use fictional fixtures and temporary
directories. Do not commit personal ledgers, credentials, or real session exports.

Run the unittest suite and both offline demos (default local and `--linear`). Add behavior tests for changed contracts,
including a failure path where relevant. Do not call external services in the
default suite. Document compatibility changes and any schema migration explicitly.

An external adapter must preserve exact identity search, live readback, source
authorization, and single execution ownership. Do not turn a local nomination
into automatic execution without designing and testing those boundaries.
