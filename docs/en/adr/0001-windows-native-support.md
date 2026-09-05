# Native Windows support: dual stdlib file-lock backends

[中文](../../zh/adr/0001-windows-native-support.md) | **English**

Through v0.2.0, Windows was an explicit Non-Goal (README/SKILL.md said "use WSL"),
because the concurrent state control depended on POSIX `fcntl.flock`. After users asked
for native support, we chose to select a stdlib lock backend per platform — POSIX keeps
`fcntl`, Windows uses `msvcrt.locking` (about 20 lines, zero new dependencies); the
semantics are the same "single-machine blocking exclusive lock", matching the tool's
single-machine deployment model.

## Considered Options

- **The third-party portalocker library**: unified API, but it breaks the
  "only dependency is pyyaml" minimal positioning, and the offline-install docs would
  need extra materials;
- **Rebuild the lock with atomic mkdir and drop file locks entirely**: a single code
  path, but it touches the concurrency core (the transaction mutual exclusion and the
  stale-reclamation reasoning would all be rewritten) — the highest risk and testing
  cost;
- **Stay WSL-only**: doesn't meet the need.

## Consequences

- Windows CI (`windows-latest`) joined the matrix as the regression backstop; local
  development still only requires macOS/Linux.
- `msvcrt.locking(LK_LOCK)` throws after failing to grab the lock for ~10 seconds
  (`fcntl` blocks indefinitely); this is mapped to a `StateError` with a retry hint —
  the only semantic difference between the two backends.
- The bash idioms in the docs (`nohup … &`, `command -v`) gained PowerShell equivalents
  in SKILL.md.
