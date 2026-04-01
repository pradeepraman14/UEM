"""Network interface inventory collector."""
import platform
import socket
from typing import Any

import psutil

from src.logger import get_logger

logger = get_logger(__name__)


def collect_network() -> list[dict[str, Any]]:
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    for name, addr_list in addrs.items():
        iface: dict[str, Any] = {
            "name": name,
            "description": None,
            "mac_address": None,
            "ip_addresses": [],
            "ipv6_addresses": [],
            "gateway": None,
            "dns_servers": None,
            "dhcp_enabled": None,
            "dhcp_server": None,
            "is_connected": None,
            "speed_mbps": None,
            "adapter_type": "Ethernet",
        }

        for addr in addr_list:
            if addr.family == psutil.AF_LINK:
                iface["mac_address"] = addr.address
            elif addr.family == socket.AF_INET:
                iface["ip_addresses"].append({
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                })
            elif addr.family == socket.AF_INET6:
                iface["ipv6_addresses"].append(addr.address)

        # Speed and connection status from stats
        if name in stats:
            s = stats[name]
            iface["is_connected"] = s.isup
            iface["speed_mbps"] = s.speed if s.speed > 0 else None

        # Determine adapter type
        name_lower = name.lower()
        if "wi-fi" in name_lower or "wireless" in name_lower or "wlan" in name_lower:
            iface["adapter_type"] = "Wi-Fi"
        elif "loopback" in name_lower or name == "lo":
            continue  # skip loopback
        elif "bluetooth" in name_lower:
            iface["adapter_type"] = "Bluetooth"

        interfaces.append(iface)

    # Get gateway info on Windows
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            configs = c.Win32_NetworkAdapterConfiguration(IPEnabled=True)
            for cfg in configs:
                for iface in interfaces:
                    if iface.get("mac_address") and cfg.MACAddress:
                        if iface["mac_address"].upper() == cfg.MACAddress.upper():
                            if cfg.DefaultIPGateway:
                                iface["gateway"] = cfg.DefaultIPGateway[0]
                            if cfg.DNSServerSearchOrder:
                                iface["dns_servers"] = list(cfg.DNSServerSearchOrder)
                            iface["dhcp_enabled"] = cfg.DHCPEnabled
                            iface["dhcp_server"] = cfg.DHCPServer
                            iface["description"] = cfg.Description
                            break
        except Exception as e:
            logger.debug("WMI network info failed", error=str(e))

    return interfaces
