"""
WebSocket Connection Manager.
Maintains a registry of connected agents and admin console connections.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class AgentConnection:
    def __init__(self, websocket: WebSocket, device_id: uuid.UUID):
        self.websocket = websocket
        self.device_id = device_id
        self.connected_at = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    async def send(self, message: dict[str, Any]) -> bool:
        """Send message, returns False if connection is closed."""
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return False
        async with self._lock:
            try:
                await self.websocket.send_text(json.dumps(message))
                return True
            except Exception:
                return False


class ConsoleConnection:
    def __init__(self, websocket: WebSocket, user_id: uuid.UUID):
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    async def send(self, message: dict[str, Any]) -> bool:
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return False
        async with self._lock:
            try:
                await self.websocket.send_text(json.dumps(message))
                return True
            except Exception:
                return False


class ConnectionManager:
    def __init__(self):
        # device_id -> AgentConnection
        self._agents: dict[str, AgentConnection] = {}
        # connection_id -> ConsoleConnection
        self._consoles: dict[str, ConsoleConnection] = {}
        self._lock = asyncio.Lock()

    # ── Agent connections ────────────────────────────────────

    async def connect_agent(self, websocket: WebSocket, device_id: uuid.UUID) -> AgentConnection:
        conn = AgentConnection(websocket, device_id)
        async with self._lock:
            self._agents[str(device_id)] = conn
        return conn

    async def disconnect_agent(self, device_id: uuid.UUID) -> None:
        async with self._lock:
            self._agents.pop(str(device_id), None)

    def get_agent(self, device_id: uuid.UUID) -> AgentConnection | None:
        return self._agents.get(str(device_id))

    def is_agent_connected(self, device_id: uuid.UUID) -> bool:
        return str(device_id) in self._agents

    def online_device_ids(self) -> list[str]:
        return list(self._agents.keys())

    async def send_to_agent(self, device_id: uuid.UUID, message: dict[str, Any]) -> bool:
        conn = self.get_agent(device_id)
        if conn:
            return await conn.send(message)
        return False

    async def broadcast_to_agents(self, message: dict[str, Any]) -> int:
        sent = 0
        for conn in list(self._agents.values()):
            if await conn.send(message):
                sent += 1
        return sent

    # ── Console connections ───────────────────────────────────

    async def connect_console(self, websocket: WebSocket, user_id: uuid.UUID) -> str:
        conn_id = str(uuid.uuid4())
        conn = ConsoleConnection(websocket, user_id)
        async with self._lock:
            self._consoles[conn_id] = conn
        return conn_id

    async def disconnect_console(self, conn_id: str) -> None:
        async with self._lock:
            self._consoles.pop(conn_id, None)

    async def broadcast_to_consoles(self, message: dict[str, Any]) -> int:
        sent = 0
        for conn in list(self._consoles.values()):
            if await conn.send(message):
                sent += 1
        return sent

    # ── Stats ──────────────────────────────────────────────────

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def console_count(self) -> int:
        return len(self._consoles)


# Global singleton
manager = ConnectionManager()
