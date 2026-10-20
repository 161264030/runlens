from typing import Protocol

from runlens.models.run import ResourceSample


class ResourceCollector(Protocol):
    def sample(self, pid: int, elapsed_ns: int) -> ResourceSample: ...
