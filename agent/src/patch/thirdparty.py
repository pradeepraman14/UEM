"""Third-party application management via winget and Chocolatey."""
import json
import platform
import subprocess
from typing import Any

from agent.src.logger import get_logger

logger = get_logger(__name__)


def install_via_winget(package_id: str, version: str | None = None) -> dict[str, Any]:
    """Install a package via winget."""
    if platform.system() != "Windows":
        return {"success": False, "message": "winget only available on Windows"}

    cmd = ["winget", "install", "--id", package_id, "--silent", "--accept-package-agreements",
           "--accept-source-agreements", "--disable-interactivity"]
    if version:
        cmd.extend(["--version", version])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "message": result.stdout.strip() or result.stderr.strip(),
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Installation timed out"}
    except FileNotFoundError:
        return {"success": False, "message": "winget not found on this system"}


def uninstall_via_winget(package_id: str) -> dict[str, Any]:
    cmd = ["winget", "uninstall", "--id", package_id, "--silent",
           "--disable-interactivity"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "message": result.stdout.strip() or result.stderr.strip(),
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def install_via_chocolatey(package_id: str, version: str | None = None) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": False, "message": "Chocolatey only available on Windows"}

    cmd = ["choco", "install", package_id, "-y", "--no-progress"]
    if version:
        cmd.extend(["--version", version])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "message": result.stdout.strip(),
            "exit_code": result.returncode,
        }
    except FileNotFoundError:
        return {"success": False, "message": "Chocolatey (choco) not found"}


def install_msi(msi_path: str, install_args: str | None = None) -> dict[str, Any]:
    """Silent MSI installation."""
    args = install_args or "/qn /norestart"
    cmd = ["msiexec", "/i", msi_path] + args.split()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode in (0, 3010),  # 3010 = success, reboot required
            "message": result.stdout or result.stderr,
            "exit_code": result.returncode,
            "reboot_required": result.returncode == 3010,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def install_exe(exe_path: str, install_args: str | None = None) -> dict[str, Any]:
    """Silent EXE installation."""
    args = (install_args or "/S /silent /quiet").split()
    cmd = [exe_path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode in (0, 3010),
            "message": result.stdout or result.stderr,
            "exit_code": result.returncode,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
