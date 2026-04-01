"""
WebSocket endpoints for agent and admin console connections.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.database import AsyncSessionLocal, get_db
from app.models.command import Command
from app.models.device import Device
from app.models.inventory import HardwareInventory, InstalledSoftware, NetworkInterface
from app.models.bitlocker import BitLockerStatus
from app.models.compliance import ComplianceRule, DeviceCompliance

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: uuid.UUID):
    """
    Persistent WebSocket connection for managed Windows agents.
    Authentication: Agent presents its device certificate via the TLS handshake (mTLS at nginx level).
    For development without mTLS, device_id path parameter is used directly.
    """
    await websocket.accept()
    conn = await manager.connect_agent(websocket, device_id)

    # Mark device online
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Device)
            .where(Device.id == device_id)
            .values(is_online=True, last_seen=datetime.now(timezone.utc))
        )
        await db.commit()

        # Broadcast to console clients
        await manager.broadcast_to_consoles({
            "type": "device_status_changed",
            "payload": {"device_id": str(device_id), "is_online": True},
        })

        # Send any pending commands
        result = await db.execute(
            select(Command).where(
                Command.device_id == device_id,
                Command.status == "pending",
            )
        )
        pending = result.scalars().all()
        for cmd in pending:
            sent = await conn.send({
                "type": "command_dispatch",
                "correlation_id": str(cmd.id),
                "payload": {
                    "command_id": str(cmd.id),
                    "command_type": cmd.command_type,
                    **cmd.payload,
                },
            })
            if sent:
                cmd.status = "sent"
                cmd.sent_at = datetime.now(timezone.utc)
        await db.commit()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")
            payload = message.get("payload", {})
            correlation_id = message.get("correlation_id")

            async with AsyncSessionLocal() as db:
                if msg_type == "heartbeat":
                    await _handle_heartbeat(db, device_id, payload)

                elif msg_type == "inventory_update":
                    await _handle_inventory(db, device_id, payload)

                elif msg_type == "command_result":
                    await _handle_command_result(db, device_id, payload, correlation_id)

                elif msg_type == "compliance_report":
                    await _handle_compliance_report(db, device_id, payload)

                elif msg_type == "alert":
                    await _handle_agent_alert(db, device_id, payload)

                elif msg_type == "file_chunk":
                    # Forward to console connection waiting for this file
                    await manager.broadcast_to_consoles({
                        "type": "file_chunk",
                        "device_id": str(device_id),
                        "correlation_id": correlation_id,
                        "payload": payload,
                    })

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect_agent(device_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Device)
                .where(Device.id == device_id)
                .values(is_online=False, last_seen=datetime.now(timezone.utc))
            )
            await db.commit()

        await manager.broadcast_to_consoles({
            "type": "device_status_changed",
            "payload": {"device_id": str(device_id), "is_online": False},
        })


async def _handle_heartbeat(db: AsyncSession, device_id: uuid.UUID, payload: dict):
    now = datetime.now(timezone.utc)
    updates = {
        "is_online": True,
        "last_seen": now,
        "last_heartbeat": now,
    }
    if payload.get("ip_address"):
        updates["ip_address"] = payload["ip_address"]
    if payload.get("agent_version"):
        updates["agent_version"] = payload["agent_version"]

    await db.execute(update(Device).where(Device.id == device_id).values(**updates))
    await db.commit()


async def _handle_inventory(db: AsyncSession, device_id: uuid.UUID, payload: dict):
    now = datetime.now(timezone.utc)

    # Hardware
    if hw_data := payload.get("hardware"):
        result = await db.execute(
            select(HardwareInventory).where(HardwareInventory.device_id == device_id)
        )
        hw = result.scalar_one_or_none()
        if hw:
            for k, v in hw_data.items():
                if hasattr(hw, k):
                    setattr(hw, k, v)
            hw.collected_at = now
        else:
            hw_data["device_id"] = device_id
            hw_data["collected_at"] = now
            db.add(HardwareInventory(**{k: v for k, v in hw_data.items() if hasattr(HardwareInventory, k)}))

    # Software - full replacement
    if sw_list := payload.get("software"):
        from sqlalchemy import delete
        await db.execute(
            delete(InstalledSoftware).where(InstalledSoftware.device_id == device_id)
        )
        for sw in sw_list:
            db.add(InstalledSoftware(
                device_id=device_id,
                display_name=sw.get("name", "Unknown"),
                publisher=sw.get("publisher"),
                version=sw.get("version"),
                install_date=sw.get("install_date"),
                source=sw.get("source"),
                is_64bit=sw.get("is_64bit"),
                size_bytes=sw.get("size_bytes"),
                collected_at=now,
            ))

    # Network interfaces
    if net_list := payload.get("network"):
        from sqlalchemy import delete
        await db.execute(
            delete(NetworkInterface).where(NetworkInterface.device_id == device_id)
        )
        for iface in net_list:
            db.add(NetworkInterface(
                device_id=device_id,
                name=iface.get("name", "Unknown"),
                description=iface.get("description"),
                mac_address=iface.get("mac_address"),
                ip_addresses=iface.get("ip_addresses"),
                ipv6_addresses=iface.get("ipv6_addresses"),
                gateway=iface.get("gateway"),
                dns_servers=iface.get("dns_servers"),
                dhcp_enabled=iface.get("dhcp_enabled"),
                is_connected=iface.get("is_connected"),
                speed_mbps=iface.get("speed_mbps"),
                adapter_type=iface.get("adapter_type"),
                collected_at=now,
            ))

    # BitLocker
    if bl_data := payload.get("bitlocker"):
        result = await db.execute(
            select(BitLockerStatus).where(BitLockerStatus.device_id == device_id)
        )
        bl = result.scalar_one_or_none()
        if bl:
            bl.is_enabled = bl_data.get("is_enabled", False)
            bl.os_volume_protected = bl_data.get("os_volume_protected")
            bl.encryption_method = bl_data.get("encryption_method")
            bl.encryption_percentage = bl_data.get("encryption_percentage")
            bl.volumes = bl_data.get("volumes")
            bl.collected_at = now
        else:
            db.add(BitLockerStatus(
                device_id=device_id,
                is_enabled=bl_data.get("is_enabled", False),
                os_volume_protected=bl_data.get("os_volume_protected"),
                encryption_method=bl_data.get("encryption_method"),
                encryption_percentage=bl_data.get("encryption_percentage"),
                volumes=bl_data.get("volumes"),
                collected_at=now,
            ))

    await db.commit()


async def _handle_command_result(
    db: AsyncSession, device_id: uuid.UUID, payload: dict, correlation_id: str | None
):
    if not correlation_id:
        return

    result = await db.execute(
        select(Command).where(Command.correlation_id == correlation_id)
    )
    cmd = result.scalar_one_or_none()
    if not cmd:
        return

    cmd.status = "completed" if payload.get("success") else "failed"
    cmd.output = payload.get("output")
    cmd.exit_code = payload.get("exit_code")
    cmd.error_message = payload.get("error")
    cmd.completed_at = datetime.now(timezone.utc)
    await db.commit()

    # Forward result to console
    await manager.broadcast_to_consoles({
        "type": "command_result",
        "device_id": str(device_id),
        "correlation_id": correlation_id,
        "payload": payload,
    })


async def _handle_compliance_report(db: AsyncSession, device_id: uuid.UUID, payload: dict):
    checks = payload.get("checks", [])
    now = datetime.now(timezone.utc)
    total = len(checks)
    compliant_count = sum(1 for c in checks if c.get("status") == "compliant")

    score = round(compliant_count / total * 100) if total else 0
    overall = "compliant" if score == 100 else ("non_compliant" if score < 70 else "compliant")

    await db.execute(
        update(Device)
        .where(Device.id == device_id)
        .values(
            compliance_status=overall,
            compliance_score=score,
            last_compliance_check=now,
        )
    )

    for check in checks:
        rule_id = check.get("rule_id")
        if not rule_id:
            continue
        result = await db.execute(
            select(DeviceCompliance).where(
                DeviceCompliance.device_id == device_id,
                DeviceCompliance.rule_id == rule_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.status = check.get("status", "unknown")
            existing.actual_value = check.get("actual_value")
            existing.checked_at = now
        else:
            db.add(DeviceCompliance(
                device_id=device_id,
                rule_id=rule_id,
                status=check.get("status", "unknown"),
                actual_value=check.get("actual_value"),
                checked_at=now,
            ))

    await db.commit()


async def _handle_agent_alert(db: AsyncSession, device_id: uuid.UUID, payload: dict):
    from app.models.alert import Alert
    alert = Alert(
        device_id=device_id,
        alert_type=payload.get("type", "custom"),
        severity=payload.get("severity", "medium"),
        title=payload.get("title", "Agent Alert"),
        message=payload.get("message", ""),
        details=payload.get("details"),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    await manager.broadcast_to_consoles({
        "type": "new_alert",
        "payload": {
            "alert_id": str(alert.id),
            "device_id": str(device_id),
            "severity": alert.severity,
            "title": alert.title,
        },
    })


@router.websocket("/ws/console")
async def console_ws(websocket: WebSocket):
    """Admin console WebSocket for real-time updates."""
    await websocket.accept()

    # Authenticate via JWT token sent as first message
    try:
        auth_msg = await websocket.receive_text()
        auth_data = json.loads(auth_msg)
        token = auth_data.get("token")
        if not token:
            await websocket.close(code=4001)
            return

        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, Exception):
        await websocket.close(code=4001)
        return

    conn_id = await manager.connect_console(websocket, user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            # Console can send pings or subscribe to specific device streams
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect_console(conn_id)
