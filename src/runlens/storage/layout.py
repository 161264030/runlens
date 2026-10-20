import re
from pathlib import Path

DEFAULT_RUNS_DIR = Path(".runlens/runs")


def run_path(root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"run_[0-9a-f]{32}", run_id):
        raise ValueError("Invalid run ID; copy an ID from 'runlens list'.")
    return root / run_id
