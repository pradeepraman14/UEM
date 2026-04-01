"""Inventory orchestrator - collects all inventory data and sends to server."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from src.inventory.hardware import collect_hardware
from src.inventory.software import collect_software
from src.inventory.network import collect_network
from src.logger import get_logger

logger = get_logger(__name__)

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


class InventoryCollector:
    def __init__(self, device_id: str, interval: int, send_fn: SendFn):
        self.device_id = device_id
        self.interval = interval
        self.send_fn = send_fn
        self._running = False

    async def collect_and_send(self) -> None:
        logger.info("Starting inventory collection")
        payload: dict[str, Any] = {}

        # Collect in parallel using asyncio threads
        try:
            hw = await asyncio.get_event_loop().run_in_executor(None, collect_hardware)
            payload["hardware"] = hw
        except Exception as e:
            logger.error("Hardware collection failed", error=str(e))

        try:
            sw = await asyncio.get_event_loop().run_in_executor(None, collect_software)
            payload["software"] = sw
        except Exception as e:
            logger.error("Software collection failed", error=str(e))

        try:
            net = await asyncio.get_event_loop().run_in_executor(None, collect_network)
            payload["network"] = net
        except Exception as e:
            logger.error("Network collection failed", error=str(e))

        # BitLocker status
        try:
            from src.bitlocker import collect_bitlocker
            bl = await asyncio.get_event_loop().run_in_executor(None, collect_bitlocker)
            payload["bitlocker"] = bl
        except Exception as e:
            logger.debug("BitLocker collection failed", error=str(e))

        await self.send_fn({
            "type": "inventory_update",
            "device_id": self.device_id,
            "payload": payload,
        })
        logger.info("Inventory sent to server",
                    software_count=len(payload.get("software", [])),
                    network_interfaces=len(payload.get("network", [])))

    async def run(self) -> None:
        self._running = True
        # Initial collection
        await self.collect_and_send()

        while self._running:
            await asyncio.sleep(self.interval)
            await self.collect_and_send()

    def stop(self) -> None:
        self._running = False
