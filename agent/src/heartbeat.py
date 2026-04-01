"""Periodic heartbeat sender."""
import asyncio
import socket
from datetime import datetime, timezone
from typing import Callable, Awaitable, Any

import psutil

from src.config import AGENT_VERSION
from src.logger import get_logger

logger = get_logger(__name__)

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


class HeartbeatService:
    def __init__(self, device_id: str, interval: int, send_fn: SendFn):
        self.device_id = device_id
        self.interval = interval
        self.send_fn = send_fn
        self._running = False

    def _collect(self) -> dict[str, Any]:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
        except Exception:
            cpu_usage = None

        try:
            mem = psutil.virtual_memory()
            ram_percent = mem.percent
        except Exception:
            ram_percent = None

        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
        except Exception:
            disk_percent = None

        try:
            uptime_seconds = int(psutil.time.time() - psutil.boot_time())
        except Exception:
            uptime_seconds = None

        # Get primary IP
        ip_address = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        # Get logged-in user
        logged_in_user = None
        try:
            users = psutil.users()
            if users:
                logged_in_user = users[-1].name
        except Exception:
            pass

        return {
            "ip_address": ip_address,
            "agent_version": AGENT_VERSION,
            "cpu_usage": cpu_usage,
            "ram_usage_percent": ram_percent,
            "disk_usage_percent": disk_percent,
            "uptime_seconds": uptime_seconds,
            "logged_in_user": logged_in_user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                payload = self._collect()
                await self.send_fn({
                    "type": "heartbeat",
                    "device_id": self.device_id,
                    "payload": payload,
                })
                logger.debug("Heartbeat sent", ip=payload.get("ip_address"))
            except Exception as e:
                logger.error("Heartbeat error", error=str(e))

            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False
