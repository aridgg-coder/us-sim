from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def get_tusx_runner_command() -> list[str]:
    runner = os.getenv("TUSX_RUNNER")
    if runner:
        return runner.split()

    root = Path(__file__).resolve().parents[2]
    return ["python3", str(root / "scripts" / "run_tusx_wrapper.py")]


def run_tusx_external(handoff_path: Path, run_dir: Path) -> dict[str, Any]:
    command = get_tusx_runner_command()
    completed = subprocess.run(
        [*command, "--handoff", str(handoff_path), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    process_payload = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    (run_dir / "tusx_process.json").write_text(
        json.dumps(process_payload, indent=2) + "\n", encoding="utf-8"
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"TUSX runner failed with code {completed.returncode}: {completed.stderr.strip()}"
        )

    result_path = run_dir / "tusx_result.json"
    if not result_path.exists():
        raise FileNotFoundError(f"TUSX result file missing: {result_path}")

    return json.loads(result_path.read_text(encoding="utf-8"))
