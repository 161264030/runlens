from pathlib import Path

import pytest

from runlens.config import DoctorConfig
from runlens.doctor import check_environment


def test_ready_linux(monkeypatch, tmp_path):
    monkeypatch.setattr("runlens.doctor.platform.system", lambda: "Linux")
    monkeypatch.setattr("runlens.doctor.shutil.which", lambda name: f"/usr/bin/{name}")
    report = check_environment(DoctorConfig(proc_root=tmp_path))
    assert report.ready
    assert [check.name for check in report.checks] == ["linux", "strace", "readelf", "proc"]
    assert all(not check.remediation for check in report.checks)


def test_missing_requirements(monkeypatch, tmp_path):
    monkeypatch.setattr("runlens.doctor.platform.system", lambda: "Windows")
    monkeypatch.setattr("runlens.doctor.shutil.which", lambda name: None)
    report = check_environment(DoctorConfig(proc_root=tmp_path / "absent"))
    assert not report.ready
    assert all(not check.ok and check.remediation for check in report.checks)
    assert "binutils" in report.checks[2].remediation
    assert report.to_dict()["ready"] is False


@pytest.mark.parametrize("kind", ["file", "denied", "error"])
def test_inaccessible_proc(monkeypatch, tmp_path, kind):
    proc = tmp_path / "proc"
    if kind == "file":
        proc.write_text("not a directory")
    else:
        proc.mkdir()
        if kind == "denied":
            monkeypatch.setattr("runlens.doctor.os.access", lambda *args: False)
        else:
            def denied(self):
                raise PermissionError("permission denied")

            monkeypatch.setattr(Path, "is_dir", denied)
    report = check_environment(DoctorConfig(proc_root=proc))
    assert not report.checks[-1].ok
    assert report.checks[-1].remediation
