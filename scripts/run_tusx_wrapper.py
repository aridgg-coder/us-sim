#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--run-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handoff_path = Path(args.handoff)
    run_dir = Path(args.run_dir)
    package_path = run_dir / "tusx_input.json"

    if not handoff_path.exists():
      print(f"missing handoff file: {handoff_path}", file=sys.stderr)
      return 2
    if not package_path.exists():
      print(f"missing tusx input package: {package_path}", file=sys.stderr)
      return 2

    # Real integration point:
    # replace this subprocess target with the actual TUSX invocation when available.
    stub_path = Path(__file__).resolve().parent / "tusx_runner_stub.py"
    completed = subprocess.run(
        ["python3", str(stub_path), "--handoff", str(handoff_path), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    wrapper_log = {
        "wrapper": "run_tusx_wrapper.py",
        "handoff_path": str(handoff_path),
        "tusx_input_path": str(package_path),
        "delegated_command": ["python3", str(stub_path), "--handoff", str(handoff_path), "--run-dir", str(run_dir)],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    (run_dir / "tusx_wrapper.log").write_text(
        json.dumps(wrapper_log, indent=2) + "\n", encoding="utf-8"
    )

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

