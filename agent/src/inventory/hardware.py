"""Hardware inventory collector via WMI (Windows) or psutil (fallback)."""
import platform
import subprocess
from datetime import date
from typing import Any

import psutil

from src.logger import get_logger

logger = get_logger(__name__)


def collect_hardware() -> dict[str, Any]:
    system = platform.system()
    if system == "Windows":
        return _collect_windows()
    return _collect_psutil()


def _collect_windows() -> dict[str, Any]:
    try:
        import wmi
        c = wmi.WMI()
    except ImportError:
        return _collect_psutil()

    result: dict[str, Any] = {}

    # CPU
    try:
        cpus = c.Win32_Processor()
        if cpus:
            cpu = cpus[0]
            result["cpu_name"] = cpu.Name.strip() if cpu.Name else None
            result["cpu_cores"] = cpu.NumberOfCores
            result["cpu_threads"] = cpu.NumberOfLogicalProcessors
            result["cpu_speed_mhz"] = cpu.MaxClockSpeed
            result["cpu_architecture"] = cpu.Architecture  # 9 = x64
    except Exception as e:
        logger.warning("CPU collection failed", error=str(e))

    # Memory
    try:
        mem = psutil.virtual_memory()
        result["ram_total_mb"] = mem.total // (1024 * 1024)
        result["ram_available_mb"] = mem.available // (1024 * 1024)
        physical_mem = c.Win32_PhysicalMemory()
        result["ram_slots"] = len(physical_mem)
    except Exception as e:
        logger.warning("Memory collection failed", error=str(e))

    # Disks
    try:
        disk_info = []
        logical_disks = c.Win32_LogicalDisk(DriveType=3)
        for d in logical_disks:
            size_gb = int(d.Size) // (1024 ** 3) if d.Size else 0
            free_gb = int(d.FreeSpace) // (1024 ** 3) if d.FreeSpace else 0
            # Try to get disk type
            disk_type = "HDD"
            try:
                for drive in c.Win32_DiskDrive():
                    if hasattr(drive, "MediaType") and drive.MediaType:
                        if "SSD" in str(drive.MediaType) or "Solid" in str(drive.MediaType):
                            disk_type = "SSD"
            except Exception:
                pass
            disk_info.append({
                "drive": d.DeviceID,
                "type": disk_type,
                "size_gb": size_gb,
                "free_gb": free_gb,
                "filesystem": d.FileSystem,
            })
        result["disk_info"] = disk_info
    except Exception as e:
        logger.warning("Disk collection failed", error=str(e))

    # GPU
    try:
        gpus = c.Win32_VideoController()
        result["gpu_info"] = [
            {
                "name": g.Name,
                "driver_version": g.DriverVersion,
                "vram_mb": int(g.AdapterRAM) // (1024 * 1024) if g.AdapterRAM else None,
            }
            for g in gpus
        ]
    except Exception as e:
        logger.warning("GPU collection failed", error=str(e))

    # BIOS
    try:
        bios_list = c.Win32_BIOS()
        if bios_list:
            bios = bios_list[0]
            result["bios_vendor"] = bios.Manufacturer
            result["bios_version"] = bios.SMBIOSBIOSVersion
            if bios.ReleaseDate:
                # WMI date format: YYYYMMDDHHMMSS.000000+000
                try:
                    d = bios.ReleaseDate[:8]
                    result["bios_date"] = date(int(d[:4]), int(d[4:6]), int(d[6:8])).isoformat()
                except Exception:
                    pass
    except Exception as e:
        logger.warning("BIOS collection failed", error=str(e))

    # Motherboard / System
    try:
        systems = c.Win32_ComputerSystem()
        if systems:
            s = systems[0]
            result["manufacturer"] = s.Manufacturer
            result["model"] = s.Model
            chassis_types = {1: "other", 3: "desktop", 4: "low_profile", 8: "tablet",
                             9: "laptop", 10: "notebook", 11: "handheld", 14: "sub_notebook",
                             15: "space_saving", 16: "lunch_box", 17: "main_server"}
            try:
                chassis = c.Win32_SystemEnclosure()
                chassis_type_id = chassis[0].ChassisTypes[0] if chassis else 3
                result["chassis_type"] = chassis_types.get(chassis_type_id, "desktop")
            except Exception:
                result["chassis_type"] = "desktop"
        boards = c.Win32_BaseBoard()
        if boards:
            b = boards[0]
            result["motherboard_manufacturer"] = b.Manufacturer
            result["motherboard_model"] = b.Product
    except Exception as e:
        logger.warning("System info collection failed", error=str(e))

    # TPM
    try:
        tpms = c.Win32_Tpm()
        if tpms:
            tpm = tpms[0]
            result["tpm_enabled"] = bool(tpm.IsActivated_InitialValue and tpm.IsEnabled_InitialValue)
            result["tpm_version"] = getattr(tpm, "SpecVersion", None)
    except Exception:
        result["tpm_enabled"] = False
        result["tpm_version"] = None

    # Secure Boot
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
        ) as k:
            val = winreg.QueryValueEx(k, "UEFISecureBootEnabled")[0]
            result["secure_boot"] = bool(val)
    except Exception:
        result["secure_boot"] = False

    # Virtualization
    try:
        cs = c.Win32_ComputerSystem()[0]
        result["virtualization_enabled"] = bool(
            getattr(cs, "HypervisorPresent", False) or
            getattr(cs, "VirtualizationFirmwareEnabled", False)
        )
    except Exception:
        result["virtualization_enabled"] = None

    # Battery
    try:
        batteries = c.Win32_Battery()
        if batteries:
            bat = batteries[0]
            result["battery_info"] = {
                "name": bat.Name,
                "status": bat.BatteryStatus,
                "charge_percent": bat.EstimatedChargeRemaining,
                "estimated_runtime_minutes": bat.EstimatedRunTime,
            }
    except Exception:
        result["battery_info"] = None

    return result


def _collect_psutil() -> dict[str, Any]:
    """Fallback collector using psutil (works on Linux/Mac for dev)."""
    result: dict[str, Any] = {}

    try:
        result["cpu_name"] = platform.processor() or "Unknown"
        result["cpu_cores"] = psutil.cpu_count(logical=False)
        result["cpu_threads"] = psutil.cpu_count(logical=True)
        result["cpu_speed_mhz"] = int(psutil.cpu_freq().max) if psutil.cpu_freq() else None
    except Exception:
        pass

    try:
        mem = psutil.virtual_memory()
        result["ram_total_mb"] = mem.total // (1024 * 1024)
        result["ram_available_mb"] = mem.available // (1024 * 1024)
    except Exception:
        pass

    try:
        disk_info = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_info.append({
                    "drive": part.mountpoint,
                    "type": "SSD",
                    "size_gb": usage.total // (1024 ** 3),
                    "free_gb": usage.free // (1024 ** 3),
                    "filesystem": part.fstype,
                })
            except PermissionError:
                pass
        result["disk_info"] = disk_info
    except Exception:
        pass

    result["manufacturer"] = "Unknown"
    result["model"] = platform.node()
    result["chassis_type"] = "desktop"

    return result
