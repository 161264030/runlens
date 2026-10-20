"""M1 storage records. Missing measurements are null, never invented zeros."""

from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = "0.1"


@dataclass
class ResourceSample:
    elapsed_ns: int
    rss_bytes: int | None = None
    rss_hwm_bytes: int | None = None
    threads: int | None = None
    fd_count: int | None = None
    cpu_user_ticks: int | None = None
    cpu_system_ticks: int | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass
class RunRecord:
    run_id: str
    argv: list[str]
    cwd: str
    started_at: str
    start_monotonic_ns: int
    sample_interval_s: float
    state: str = "running"
    schema_version: str = SCHEMA_VERSION
    pid: int | None = None
    ended_at: str | None = None
    end_monotonic_ns: int | None = None
    duration_s: float | None = None
    returncode: int | None = None
    exit_code: int | None = None
    signal: str | None = None
    error: str | None = None
    sample_count: int = 0
    peak_rss_bytes: int | None = None
    peak_threads: int | None = None
    peak_fd_count: int | None = None
    proc_capture: str = "unavailable"
    capture_notes: list[str] = field(default_factory=list)

    def observe(self, sample: ResourceSample) -> None:
        self.sample_count += 1
        for attribute, values in (
            ("peak_rss_bytes", (sample.rss_bytes, sample.rss_hwm_bytes)),
            ("peak_threads", (sample.threads,)),
            ("peak_fd_count", (sample.fd_count,)),
        ):
            for value in values:
                if value is not None:
                    previous = getattr(self, attribute)
                    setattr(self, attribute, value if previous is None else max(previous, value))
        for error in sample.errors:
            self.note(error)

    def note(self, message: str) -> None:
        if message not in self.capture_notes and len(self.capture_notes) < 20:
            self.capture_notes.append(message)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
