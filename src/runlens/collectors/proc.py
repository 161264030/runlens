"""Best-effort sampling of the launched process, without traversing descendants."""

import os
from pathlib import Path

from runlens.models.run import ResourceSample


class ProcCollector:
    def __init__(self, proc_root: Path = Path("/proc")) -> None:
        self.proc_root = proc_root

    def sample(self, pid: int, elapsed_ns: int) -> ResourceSample:
        root = self.proc_root / str(pid)
        sample = ResourceSample(elapsed_ns)
        try:
            fields = {}
            for line in (
                (root / "status").read_text(encoding="utf-8", errors="replace").splitlines()
            ):
                name, separator, value = line.partition(":")
                if separator:
                    fields[name] = value.split()
            for key, attr, memory in (
                ("VmRSS", "rss_bytes", True),
                ("VmHWM", "rss_hwm_bytes", True),
                ("Threads", "threads", False),
            ):
                try:
                    parts = fields[key]
                    number = int(parts[0])
                    if number < 0 or (memory and parts[1:] != ["kB"]):
                        raise ValueError("unexpected value or unit")
                    setattr(sample, attr, number * 1024 if memory else number)
                except (KeyError, IndexError, ValueError):
                    sample.errors.append(f"status: {key} missing or invalid")
        except OSError as exc:
            sample.errors.append(f"status: {type(exc).__name__}")
        try:
            with os.scandir(root / "fd") as entries:
                sample.fd_count = sum(1 for _ in entries)
        except OSError as exc:
            sample.errors.append(f"fd: {type(exc).__name__}")
        try:
            # comm may contain spaces and parentheses; fields follow its last ')'.
            stat = (root / "stat").read_text(encoding="utf-8", errors="replace")
            _, separator, tail = stat.rpartition(")")
            if not separator:
                raise ValueError("missing comm")
            fields_stat = tail.split()
            user, system = int(fields_stat[11]), int(fields_stat[12])
            if user < 0 or system < 0:
                raise ValueError("negative CPU ticks")
            sample.cpu_user_ticks, sample.cpu_system_ticks = user, system
        except (OSError, ValueError, IndexError) as exc:
            sample.errors.append(f"stat: {type(exc).__name__}")
        return sample
