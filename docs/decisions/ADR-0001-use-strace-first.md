# ADR-0001: Use strace before a custom tracing backend

Status: Accepted

Reuse strace/readelf in the initial Linux implementation. Establish the run model,
evidence normalization, and comparisons before implementing ptrace in C++.
Collectors gather raw evidence; analyzers consume normalized data only.

M0 detects dependencies without invoking them. argparse is sufficient for the
initial command surface, so no runtime dependency is required. Missing capture
dependencies do not prevent installation or CLI help on other platforms.
