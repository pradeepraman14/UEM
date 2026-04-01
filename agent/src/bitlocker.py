"""BitLocker status collection and management."""
import platform
import subprocess
import json
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)


def collect_bitlocker() -> dict[str, Any]:
    """Collect BitLocker status for all drives."""
    if platform.system() != "Windows":
        return {"is_enabled": False, "volumes": [], "os_volume_protected": False}

    script = """
$volumes = Get-BitLockerVolume -ErrorAction SilentlyContinue
if (-not $volumes) { Write-Output "[]"; exit 0 }

$result = @()
foreach ($vol in $volumes) {
    $result += @{
        drive = $vol.MountPoint
        protection_status = if ($vol.ProtectionStatus -eq "On") { "on" } else { "off" }
        encryption_method = $vol.EncryptionMethod.ToString()
        encryption_percentage = $vol.EncryptionPercentage
        lock_status = if ($vol.LockStatus -eq "Unlocked") { "unlocked" } else { "locked" }
        volume_type = $vol.VolumeType.ToString()
        recovery_key_ids = @($vol.KeyProtector | Where-Object {$_.KeyProtectorType -eq "RecoveryPassword"} | ForEach-Object { $_.KeyProtectorId })
    }
}
$result | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {"is_enabled": False, "volumes": [], "os_volume_protected": False}

        volumes = json.loads(result.stdout.strip())
        if isinstance(volumes, dict):
            volumes = [volumes]

        is_enabled = any(v.get("protection_status") == "on" for v in volumes)
        os_vol = next((v for v in volumes if v.get("volume_type", "").lower() in ("operatingsystem", "fixeddisk")), None)
        os_protected = os_vol and os_vol.get("protection_status") == "on" if os_vol else False
        encryption_method = os_vol.get("encryption_method") if os_vol else None
        encryption_pct = os_vol.get("encryption_percentage") if os_vol else None

        return {
            "is_enabled": is_enabled,
            "os_volume_protected": bool(os_protected),
            "encryption_method": encryption_method,
            "encryption_percentage": encryption_pct,
            "volumes": volumes,
        }
    except Exception as e:
        logger.error("BitLocker collection failed", error=str(e))
        return {"is_enabled": False, "volumes": [], "os_volume_protected": False}


def get_recovery_keys() -> list[dict[str, Any]]:
    """Get BitLocker recovery keys for escrow."""
    if platform.system() != "Windows":
        return []

    script = """
$keys = @()
$vols = Get-BitLockerVolume -ErrorAction SilentlyContinue
foreach ($vol in $vols) {
    foreach ($kp in $vol.KeyProtector) {
        if ($kp.KeyProtectorType -eq "RecoveryPassword") {
            $keys += @{
                drive = $vol.MountPoint
                key_id = $kp.KeyProtectorId
                recovery_password = $kp.RecoveryPassword
            }
        }
    }
}
$keys | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            keys = json.loads(result.stdout.strip())
            if isinstance(keys, dict):
                keys = [keys]
            return keys
    except Exception as e:
        logger.error("Recovery key collection failed", error=str(e))
    return []
