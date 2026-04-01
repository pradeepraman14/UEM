"""Software inventory collector - reads from Windows registry and AppX."""
import platform
import subprocess
from datetime import date
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)


def collect_software() -> list[dict[str, Any]]:
    system = platform.system()
    if system == "Windows":
        return _collect_windows()
    return _collect_linux()


def _collect_windows() -> list[dict[str, Any]]:
    """Collect installed software from Windows registry (32-bit and 64-bit)."""
    software = []
    seen = set()

    # Registry paths to check
    reg_paths = [
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "x64"),
        (r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "x86"),
    ]

    try:
        import winreg

        for reg_path, arch in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub_key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sub_key_name) as sub_key:
                                def get_val(name: str) -> str | None:
                                    try:
                                        return winreg.QueryValueEx(sub_key, name)[0]
                                    except FileNotFoundError:
                                        return None

                                name = get_val("DisplayName")
                                if not name:
                                    continue

                                version = get_val("DisplayVersion")
                                publisher = get_val("Publisher")
                                install_date_str = get_val("InstallDate")
                                install_location = get_val("InstallLocation")
                                uninstall_string = get_val("UninstallString")
                                size_str = get_val("EstimatedSize")

                                # Parse install date (YYYYMMDD format)
                                install_date = None
                                if install_date_str and len(install_date_str) == 8:
                                    try:
                                        install_date = date(
                                            int(install_date_str[:4]),
                                            int(install_date_str[4:6]),
                                            int(install_date_str[6:8]),
                                        ).isoformat()
                                    except Exception:
                                        pass

                                size_bytes = int(size_str) * 1024 if size_str else None

                                key_str = f"{name}|{version}"
                                if key_str in seen:
                                    continue
                                seen.add(key_str)

                                software.append({
                                    "name": name.strip(),
                                    "version": version,
                                    "publisher": publisher,
                                    "install_date": install_date,
                                    "install_location": install_location,
                                    "uninstall_string": uninstall_string,
                                    "size_bytes": size_bytes,
                                    "source": f"registry_{arch}",
                                    "is_64bit": arch == "x64",
                                })
                        except Exception:
                            continue
            except Exception as e:
                logger.warning("Registry software collection error", arch=arch, error=str(e))

    except ImportError:
        pass

    # Also collect AppX / UWP apps
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-AppxPackage | Select-Object Name, Version, Publisher | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            appx_apps = json.loads(result.stdout)
            if isinstance(appx_apps, dict):
                appx_apps = [appx_apps]
            for app in appx_apps:
                name = app.get("Name", "")
                if name and f"{name}|{app.get('Version')}" not in seen:
                    seen.add(f"{name}|{app.get('Version')}")
                    software.append({
                        "name": name,
                        "version": app.get("Version"),
                        "publisher": app.get("Publisher"),
                        "install_date": None,
                        "source": "appx",
                        "is_64bit": None,
                    })
    except Exception as e:
        logger.debug("AppX collection failed", error=str(e))

    logger.info("Software inventory collected", count=len(software))
    return software


def _collect_linux() -> list[dict[str, Any]]:
    """Linux fallback for dev/test."""
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            packages = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    packages.append({
                        "name": parts[0],
                        "version": parts[1],
                        "source": "dpkg",
                    })
            return packages
    except Exception:
        pass
    return []
