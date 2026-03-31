"""MATLAB environment configuration for TUSX integration."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional


class MATLABConfig:
    """Manages MATLAB executable and path configuration."""
    
    # Common MATLAB installation paths by OS
    COMMON_PATHS = {
        "windows": [
            r"C:\Program Files\MATLAB",
            r"C:\Program Files (x86)\MATLAB",
            r"/mnt/c/Program Files/MATLAB",  # WSL
        ],
        "linux": [
            "/usr/local/MATLAB",
            "/opt/MATLAB",
            "/home",  # Search home directories
        ],
        "darwin": [
            "/Applications/MATLAB_R",
        ],
    }
    
    @staticmethod
    def is_wsl() -> bool:
        """Check if running under WSL."""
        return "microsoft" in platform.release().lower()
    
    @staticmethod
    def find_matlab_executable() -> Optional[Path]:
        """
        Find MATLAB executable on the system.
        
        Tries in order:
        1. MATLAB_ROOT environment variable
        2. which matlab (Unix) or where matlab (Windows)
        3. Common installation paths
        
        Returns:
            Path to matlab executable, or None if not found
        """
        # Check environment variable first
        matlab_root = os.getenv("MATLAB_ROOT")
        if matlab_root:
            exe_path = Path(matlab_root) / "bin" / "matlab.exe"
            if exe_path.exists():
                return exe_path
        
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
    
    @staticmethod
    def get_matlab_launch_command(
        matlab_exe: Optional[Path] = None,
        script: Optional[str] = None,
        args: Optional[dict] = None,
    ) -> list[str]:
        """
        Build MATLAB launch command.
        
        Args:
            matlab_exe: Path to matlab executable (auto-detected if None)
            script: Name of MATLAB script to run
            args: Dictionary of environment variables to set
        
        Returns:
            Command list for subprocess.run
        """
        if matlab_exe is None:
            matlab_exe = MATLABConfig.find_matlab_executable()
        
        if matlab_exe is None:
            raise RuntimeError(
                "MATLAB not found. Set MATLAB_ROOT environment variable or add MATLAB to PATH."
            )
        
        cmd = [str(matlab_exe), "-batch"]
        
        # Build MATLAB batch command
        if script:
            batch_cmd = script
            if args:
                for key, value in args.items():
                    batch_cmd = f"setenv('{key}', '{value}'); {batch_cmd}"
            cmd.append(batch_cmd)
        
        return cmd
    
    @staticmethod
    def build_wsl_matlab_command(matlab_exe: Path, matlab_cmd: str) -> list[str]:
        """
        Build a command to invoke Windows MATLAB from WSL.
        
        When running under WSL, we need to invoke MATLAB through cmd.exe
        to avoid "Exec format error" for Windows executables.
        
        Args:
            matlab_exe: Path to MATLAB executable (in WSL format)
            matlab_cmd: MATLAB batch command string
            
        Returns:
            Command list for subprocess.run
        """
        if MATLABConfig.is_wsl():
            # On WSL, invoke Windows MATLAB via PowerShell to avoid exec-format
            # errors and cmd.exe UNC working-directory issues.
            win_exe = str(matlab_exe).replace("/mnt/c", "C:").replace("/", "\\")
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"& '{win_exe}' -batch \"{matlab_cmd}\"",
            ]
        else:
            cmd = [str(matlab_exe), "-batch", matlab_cmd]
        
        return cmd
    
    @staticmethod
    def verify_toolboxes() -> dict[str, bool]:
        """
        Verify that required MATLAB toolboxes are installed.
        
        Returns:
            Dictionary with toolbox names as keys and installation status as values
        """
        matlab_exe = MATLABConfig.find_matlab_executable()
        if not matlab_exe:
            return {"matlab": False, "tusx": False, "kwave": False}
        
        verification_cmd = [
            str(matlab_exe),
            "-batch",
            "try; ver('Signal Processing Toolbox'); disp('MATLAB OK'); catch; disp('MATLAB FAILED'); end; exit;",
        ]
        
        try:
            result = subprocess.run(
                verification_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "matlab": "MATLAB OK" in result.stdout,
                "tusx": "TODO: check tusx",
                "kwave": "TODO: check kwave",
            }
        except subprocess.TimeoutExpired:
            return {"matlab": False, "tusx": False, "kwave": False}


def get_matlab_executable() -> Path:
    """Get MATLAB executable or raise error."""
    exe = MATLABConfig.find_matlab_executable()
    if exe is None:
        raise RuntimeError(
            "MATLAB not found. Please install MATLAB and add to PATH, "
            "or set MATLAB_ROOT environment variable."
        )
    return exe
