"""Real Linux acceptance fixtures, executed by Ubuntu CI."""

import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from runlens.runner import run_command
from runlens.storage.json_store import JsonStore

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Requires real Linux /proc")
PROGRAMS = Path(__file__).parents[1] / "fixtures" / "programs"


def fixture_run(tmp_path, name):
    return run_command(
        [sys.executable, str(PROGRAMS / f"{name}.py")], JsonStore(tmp_path), interval=0.005
    )


@pytest.mark.parametrize("fixture,code", [("exit0", 0), ("exit1", 1)])
def test_exit_fixtures(tmp_path, fixture, code):
    record = fixture_run(tmp_path, fixture)
    assert record.state == "completed" and record.exit_code == code
    assert record.returncode == code and record.signal is None


def test_sleep(tmp_path):
    record = fixture_run(tmp_path, "sleep")
    assert record.exit_code == 0 and record.duration_s >= 0.3
    assert record.sample_count > 0
    assert record.peak_rss_bytes > 0


def test_memory_growth(tmp_path):
    record = fixture_run(tmp_path, "memory_growth")
    samples = [
        json.loads(line)
        for line in (tmp_path / record.run_id / "resources.jsonl").read_text().splitlines()
    ]
    rss = [s["rss_bytes"] for s in samples if s["rss_bytes"] is not None]
    assert record.exit_code == 0
    assert max(rss) - min(rss) >= 24 * 1024 * 1024
    assert record.peak_rss_bytes >= max(rss)


def test_thread_spawn(tmp_path):
    record = fixture_run(tmp_path, "thread_spawn")
    assert record.exit_code == 0 and record.peak_threads >= 6


def test_fd_open(tmp_path):
    record = fixture_run(tmp_path, "fd_open")
    assert record.exit_code == 0 and record.peak_fd_count >= 27


def test_signal_exit(tmp_path):
    record = fixture_run(tmp_path, "signal_exit")
    assert record.returncode == -signal.SIGTERM
    assert record.exit_code is None and record.signal == "SIGTERM"


def test_cli_run_list_inspect(tmp_path):
    def cli(*args):
        return subprocess.run(
            [sys.executable, "-m", "runlens", *args], capture_output=True, text=True, check=False
        )

    root = str(tmp_path / "runs")
    result = cli("run", "--runs-dir", root, "--", sys.executable, str(PROGRAMS / "exit1.py"))
    assert result.returncode == 1 and "Saved:" in result.stderr
    listing = cli("list", "--runs-dir", root, "--json")
    assert listing.returncode == 0
    records = json.loads(listing.stdout)
    inspected = cli("inspect", "--runs-dir", root, "--json", records[0]["run_id"])
    assert inspected.returncode == 0
    assert json.loads(inspected.stdout)["exit_code"] == 1


def test_cli_signal_exit_code(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "runlens",
            "run",
            "--runs-dir",
            str(tmp_path),
            "--",
            sys.executable,
            str(PROGRAMS / "signal_exit.py"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 143
    assert "SIGTERM" in result.stderr


def test_capture_failure_kills_child_that_ignores_terminate(tmp_path):
    from runlens.collectors.proc import ProcCollector

    marker = tmp_path / "ready"

    class FailAfterReady:
        def sample(self, pid, elapsed_ns):
            if marker.exists():
                raise RuntimeError("simulate collector failure")
            return ProcCollector().sample(pid, elapsed_ns)

    code = (
        "import signal,time,pathlib; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"pathlib.Path({str(marker)!r}).touch(); time.sleep(10)"
    )
    record = run_command(
        [sys.executable, "-c", code],
        JsonStore(tmp_path / "runs"),
        collector=FailAfterReady(),
        interval=0.005,
    )
    assert record.state == "capture_failed" and record.signal == "SIGKILL"
    assert record.duration_s < 8
    assert not Path(f"/proc/{record.pid}").exists()
