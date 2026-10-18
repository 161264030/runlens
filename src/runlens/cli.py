"""M0 command surface. Future milestones implement capture and analysis."""

import argparse
import json
import sys
from collections.abc import Sequence

from runlens import __version__
from runlens.doctor import check_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runlens",
        description="Linux execution forensics: capture runs and compare evidence.",
    )
    parser.add_argument("--version", action="version", version=f"runlens {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check Linux and required capture dependencies")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable checks")
    run = commands.add_parser("run", help="Capture a command (planned: M1)")
    run.add_argument("argv", nargs=argparse.REMAINDER, help="Command and its arguments")
    commands.add_parser("list", help="List saved runs (planned: M1)")
    inspect = commands.add_parser("inspect", help="Inspect a saved run (planned: M1)")
    inspect.add_argument("run_id")
    diff = commands.add_parser("diff", help="Compare good and bad runs (planned: M4)")
    diff.add_argument("good")
    diff.add_argument("bad")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
            print("Checks detect availability only; ptrace permissions are not verified in M0.")
        return 0 if report.ready else 1
    if args.command == "run" and (not args.argv or args.argv == ["--"]):
        parser.error("run requires a command; example: runlens run -- ./prog")
    milestone = "M4" if args.command == "diff" else "M1"
    print(
        f"runlens {args.command}: not implemented in M0 (planned: {milestone}). "
        "Use 'runlens doctor' to check capture prerequisites.",
        file=sys.stderr,
    )
    return 2
