# Architecture

Target: Ubuntu 22.04, Python 3.10+. Runtime: standard library only.

M0 supplies installation, CLI, doctor, and quality checks. M1 adds:

- cli.py: argv parsing, Linux guard, command dispatch, text/JSON presentation.
- runner.py: subprocess lifecycle, monotonic timing, sample loop, finalization.
- models/run.py: run metadata, resource samples, and peak aggregation.
- collectors/base.py: ResourceCollector protocol, injectable in tests.
- collectors/proc.py: best-effort main-PID status/fd/stat readings.
- storage/layout.py: default location and ID validation.
- storage/json_store.py: JSONL streaming, atomic metadata replacement, loading.

The runner inherits streams and environment without recording their contents.
It does not use a shell, require strace, or aggregate descendant processes.
Handled interruption/failure terminates and reaps the direct child. Records are
finalized even when launch fails. Storage failures are explicit; no successful
final write is promised if the storage device itself fails.

Later pipeline: collector -> raw evidence -> normalizer -> normalized events ->
run storage -> analyzer -> report. Analyzers never parse raw strace directly.
Findings/differences reference evidence IDs; reports present analysis results.

M2 introduces strace events, M3 failure capsules, M4 comparisons, M5 divergence,
M6 C++/ptrace. M1 schema decisions are recorded in ADR-0002.
