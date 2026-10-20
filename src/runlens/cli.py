"""Command-line interface for environment checks and M1 run recording."""

import argparse
import json
import math
import platform
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from runlens import __version__
from runlens.doctor import check_environment
from runlens.runner import run_command
from runlens.storage.json_store import JsonStore
from runlens.storage.layout import DEFAULT_RUNS_DIR


def positive_interval(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("interval must be a number") from exc
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("interval must be finite and greater than zero")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runlens",
        description="Linux execution forensics: capture runs and compare evidence.",
    )
    parser.add_argument("--version", action="version", version=f"runlens {__version__}")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks for CLI errors")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check Linux and capture dependencies")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable checks")
    run = commands.add_parser("run", help="Run a command and sample its /proc resources")
    run.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    run.add_argument("--cwd", type=Path, help="Working directory for the target command")
    run.add_argument(
        "--interval", type=positive_interval, default=0.02, help="Sample seconds (0.02)"
    )
    run.add_argument("argv", nargs=argparse.REMAINDER, help="Command and its arguments")
    listing = commands.add_parser("list", help="List recorded runs")
    listing.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    listing.add_argument("--json", action="store_true")
    inspect = commands.add_parser("inspect", help="Inspect a recorded run")
    inspect.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    inspect.add_argument("--json", action="store_true")
    inspect.add_argument("run_id")
    diff = commands.add_parser("diff", help="Compare good and bad runs (planned: M4)")
    diff.add_argument("good")
    diff.add_argument("bad")
    return parser


def command_text(value: object) -> str:
    if isinstance(value, list):
        return shlex.join(str(part) for part in value)
    return str(value)


def summary(record: dict[str, object]) -> str:
    result = record.get("signal") or record.get("exit_code")
    return f"{record['state']} (result={result})"


def inspect_text(record: dict[str, object]) -> str:
    lines = [
        f"Run: {record['run_id']}",
        f"Command: {command_text(record['argv'])}",
        f"Cwd: {record['cwd']}",
        f"PID: {record.get('pid')}",
        f"Result: {summary(record)}",
        f"Duration: {record.get('duration_s')} s",
        f"Peak RSS: {record.get('peak_rss_bytes')} bytes",
        f"Peak threads: {record.get('peak_threads')}",
        f"Peak FD: {record.get('peak_fd_count')}",
        f"Proc capture: {record['proc_capture']} ({record.get('sample_count')} samples)",
    ]
    if record.get("error"):
        lines.append(f"Error: {record['error']}")
    notes = record.get("capture_notes", [])
    if isinstance(notes, list):
        lines.extend(f"Note: {note}" for note in notes)
    return "\n".join(lines)


def execute(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        report = check_environment()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print("RunLens doctor - capture prerequisites")
            for check in report.checks:
                print(f"[{'OK' if check.ok else 'FAIL'}] {check.name}: {check.detail}")
                if check.remediation:
                    print(f"       Fix: {check.remediation}")
            print("Ready for capture." if report.ready else "Capture prerequisites are incomplete.")
            print("Checks detect availability only; ptrace permissions are not verified.")
        return 0 if report.ready else 1
    if args.command == "diff":
        print("runlens diff: not implemented (planned: M4).", file=sys.stderr)
        return 2
    store = JsonStore(args.runs_dir.resolve())
    if args.command == "run":
        if platform.system() != "Linux":
            raise ValueError("Run capture requires Linux with /proc; use Ubuntu 22.04 or WSL2.")
        record = run_command(args.argv, store, cwd=args.cwd, interval=args.interval)
        print(inspect_text(record.to_dict()), file=sys.stderr)
        print(f"Saved: {store.root / record.run_id}", file=sys.stderr)
        if record.state == "interrupted":
            return 130
        if record.state == "launch_failed":
            return 127
        if record.state != "completed":
            return 1
        assert record.returncode is not None
        return record.returncode if record.returncode >= 0 else 128 - record.returncode
    if args.command == "inspect":
        metadata = store.load(args.run_id)
        print(json.dumps(metadata, indent=2) if args.json else inspect_text(metadata))
        return 0
    records, warnings = store.list_runs()
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps(records, indent=2))
    elif not records:
        print("No saved runs.")
    else:
        for metadata in records:
            print(f"{metadata['run_id']}  {summary(metadata)}  {command_text(metadata['argv'])}")
    return 1 if warnings else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.argv[:1] == ["--"]:
            args.argv = args.argv[1:]
        if not args.argv:
            parser.error("run requires a command; example: runlens run -- ./prog")
    try:
        return execute(args)
    except (OSError, ValueError) as exc:
        if args.debug:
            raise
        print(f"runlens: {exc}", file=sys.stderr)
        return 1
