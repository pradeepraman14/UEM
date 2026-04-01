"""
PyInstaller build script for UEM Agent.
Run: python build_installer.py
Output: dist/UEMAgent.exe (single-file executable)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"

PYINSTALLER_ARGS = [
    "pyinstaller",
    "--onefile",
    "--name", "UEMAgent",
    "--icon", str(ROOT / "installer" / "uem_agent.ico") if (ROOT / "installer" / "uem_agent.ico").exists() else "NONE",
    "--version-file", str(ROOT / "installer" / "version_info.txt"),
    # Hidden imports required by pywin32 and WMI
    "--hidden-import", "win32serviceutil",
    "--hidden-import", "win32service",
    "--hidden-import", "win32event",
    "--hidden-import", "servicemanager",
    "--hidden-import", "win32api",
    "--hidden-import", "win32con",
    "--hidden-import", "wmi",
    "--hidden-import", "pywintypes",
    "--hidden-import", "pythoncom",
    "--hidden-import", "win32com.client",
    "--hidden-import", "win32com.server.util",
    # Crypto / TLS
    "--hidden-import", "cryptography.hazmat.primitives.asymmetric.rsa",
    "--hidden-import", "cryptography.hazmat.primitives.serialization.pkcs12",
    "--hidden-import", "cryptography.x509",
    # Websockets
    "--hidden-import", "websockets.legacy.client",
    "--hidden-import", "websockets.legacy.server",
    # Other runtime imports
    "--hidden-import", "psutil",
    "--hidden-import", "aiohttp",
    "--hidden-import", "aiohttp.connector",
    "--hidden-import", "aiofiles",
    "--hidden-import", "anyio",
    "--hidden-import", "sniffio",
    # Collect all data from packages
    "--collect-data", "wmi",
    "--collect-data", "win32com",
    # Exclude unnecessary heavy packages
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "PIL",
    "--exclude-module", "numpy",
    "--exclude-module", "pandas",
    "--exclude-module", "scipy",
    # Runtime hook for pythoncom initialization in threads
    "--runtime-hook", str(ROOT / "installer" / "rt_hook_com.py"),
    "--distpath", str(DIST_DIR),
    "--workpath", str(BUILD_DIR),
    "--noconfirm",
    "--clean",
    str(ROOT / "agent_main.py"),
]


def clean():
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)
    spec = ROOT / "UEMAgent.spec"
    if spec.exists():
        spec.unlink()


def build():
    # Remove the icon arg if no icon exists
    args = PYINSTALLER_ARGS[:]
    icon_idx = args.index("--icon") if "--icon" in args else -1
    if icon_idx != -1:
        icon_value = args[icon_idx + 1]
        if icon_value == "NONE":
            args.pop(icon_idx)      # remove --icon
            args.pop(icon_idx)      # remove NONE

    # Remove version file arg if file doesn't exist
    vf_idx = args.index("--version-file") if "--version-file" in args else -1
    if vf_idx != -1:
        vf_path = Path(args[vf_idx + 1])
        if not vf_path.exists():
            args.pop(vf_idx)
            args.pop(vf_idx)

    # Remove runtime-hook arg if file doesn't exist
    rh_idx = args.index("--runtime-hook") if "--runtime-hook" in args else -1
    if rh_idx != -1:
        rh_path = Path(args[rh_idx + 1])
        if not rh_path.exists():
            args.pop(rh_idx)
            args.pop(rh_idx)

    print(f"[*] Building UEMAgent.exe ...")
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        print("[!] PyInstaller build failed.")
        sys.exit(result.returncode)

    exe = DIST_DIR / "UEMAgent.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1024 / 1024
        print(f"[+] Built: {exe}  ({size_mb:.1f} MB)")
    else:
        print("[!] Output exe not found.")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build UEM Agent installer binary")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts before building")
    args = parser.parse_args()

    if args.clean:
        clean()

    # Create installer dir if missing
    (ROOT / "installer").mkdir(exist_ok=True)

    build()
    print("[+] Done. Run installer/build_nsis.bat to create the full Windows installer.")
