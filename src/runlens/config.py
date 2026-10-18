"""Stable M0 defaults; no filesystem side effects on import."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DoctorConfig:
    proc_root: Path = Path("/proc")
    required_tools: tuple[str, ...] = ("strace", "readelf")
