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


@pytest.mark.parametrize(
    "args,milestone",
    [(["run", "--", "./prog", "--flag"], "M1"), (["list"], "M1"),
     (["inspect", "run-id"], "M1"), (["diff", "good", "bad"], "M4")],
)
def test_placeholders(args, milestone, capsys, tmp_path):
    marker = tmp_path / "must-not-exist"
    if args[0] == "run":
        args = ["run", "--", sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]
    assert main(args) == 2
    captured = capsys.readouterr()
    assert "not implemented in M0" in captured.err
    assert milestone in captured.err
    assert not captured.out
    assert not marker.exists()


@pytest.mark.parametrize("args", [[], ["unknown"], ["run"], ["run", "--"], ["inspect"],
                                  ["diff", "good"], ["doctor", "--unknown"]])
def test_usage_error(args, capsys):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "error:" in error
    assert "Traceback" not in error


def test_installed_module_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "runlens", "--help"], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "doctor" in result.stdout
