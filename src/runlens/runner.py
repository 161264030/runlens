"""Launch argv without a shell, sample while alive, and always reap the child."""

import math
import signal
import subprocess
import time
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from runlens.collectors.base import ResourceCollector
from runlens.collectors.proc import ProcCollector
from runlens.models.run import RunRecord
from runlens.storage.json_store import JsonStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stop_child(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    except ProcessLookupError:
        process.wait()


def run_command(
    argv: Sequence[str],
    store: JsonStore,
    *,
    cwd: Path | None = None,
    interval: float = 0.02,
    collector: ResourceCollector | None = None,
) -> RunRecord:
    if not argv:
        raise ValueError("A command is required.")
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("Sample interval must be a finite number greater than zero.")
    collector = collector if collector is not None else ProcCollector()
    workdir = (cwd or Path.cwd()).resolve(strict=True)
    if not workdir.is_dir():
        raise ValueError(f"Working directory is not a directory: {workdir}")
    record = RunRecord(
        run_id=f"run_{uuid.uuid4().hex}",
        argv=list(argv),
        cwd=str(workdir),
        started_at=utc_now(),
        start_monotonic_ns=time.monotonic_ns(),
        sample_interval_s=interval,
    )
    store.create(record)
    process: subprocess.Popen[bytes] | None = None
    any_data, degraded = False, False
    try:
        with store.open_samples(record.run_id) as samples:
            try:
                process = subprocess.Popen(list(argv), cwd=workdir)
            except (OSError, ValueError) as exc:
                record.state = "launch_failed"
                record.error = str(exc)
            else:
                record.pid = process.pid
                store.save(record)
                while process.poll() is None:
                    sample = collector.sample(
                        process.pid, time.monotonic_ns() - record.start_monotonic_ns
                    )
                    store.append(samples, sample)
                    record.observe(sample)
                    any_data |= any(
                        value is not None
                        for value in (
                            sample.rss_bytes,
                            sample.threads,
                            sample.fd_count,
                        )
                    )
                    degraded |= bool(sample.errors)
                    try:
                        process.wait(timeout=interval)
                    except subprocess.TimeoutExpired:
                        pass
                record.state = "completed"
    except KeyboardInterrupt:
        record.state = "interrupted"
        record.error = "Capture interrupted by user."
    except Exception as exc:
        record.state = "capture_failed"
        record.error = f"{type(exc).__name__}: {exc}"
    finally:
        if process is not None:
            stop_child(process)
            code = process.wait()
            record.returncode = code
            if code >= 0:
                record.exit_code = code
            else:
                try:
                    record.signal = signal.Signals(-code).name
                except ValueError:
                    record.signal = f"SIGNAL_{-code}"
        record.end_monotonic_ns = time.monotonic_ns()
        record.ended_at = utc_now()
        record.duration_s = (record.end_monotonic_ns - record.start_monotonic_ns) / 1e9
        degraded |= record.state != "completed"
        record.proc_capture = (
            "partial" if any_data and degraded else ("sampled" if any_data else "unavailable")
        )
        if not any_data:
            record.note("No resource measurements; process may have exited before sampling.")
        record.note(
            "Periodic main-process samples may miss short-lived resource peaks or children."
        )
        store.save(record)
    return record
