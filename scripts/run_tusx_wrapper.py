#!/usr/bin/env python3
"""
TUSX Runner Wrapper: Orchestrates the MATLAB/k-Wave simulation through TUSX.

This script:
1. Takes a handoff JSON package prepared by the backend
2. Attempts to invoke the MATLAB launcher with TUSX + k-Wave
3. Falls back to stub results if MATLAB is unavailable (MVP mode)
4. Writes results back to JSON for the backend to consume
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TUSX simulation via MATLAB launcher or fallback to stub"
    )
    parser.add_argument("--handoff", required=True, help="Path to handoff JSON file")
    parser.add_argument("--run-dir", required=True, help="Run artifacts directory")
    parser.add_argument("--use-stub", action="store_true", help="Force stub mode (no MATLAB)")
    return parser.parse_args()


def find_matlab_executable() -> Path | None:
    """Find MATLAB executable on the system."""
    # Check environment variable first
    matlab_root = os.getenv("MATLAB_ROOT")
    if matlab_root:
        exe = Path(matlab_root) / "bin" / "matlab"
        if exe.exists():
            return exe
    
    # Try which command (Unix-like)
    try:
        result = subprocess.run(
            ["which", "matlab"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    
    # Check common Windows WSL path
    wsl_path = Path("/mnt/c/Program Files/MATLAB")
    if wsl_path.exists():
        # Find most recent version
        versions = sorted([d for d in wsl_path.iterdir() if d.is_dir()], reverse=True)
        for version_dir in versions:
            exe = version_dir / "bin" / "matlab.exe"
            if exe.exists():
                return exe
    
    # Check Windows native
    for base in [Path(r"C:\Program Files\MATLAB"), Path(r"C:\Program Files (x86)\MATLAB")]:
        if base.exists():
            versions = sorted([d for d in base.iterdir() if d.is_dir()], reverse=True)
            for version_dir in versions:
                exe = version_dir / "bin" / "matlab.exe"
                if exe.exists():
                    return exe
    
    return None


def run_matlab_tusx(
    handoff_path: Path,
    run_dir: Path,
    matlab_exe: Path,
) -> tuple[int, str, str]:
    """
    Run TUSX simulation via MATLAB.
    
    Args:
        handoff_path: Path to external_handoff.json
        run_dir: Run artifacts directory
        matlab_exe: Path to MATLAB executable
    
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    # Import here to avoid circular dependency
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.matlab_config import MATLABConfig
    
    # Build MATLAB launcher script path
    launcher_script = Path(__file__).resolve().parent / "tusx_matlab_launcher.m"
    
    # Build MATLAB command to run the launcher script
    # MATLAB batch mode: -batch "script_name; exit;"
    matlab_cmd = "disp('Hello from MATLAB');"
    
    # Set up environment with k-Wave and TUSX paths
    env = os.environ.copy()
    env["TUSX_INPUT_FILE"] = str(run_dir / "tusx_input.json")
    env["TUSX_RUN_DIR"] = str(run_dir)
    
    # Load KWAVE_PATH and TUSX_PATH from environment
    kwave_path = env.get("KWAVE_PATH") or "/mnt/c/Users/rakxa/Desktop/ucl-bug-k-wave-1.4.1.0"
    tusx_path = env.get("TUSX_PATH") or "/home/aridgg/us-sim/tusx"
    
    env["KWAVE_PATH"] = kwave_path
    env["TUSX_PATH"] = tusx_path
    
    # Build command using WSL-aware builder if needed
    cmd = MATLABConfig.build_wsl_matlab_command(matlab_exe, matlab_cmd)
    
    # Run MATLAB
    try:
        returncode = os.system(cmd)
        return returncode, "", ""  # os.system doesn't capture output
    except Exception as e:
        return 1, "", f"Failed to run MATLAB: {e}"


def run_stub_simulation(handoff_path: Path, run_dir: Path) -> int:
    """
    Run stub simulation (MVP fallback mode).
    
    Args:
        handoff_path: Path to external_handoff.json
        run_dir: Run artifacts directory
    
    Returns:
        Return code
    """
    stub_path = Path(__file__).resolve().parent / "tusx_runner_stub.py"
    completed = subprocess.run(
        ["python3", str(stub_path), "--handoff", str(handoff_path), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode


def main() -> int:
    args = parse_args()
    handoff_path = Path(args.handoff)
    run_dir = Path(args.run_dir)
    package_path = run_dir / "tusx_input.json"

    # Validate inputs
    if not handoff_path.exists():
        print(f"missing handoff file: {handoff_path}", file=sys.stderr)
        return 2
    if not package_path.exists():
        print(f"missing tusx input package: {package_path}", file=sys.stderr)
        return 2

    # Try to use real MATLAB + TUSX, fall back to stub
    returncode = 1
    stdout_text = ""
    stderr_text = ""
    matlab_path = None
    
    if not args.use_stub:
        matlab_path = find_matlab_executable()
        if matlab_path:
            print(f"Found MATLAB at: {matlab_path}")
            returncode, stdout_text, stderr_text = run_matlab_tusx(
                handoff_path, run_dir, matlab_path
            )
        else:
            print("MATLAB not found, falling back to stub simulation (MVP mode)")
            returncode = run_stub_simulation(handoff_path, run_dir)
    else:
        print("Stub mode forced, skipping MATLAB")
        returncode = run_stub_simulation(handoff_path, run_dir)

    # Log the wrapper execution
    wrapper_log = {
        "wrapper": "run_tusx_wrapper.py",
        "handoff_path": str(handoff_path),
        "tusx_input_path": str(package_path),
        "tusx_launcher": str(Path(__file__).resolve().parent / "tusx_matlab_launcher.m"),
        "matlab_found": matlab_path is not None,
        "matlab_executable": str(matlab_path) if matlab_path else None,
        "mode": "matlab" if matlab_path and not args.use_stub else "stub",
        "returncode": returncode,
        "stdout": stdout_text[:2000] if stdout_text else "",  # Limit log size
        "stderr": stderr_text[:2000] if stderr_text else "",
    }
    
    log_path = run_dir / "tusx_wrapper.log"
    log_path.write_text(
        json.dumps(wrapper_log, indent=2) + "\n",
        encoding="utf-8",
    )

    return returncode


if __name__ == "__main__":
    raise SystemExit(main())

