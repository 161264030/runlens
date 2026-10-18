# Data formats

M0 creates no runs, events, or capsules. No capture schema is committed yet.

`runlens doctor --json` prints a diagnostic object with `ready` (boolean) and
`checks` (ordered array). Each check has `name`, `ok`, `detail`, and `remediation`.
Names: linux, strace, readelf, proc. An empty remediation means no fix is needed.
This output describes availability, not a guarantee of tracing permissions.

M1 will introduce run metadata/resources. Capture formats must have an explicit
schema version before capsules are introduced in M3. Preserve raw evidence
separately and attach source/evidence IDs to normalized data.
