# Next issue: Implement RunSession and subprocess runner (M1)

Goal: launch argv via subprocess without shell=True; record argv, cwd, PID,
start/end monotonic times, exit status, and explicit signal names.

Non-goals: strace, parser, capsule, diff, and C++.

Acceptance: exit0, exit1, sleep, and signal termination fixtures produce correct
results. Add /proc polling and JSON storage in subsequent scoped M1 work.

This local issue draft does not create a GitHub repository or remote issue.
