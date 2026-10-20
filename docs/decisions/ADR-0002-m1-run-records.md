# ADR-0002: M1 run storage and collection boundaries

Status: Accepted

Use schema_version 0.1 for metadata.json and each resources.jsonl line. M0 did
not write runs, so no migration is required. Future incompatible changes require
a schema/version decision. These records are not M3 failure capsules yet.

Use UUID-based run IDs and validate IDs before constructing storage paths.
Write metadata on creation, after launch, and on finalization using atomic
replacement. Flush samples individually to avoid buffering an entire run in RAM.
Create run directories with mode 0700 and files with mode 0600 on POSIX systems.

M1 observes only the launched PID. Polling is not an exact lifetime peak monitor.
Use VmHWM where available for RSS peaks; FD/thread peaks remain sampled maxima.
Do not claim capture completeness: sampled, partial, and unavailable explicitly
describe the observations. Missing values are null; errors are recorded.

Keep subprocess runner, collector protocol, records, storage, and CLI separate.
The runner inherits target streams and environment but records no environment
variables or stream contents. It launches argv without shell=True. On handled
interruption or collection failure, terminate/reap the direct child, escalating
to kill after one second. Descendant cleanup and SIGKILL recovery are not M1.

CLI options for run precede the target executable; one optional -- separator
is stripped. The CLI propagates child exit codes and uses 128+signal for signal
termination. CLI summaries go to stderr so target stdout is unchanged.
