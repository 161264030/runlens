# Next milestone: M2 strace and normalized events

M1 implementation: runner, periodic main-PID /proc sampling, private JSON/JSONL
storage, list, inspect, and automated acceptance fixtures. Validate real Linux
integration tests on Ubuntu 22.04 and review CI before claiming acceptance.

M2 scope: strace subprocess adapter, raw evidence preservation, a small syscall
normalizer with source references, and parser golden cases. See the playbook.
Do not add capsules, diff analysis, C++, or eBPF in this milestone.

Potential follow-ups outside M1: descendant accounting/cleanup, crash recovery,
resource sampling benchmarks, and more collector compatibility fixtures.
