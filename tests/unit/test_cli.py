import json
import subprocess
import sys

import pytest

from runlens import __version__
from runlens.cli import main
from runlens.doctor import CheckResult, DoctorReport


@pytest.mark.parametrize("command", [None, "run", "list", "inspect", "diff", "doctor"])
def test_help(command, capsys):
    with pytest.raises(SystemExit) as exc:
        main(([command] if command else []) + ["--help"])
    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize("ready", [True, False])
@pytest.mark.parametrize("as_json", [True, False])
def test_doctor_output(monkeypatch, capsys, ready, as_json):
    report = DoctorReport((CheckResult("linux", ready, "platform", "" if ready else "Use Linux"),))
    monkeypatch.setattr("runlens.cli.check_environment", lambda: report)
    code = main(["doctor"] + (["--json"] if as_json else []))
    assert code == (0 if ready else 1)
    output = capsys.readouterr().out
    if as_json:
        assert json.loads(output) == report.to_dict()
    else:
        assert ("[OK]" if ready else "[FAIL]") in output
        assert ("Fix:" in output) is not ready


def test_diff_placeholder(capsys):
    assert main(["diff", "good", "bad"]) == 2
    assert "planned: M4" in capsys.readouterr().err


def test_empty_list_and_missing_inspect(tmp_path, capsys):
    root = str(tmp_path / "runs")
    assert main(["list", "--runs-dir", root, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["inspect", "--runs-dir", root, "run_" + "f" * 32]) == 1
    assert "Cannot read run" in capsys.readouterr().err


def test_non_linux_run_is_actionable(monkeypatch, capsys):
    monkeypatch.setattr("runlens.cli.platform.system", lambda: "Windows")
    assert main(["run", "--", "./prog"]) == 1
    assert "requires Linux" in capsys.readouterr().err


def test_cli_launch_failure_is_saved(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("runlens.cli.platform.system", lambda: "Linux")
    assert (
        main(["run", "--runs-dir", str(tmp_path), "--", str(tmp_path / "no-such-program")]) == 127
    )
    output = capsys.readouterr().err
    assert "launch_failed" in output and "Saved:" in output
    assert "Traceback" not in output
    assert main(["list", "--runs-dir", str(tmp_path), "--json"]) == 0
    records = json.loads(capsys.readouterr().out)
    assert records[0]["state"] == "launch_failed"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_interval(value, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--interval", value, "--", "./prog"])
    assert exc.value.code == 2
    assert "interval" in capsys.readouterr().err


def test_cli_run_status_and_argument_boundary(monkeypatch, tmp_path, capsys):
    from runlens.models.run import RunRecord

    calls = []

    def run(argv, store, **kwargs):
        calls.append(argv)
        record = RunRecord("run_" + "a" * 32, list(argv), str(tmp_path), "now", 0, 0.02)
        record.state = "completed"
        record.returncode = record.exit_code = 7
        return record

    monkeypatch.setattr("runlens.cli.platform.system", lambda: "Linux")
    monkeypatch.setattr("runlens.cli.run_command", run)
    assert main(["run", "--", "prog", "--json", "value with spaces"]) == 7
    assert calls == [["prog", "--json", "value with spaces"]]
    assert "Saved:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["unknown"],
        ["run"],
        ["run", "--"],
        ["inspect"],
        ["diff", "good"],
        ["doctor", "--unknown"],
    ],
)
def test_usage_error(args, capsys):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "error:" in error
    assert "Traceback" not in error


def test_installed_module_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "runlens", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "doctor" in result.stdout
