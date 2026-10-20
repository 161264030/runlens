# M1 schema: 0.1

Every metadata.json and resources.jsonl record has schema_version "0.1".
A run ID is run_ followed by 32 lowercase hex digits. No capsule manifest yet.

## metadata.json

| Field | Type / meaning |
| --- | --- |
| run_id | Unique run ID |
| argv | Nonempty array of argument strings, with no shell expansion |
| cwd | Absolute target working directory |
| pid | Launched PID, or null if launch failed |
| started_at, ended_at | UTC ISO 8601; ended_at null while running |
| start_monotonic_ns, end_monotonic_ns | Monotonic nanoseconds; end null while running |
| duration_s | Seconds between monotonic timestamps, or null |
| sample_interval_s | Requested sampling interval in seconds |
| state | running / completed / launch_failed / interrupted / capture_failed |
| returncode | Raw subprocess code; negative signal number on Linux; nullable |
| exit_code | Nonnegative target exit code; null for signal termination/no child |
| signal | Signal name, e.g. SIGTERM, or null |
| error | Launch/capture/interruption error text, or null |
| sample_count | Number of persisted samples |
| peak_rss_bytes | Maximum observed VmRSS or VmHWM, or null |
| peak_threads, peak_fd_count | Maximum sampled values, or null |
| proc_capture | sampled / partial / unavailable |
| capture_notes | Deduplicated diagnostic notes (up to 20) |

completed describes lifecycle completion, not success: exit_code may be nonzero
or signal may be set. Duration includes storage/launch/sampling/cleanup overhead.
Monotonic timestamps are not wall-clock timestamps and should not be compared
across hosts/boots. UTC timestamps support human-readable ordering.

Readers validate schema version, required fields, field types, and enums.
Unknown extra fields are accepted. Incompatible changes require a new ADR/version.
Malformed entries make list emit warnings and return 1; valid runs remain visible.
Missing runs and invalid IDs produce actionable CLI errors without tracebacks.

## resources.jsonl

| Field | Meaning |
| --- | --- |
| elapsed_ns | Nanoseconds relative to the metadata start timestamp |
| rss_bytes | VmRSS converted from kB to bytes, or null |
| rss_hwm_bytes | VmHWM converted from kB to bytes, or null |
| threads | Threads from status, or null |
| fd_count | Number of fd directory entries, or null |
| cpu_user_ticks, cpu_system_ticks | stat utime/stime ticks, or null |
| errors | Per-source read/parse errors; empty if none observed |

Each line is independently flushed. Reads of status/fd/stat are not atomic.
A process exit during sampling may yield partial or wholly missing measurements.
JSON null is distinct from zero. Sampling observes one PID, not a process tree.
sampled is not a completeness guarantee; periodic sampling may miss short peaks.

## doctor --json

Unchanged diagnostic shape: ready (boolean), checks (array of objects with name,
ok, detail, remediation). Checks are linux, strace, readelf, proc. It detects
availability, not tracing permissions or version compatibility.
