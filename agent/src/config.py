"""
UEM Agent Configuration.
Loaded from:
  1. C:\\ProgramData\\UEMAgent\\config.json  (primary, written at enrollment)
  2. Environment variables (fallback/override)
  3. Default values
"""
import json
import platform
from pathlib import Path
from typing import Any

# Config file location
if platform.system() == "Windows":
    CONFIG_DIR = Path("C:/ProgramData/UEMAgent")
else:
    CONFIG_DIR = Path("/etc/uem-agent")  # Linux dev

CONFIG_FILE = CONFIG_DIR / "config.json"
CERT_DIR = CONFIG_DIR / "certs"
LOG_DIR = CONFIG_DIR / "logs"

AGENT_VERSION = "1.0.0"


class AgentConfig:
    """Runtime agent configuration."""

    def __init__(self):
        self.server_url: str = ""
        self.ws_url: str = ""
        self.device_id: str = ""
        self.cert_path: Path = CERT_DIR / "device.crt"
        self.key_path: Path = CERT_DIR / "device.key"
        self.ca_cert_path: Path = CERT_DIR / "ca.crt"
        self.heartbeat_interval: int = 30
        self.inventory_interval: int = 3600
        self.patch_check_interval: int = 86400
        self.log_level: str = "INFO"
        self.enrollment_token: str = ""

    def load(self) -> bool:
        """Load config from disk. Returns True if enrolled."""
        if not CONFIG_FILE.exists():
            return False
        try:
            data: dict[str, Any] = json.loads(CONFIG_FILE.read_text())
            self.server_url = data.get("server_url", "")
            self.ws_url = data.get("ws_url", "")
            self.device_id = data.get("device_id", "")
            self.heartbeat_interval = data.get("heartbeat_interval", 30)
            self.inventory_interval = data.get("inventory_interval", 3600)
            self.patch_check_interval = data.get("patch_check_interval", 86400)
            self.log_level = data.get("log_level", "INFO")
            return bool(self.server_url and self.device_id)
        except Exception:
            return False

    def save(self, data: dict[str, Any]) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
        # Reload
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def is_enrolled(self) -> bool:
        return bool(self.device_id and self.server_url and self.cert_path.exists())
