# Architecture

RunLens captures Linux program executions, normalizes evidence, compares runs,
and identifies meaningful divergence. M0 provides packaging, CLI, and read-only
environment checks only. Python 3.10+; no runtime dependencies.

Planned flow: collector -> raw evidence -> normalizer -> normalized events ->
run storage -> analyzer -> report. Analyzers never parse raw strace output.
Findings and differences must reference evidence IDs. Reports present analysis
without hidden diagnosis logic. Backends remain replaceable.

M1 adds subprocess runner, /proc collector, and JSON storage. M2 adds strace;
M3 versions capsules; M4 compares runs; M5 ranks meaningful divergence.
C++/ptrace begins at M6. Future modules are added when implemented, rather than
populated with empty interfaces now.
