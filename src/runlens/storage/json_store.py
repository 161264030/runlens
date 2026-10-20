"""Stream samples and atomically replace metadata after state transitions."""

import json
import math
import os
from dataclasses import fields
from pathlib import Path
from typing import TextIO, cast

from runlens.models.run import SCHEMA_VERSION, ResourceSample, RunRecord
from runlens.storage.layout import run_path


class StorageError(ValueError):
    pass


class JsonStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, run: RunRecord) -> Path:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = run_path(self.root, run.run_id)
        directory.mkdir(mode=0o700)
        self.save(run)
        return directory

    def save(self, run: RunRecord) -> None:
        directory = run_path(self.root, run.run_id)
        temporary = directory / "metadata.json.tmp"
        with temporary.open("w", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(run.to_dict(), stream, indent=2, ensure_ascii=True, allow_nan=False)
            stream.write("\n")
        temporary.replace(directory / "metadata.json")

    def open_samples(self, run_id: str) -> TextIO:
        path = run_path(self.root, run_id) / "resources.jsonl"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        return os.fdopen(descriptor, "w", encoding="utf-8")

    @staticmethod
    def append(stream: TextIO, sample: ResourceSample) -> None:
        stream.write(json.dumps(sample.to_dict(), allow_nan=False) + "\n")
        stream.flush()

    def load(self, run_id: str) -> dict[str, object]:
        path = run_path(self.root, run_id) / "metadata.json"
        try:
            with path.open(encoding="utf-8") as stream:
                value = json.load(stream)
        except (OSError, ValueError) as exc:
            raise StorageError(f"Cannot read run {run_id}: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise StorageError(f"Invalid or unsupported metadata schema: {run_id}")
        required = {item.name for item in fields(RunRecord)}
        if not required <= value.keys() or value["run_id"] != run_id:
            raise StorageError(f"Incomplete metadata: {run_id}")
        if (
            not isinstance(value["argv"], list)
            or not value["argv"]
            or not all(isinstance(arg, str) for arg in value["argv"])
            or not all(isinstance(value[key], str) for key in ("cwd", "started_at"))
            or value["state"]
            not in ("running", "completed", "launch_failed", "interrupted", "capture_failed")
            or value["proc_capture"] not in ("sampled", "partial", "unavailable")
            or not isinstance(value["capture_notes"], list)
            or not all(isinstance(note, str) for note in value["capture_notes"])
        ):
            raise StorageError(f"Invalid metadata fields: {run_id}")
        for key in ("ended_at", "signal", "error"):
            if value[key] is not None and not isinstance(value[key], str):
                raise StorageError(f"Invalid {key}: {run_id}")
        for key in (
            "start_monotonic_ns",
            "end_monotonic_ns",
            "pid",
            "returncode",
            "exit_code",
            "sample_count",
            "peak_rss_bytes",
            "peak_threads",
            "peak_fd_count",
        ):
            number = value[key]
            if number is None and key not in ("start_monotonic_ns", "sample_count"):
                continue
            if type(number) is not int or (key != "returncode" and number < 0):
                raise StorageError(f"Invalid {key}: {run_id}")
        for key in ("duration_s", "sample_interval_s"):
            number = value[key]
            if number is None and key == "duration_s":
                continue
            if (
                type(number) not in (int, float)
                or not math.isfinite(number)
                or number < 0
                or (key == "sample_interval_s" and number == 0)
            ):
                raise StorageError(f"Invalid {key}: {run_id}")
        return cast(dict[str, object], value)

    def list_runs(self) -> tuple[list[dict[str, object]], list[str]]:
        if not self.root.exists():
            return [], []
        records, warnings = [], []
        for directory in sorted(self.root.iterdir()):
            if directory.is_dir() and directory.name.startswith("run_"):
                try:
                    records.append(self.load(directory.name))
                except (StorageError, ValueError) as exc:
                    warnings.append(str(exc))
        records.sort(key=lambda record: str(record["started_at"]), reverse=True)
        return records, warnings
