"""Read-only capability detection; never execute external tools or request root."""

import os
import platform
import shutil
from dataclasses import asdict, dataclass

from runlens.config import DoctorConfig


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    remediation: str = ""


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[CheckResult, ...]

    @property
    def ready(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "checks": [asdict(check) for check in self.checks]}


def check_environment(config: DoctorConfig | None = None) -> DoctorReport:
    config = config or DoctorConfig()
    system = platform.system()
    checks = [
        CheckResult(
            "linux",
            system == "Linux",
            f"Detected platform: {system}",
            "Use Linux (recommended: Ubuntu 24.04+) or WSL2." if system != "Linux" else "",
        )
    ]
    for tool in config.required_tools:
        resolved = shutil.which(tool)
        package = "binutils" if tool == "readelf" else tool
        checks.append(
            CheckResult(
                tool,
                resolved is not None,
                resolved or f"{tool} not found on PATH",
                f"On Ubuntu/Debian: sudo apt install {package}" if resolved is None else "",
            )
        )
    try:
        proc_ok = config.proc_root.is_dir() and os.access(config.proc_root, os.R_OK | os.X_OK)
    except OSError:
        proc_ok = False
    checks.append(
        CheckResult(
            "proc",
            proc_ok,
            f"{config.proc_root}: {'accessible' if proc_ok else 'missing or inaccessible'}",
            "Use Linux with procfs mounted and readable at /proc." if not proc_ok else "",
        )
    )
    return DoctorReport(tuple(checks))
