"""
Compliance checker - evaluates compliance rules locally and reports to server.
"""
import platform
import subprocess
from typing import Any

from agent.src.logger import get_logger

logger = get_logger(__name__)


async def evaluate_compliance(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate a list of compliance rules and return results."""
    results = []
    for rule in rules:
        result = await _evaluate_rule(rule)
        results.append(result)
    return results


async def _evaluate_rule(rule: dict[str, Any]) -> dict[str, Any]:
    rule_id = rule.get("rule_id") or rule.get("id")
    check_type = rule.get("check_type", "")
    operator = rule.get("operator", "equals")
    expected = rule.get("expected_value")

    actual_value = None
    status = "unknown"

    try:
        actual_value = await _get_actual_value(check_type)
        if actual_value is not None:
            status = _evaluate_operator(actual_value, operator, expected)
        else:
            status = "unknown"
    except Exception as e:
        logger.warning("Rule evaluation failed", rule_id=rule_id, error=str(e))
        status = "error"

    return {
        "rule_id": rule_id,
        "status": status,
        "actual_value": str(actual_value) if actual_value is not None else None,
    }


async def _get_actual_value(check_type: str) -> Any:
    """Get the actual system value for a given check type."""
    if check_type == "bitlocker_enabled":
        from agent.src.bitlocker import collect_bitlocker
        bl = collect_bitlocker()
        return str(bl.get("is_enabled", False)).lower()

    elif check_type == "defender_enabled":
        return _check_defender_enabled()

    elif check_type == "firewall_enabled":
        return _check_firewall_enabled()

    elif check_type == "screen_lock":
        return _get_screen_lock_timeout()

    elif check_type == "os_version":
        return platform.version()

    elif check_type == "os_build":
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                    return winreg.QueryValueEx(k, "CurrentBuildNumber")[0]
            except Exception:
                pass
        return platform.release()

    elif check_type == "patch_level":
        from agent.src.patch.wua import scan_missing_patches
        patches = scan_missing_patches()
        critical = sum(1 for p in patches if p.get("severity") == "critical")
        return f"{critical}_critical_missing" if critical == 0 else f"{critical}_critical_missing"

    return None


def _check_defender_enabled() -> str:
    if platform.system() != "Windows":
        return "unknown"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-MpComputerStatus).AntivirusEnabled"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().lower()
    except Exception:
        return "unknown"


def _check_firewall_enabled() -> str:
    if platform.system() != "Windows":
        return "unknown"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetFirewallProfile -Profile Domain).Enabled"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().lower()
    except Exception:
        return "unknown"


def _get_screen_lock_timeout() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop"
        ) as k:
            val = winreg.QueryValueEx(k, "ScreenSaveTimeOut")[0]
            return str(int(val) // 60)  # return in minutes
    except Exception:
        return None


def _evaluate_operator(actual: Any, operator: str, expected: Any) -> str:
    actual_str = str(actual).lower()
    expected_str = str(expected).lower() if expected else ""

    try:
        if operator == "equals":
            return "compliant" if actual_str == expected_str else "non_compliant"
        elif operator == "not_equals":
            return "compliant" if actual_str != expected_str else "non_compliant"
        elif operator == "contains":
            return "compliant" if any(e.strip() in actual_str for e in expected_str.split(",")) else "non_compliant"
        elif operator == "greater_than":
            return "compliant" if float(actual_str) > float(expected_str) else "non_compliant"
        elif operator == "less_than":
            return "compliant" if float(actual_str) < float(expected_str) else "non_compliant"
        elif operator == "exists":
            return "compliant" if actual else "non_compliant"
        elif operator == "not_exists":
            return "compliant" if not actual else "non_compliant"
    except Exception:
        pass

    return "unknown"
