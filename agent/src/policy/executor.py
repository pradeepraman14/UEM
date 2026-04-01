"""Policy executor - receives policy payloads from server and applies them."""
import platform
from typing import Any

from agent.src.logger import get_logger

logger = get_logger(__name__)


async def execute_policy(policy_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    Apply a policy. Returns {'success': bool, 'message': str}.
    """
    logger.info("Applying policy", type=policy_type)

    handlers = {
        "password": _apply_password_policy,
        "screen_lock": _apply_screen_lock,
        "firewall": _apply_firewall_policy,
        "usb": _apply_usb_policy,
        "registry": _apply_registry_policy,
        "bitlocker": _apply_bitlocker_policy,
    }

    handler = handlers.get(policy_type)
    if not handler:
        return {"success": False, "message": f"Unknown policy type: {policy_type}"}

    try:
        return await handler(config)
    except Exception as e:
        logger.error("Policy execution failed", type=policy_type, error=str(e))
        return {"success": False, "message": str(e)}


async def _apply_password_policy(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "Password policy skipped (non-Windows)"}

    import subprocess
    commands = []

    min_len = config.get("min_length", 8)
    max_age = config.get("max_age_days", 90)
    min_age = config.get("min_age_days", 1)
    history = config.get("history_count", 5)
    lockout_thresh = config.get("lockout_threshold", 5)
    lockout_dur = config.get("lockout_duration_minutes", 30)
    complexity = 1 if config.get("require_uppercase") else 0

    script = f"""
net accounts /minpwlen:{min_len} /maxpwage:{max_age} /minpwage:{min_age} /uniquepw:{history}
net accounts /lockoutthreshold:{lockout_thresh} /lockoutduration:{lockout_dur}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0:
        return {"success": True, "message": "Password policy applied"}
    return {"success": False, "message": result.stderr}


async def _apply_screen_lock(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "Screen lock skipped (non-Windows)"}

    import subprocess

    timeout_min = config.get("idle_timeout_minutes", 15)
    timeout_sec = timeout_min * 60

    script = f"""
# Set screen timeout (AC and DC power)
powercfg /change standby-timeout-ac {timeout_min}
powercfg /change monitor-timeout-ac {timeout_min}
powercfg /change standby-timeout-dc {timeout_min}
powercfg /change monitor-timeout-dc {timeout_min}

# Require password on wake
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 1

# Set registry screensaver timeout
Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop" -Name "ScreenSaveTimeOut" -Value "{timeout_sec}"
Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop" -Name "ScreenSaverIsSecure" -Value "1"
Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop" -Name "ScreenSaveActive" -Value "1"
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=30
    )
    return {"success": result.returncode == 0, "message": result.stderr or "Screen lock applied"}


async def _apply_firewall_policy(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "Firewall skipped (non-Windows)"}

    import subprocess

    domain = config.get("domain_profile", "on")
    private = config.get("private_profile", "on")
    public = config.get("public_profile", "on")

    script = f"""
Set-NetFirewallProfile -Profile Domain -Enabled {domain.capitalize()}
Set-NetFirewallProfile -Profile Private -Enabled {private.capitalize()}
Set-NetFirewallProfile -Profile Public -Enabled {public.capitalize()}
"""

    # Custom firewall rules
    for rule in config.get("rules", []):
        action = rule.get("action", "Allow")
        direction = rule.get("direction", "Inbound")
        protocol = rule.get("protocol", "TCP")
        port = rule.get("local_port", "*")
        name = rule.get("name", "UEM Rule")
        script += f"""
if (-not (Get-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue)) {{
    New-NetFirewallRule -DisplayName "{name}" -Direction {direction} -Action {action} -Protocol {protocol} -LocalPort {port}
}}
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=30
    )
    return {"success": result.returncode == 0, "message": result.stderr or "Firewall policy applied"}


async def _apply_usb_policy(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "USB policy skipped (non-Windows)"}

    import subprocess

    block_removable = config.get("block_removable_storage", False)
    block_all = config.get("block_all_usb", False)

    if block_all:
        # Disable USB storage via registry
        script = """
Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR" -Name "Start" -Value 4 -Type DWord
"""
    elif block_removable:
        # Set USB storage to read-only
        script = """
Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\StorageDevicePolicies" -Name "WriteProtect" -Value 1 -Type DWord
"""
    else:
        # Enable USB storage
        script = """
Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR" -Name "Start" -Value 3 -Type DWord
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=30
    )
    return {"success": result.returncode == 0, "message": result.stderr or "USB policy applied"}


async def _apply_registry_policy(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "Registry policy skipped (non-Windows)"}

    try:
        import winreg

        results = []
        for entry in config.get("entries", []):
            hive_map = {
                "HKLM": winreg.HKEY_LOCAL_MACHINE,
                "HKCU": winreg.HKEY_CURRENT_USER,
                "HKCR": winreg.HKEY_CLASSES_ROOT,
            }
            hive_str = entry.get("hive", "HKLM")
            hive = hive_map.get(hive_str, winreg.HKEY_LOCAL_MACHINE)
            key_path = entry.get("key")
            value_name = entry.get("value_name")
            value_data = entry.get("value_data")
            value_type = entry.get("value_type", "DWORD")

            type_map = {
                "DWORD": winreg.REG_DWORD,
                "STRING": winreg.REG_SZ,
                "EXPAND_STRING": winreg.REG_EXPAND_SZ,
                "BINARY": winreg.REG_BINARY,
                "QWORD": winreg.REG_QWORD,
            }
            reg_type = type_map.get(value_type, winreg.REG_DWORD)

            try:
                with winreg.CreateKeyEx(hive, key_path, access=winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, value_name, 0, reg_type, value_data)
                results.append(f"Set {hive_str}\\{key_path}\\{value_name}")
            except Exception as e:
                results.append(f"FAILED {key_path}: {e}")

        return {"success": True, "message": f"Registry policy applied: {len(results)} entries"}
    except ImportError:
        return {"success": False, "message": "winreg not available"}


async def _apply_bitlocker_policy(config: dict[str, Any]) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"success": True, "message": "BitLocker skipped (non-Windows)"}

    require = config.get("require_encryption", True)
    if not require:
        return {"success": True, "message": "BitLocker policy: encryption not required"}

    import subprocess
    drive = config.get("drive", "C:")
    method = config.get("encryption_method", "XtsAes256")

    script = f"""
$vol = Get-BitLockerVolume -MountPoint "{drive}" -ErrorAction SilentlyContinue
if ($vol -and $vol.ProtectionStatus -eq "Off") {{
    Enable-BitLocker -MountPoint "{drive}" -EncryptionMethod {method} -RecoveryPasswordProtector
    Resume-BitLocker -MountPoint "{drive}"
    Write-Output "BitLocker enabled on {drive}"
}} else {{
    Write-Output "BitLocker already enabled or not applicable"
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=120
    )
    return {
        "success": result.returncode == 0,
        "message": result.stdout.strip() or result.stderr.strip() or "BitLocker command completed"
    }
