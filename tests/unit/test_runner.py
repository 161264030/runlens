import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from runlens.models.run import ResourceSample
from runlens.runner import run_command
from runlens.storage.json_store import JsonStore


class FakeCollector:
    def sample(self, pid, elapsed_ns):
        return ResourceSample(elapsed_ns, rss_bytes=100, rss_hwm_bytes=200, threads=3, fd_count=4)


def test_real_subprocess_roundtrip_and_samples(tmp_path):
    store = JsonStore(tmp_path / "runs")
    record = run_command(
        [sys.executable, "-c", "import time; time.sleep(0.15)"],
        store,
        collector=FakeCollector(),
        interval=0.01,
    )
    assert record.state == "completed" and record.exit_code == 0
    assert record.pid is not None and record.signal is None
    assert record.duration_s >= 0.15
    assert record.end_monotonic_ns >= record.start_monotonic_ns
    assert record.peak_rss_bytes == 200
    assert record.peak_threads == 3 and record.peak_fd_count == 4
    assert record.proc_capture == "sampled"
    assert store.load(record.run_id)["pid"] == record.pid
    samples = [
        json.loads(line)
        for line in (store.root / record.run_id / "resources.jsonl").read_text().splitlines()
    ]
    assert len(samples) == record.sample_count > 0
    assert [s["elapsed_ns"] for s in samples] == sorted(s["elapsed_ns"] for s in samples)
    assert samples[-1]["elapsed_ns"] <= record.duration_s * 1e9


def test_argv_and_cwd_are_preserved_without_shell(tmp_path):
    value = "; echo DO_NOT_EXECUTE $(whoami) space"
    code = "import pathlib,sys; pathlib.Path('argv.txt').write_text(sys.argv[1])"
    record = run_command(
        [sys.executable, "-c", code, value],
        JsonStore(tmp_path / "runs"),
        cwd=tmp_path,
        collector=FakeCollector(),
    )
    assert record.exit_code == 0
    assert record.argv[-1] == value
    assert record.cwd == str(tmp_path.resolve())
    assert (tmp_path / "argv.txt").read_text() == value


@pytest.mark.parametrize("code", [0, 1, 7])
def test_exit_status(tmp_path, code):
    record = run_command(
        [sys.executable, "-c", f"raise SystemExit({code})"],
        JsonStore(tmp_path),
        collector=FakeCollector(),
    )
    assert record.exit_code == code and record.returncode == code
    assert record.state == "completed"


def test_launch_failure_saved(tmp_path):
    store = JsonStore(tmp_path)
    record = run_command([str(tmp_path / "no-such-executable")], store)
    assert record.state == "launch_failed" and record.error
    assert record.pid is None and record.exit_code is None
    assert record.peak_rss_bytes is None and record.proc_capture == "unavailable"
    assert store.load(record.run_id)["state"] == "launch_failed"
    assert (tmp_path / record.run_id / "resources.jsonl").read_text() == ""


@pytest.mark.parametrize(
    "exception,state", [(KeyboardInterrupt, "interrupted"), (RuntimeError, "capture_failed")]
)
def test_interruption_and_capture_errors_reap_child(tmp_path, monkeypatch, exception, state):
    children = []
    original = subprocess.Popen

    def launch(*args, **kwargs):
        process = original(*args, **kwargs)
        children.append(process)
        return process

    class BrokenCollector:
        def sample(self, pid, elapsed_ns):
            raise exception("test failure")

    monkeypatch.setattr("runlens.runner.subprocess.Popen", launch)
    record = run_command(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        JsonStore(tmp_path),
        collector=BrokenCollector(),
    )
    assert record.state == state and record.error
    assert children[0].poll() is not None


def test_partial_and_unavailable_samples(tmp_path):
    class Partial:
        def sample(self, pid, elapsed_ns):
            return ResourceSample(elapsed_ns, threads=1, errors=["fd: PermissionError"])

    record = run_command(
        [sys.executable, "-c", "import time; time.sleep(0.1)"],
        JsonStore(tmp_path / "partial"),
        collector=Partial(),
    )
    assert record.proc_capture == "partial" and record.peak_fd_count is None
    assert "fd: PermissionError" in record.capture_notes
    from runlens.collectors.proc import ProcCollector

    record = run_command(
        [sys.executable, "-c", "import time; time.sleep(0.1)"],
        JsonStore(tmp_path / "missing"),
        collector=ProcCollector(tmp_path / "none"),
    )
    assert record.proc_capture == "unavailable" and record.peak_rss_bytes is None


@pytest.mark.parametrize("interval", [0, -1, math.nan, math.inf])
def test_invalid_interval_does_not_create_storage(tmp_path, interval):
    root = tmp_path / "unused"
    with pytest.raises(ValueError):
        run_command(["never-launched"], JsonStore(root), interval=interval)
    assert not root.exists()


def test_invalid_cwd(tmp_path):
    with pytest.raises(OSError):
        run_command(
            ["never-launched"], JsonStore(tmp_path / "unused"), cwd=Path("/not-a-runlens-dir")
        )
