"""
Reconnecting WebSocket client for the UEM agent.
Handles authentication, message dispatch, and exponential backoff reconnection.
"""
import asyncio
import json
import ssl
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.logger import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]

RECONNECT_BASE = 5
RECONNECT_MAX = 60


class WSClient:
    def __init__(
        self,
        ws_url: str,
        device_id: str,
        cert_path: Path,
        key_path: Path,
        ca_cert_path: Path,
        on_message: MessageHandler,
    ):
        self.ws_url = ws_url
        self.device_id = device_id
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_cert_path = ca_cert_path
        self.on_message = on_message
        self._ws = None
        self._running = False
        self._send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reconnect_delay = RECONNECT_BASE

    def _build_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(str(self.ca_cert_path))
        ctx.load_cert_chain(str(self.cert_path), str(self.key_path))
        ctx.check_hostname = False  # use certificate pinning instead
        return ctx

    async def send(self, message: dict[str, Any]) -> None:
        await self._send_queue.put(message)

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                ssl_ctx = self._build_ssl_context() if self.cert_path.exists() else True
                logger.info("Connecting to server", url=self.ws_url)
                async with websockets.connect(
                    self.ws_url,
                    ssl=ssl_ctx,
                    ping_interval=20,
                    ping_timeout=30,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024,  # 10 MB max message
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = RECONNECT_BASE
                    logger.info("Connected to UEM server")

                    await asyncio.gather(
                        self._receive_loop(ws),
                        self._send_loop(ws),
                    )
            except (ConnectionClosed, WebSocketException, OSError, asyncio.TimeoutError) as e:
                logger.warning("WebSocket disconnected", error=str(e))
            except Exception as e:
                logger.error("Unexpected WS error", error=str(e))
            finally:
                self._ws = None

            if not self._running:
                break

            logger.info("Reconnecting", delay=self._reconnect_delay)
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 1.5, RECONNECT_MAX)

    async def _receive_loop(self, ws) -> None:
        async for raw in ws:
            try:
                message = json.loads(raw)
                await self.on_message(message)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.error("Error handling message", error=str(e))

    async def _send_loop(self, ws) -> None:
        while True:
            message = await self._send_queue.get()
            try:
                await ws.send(json.dumps(message))
            except Exception as e:
                logger.warning("Failed to send message", error=str(e))
                # Re-queue
                await self._send_queue.put(message)
                break

    def stop(self) -> None:
        self._running = False
        if self._ws:
            asyncio.create_task(self._ws.close())
