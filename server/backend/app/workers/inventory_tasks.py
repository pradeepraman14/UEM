"""Inventory collection Celery tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.inventory_tasks.trigger_inventory_collection")
def trigger_inventory_collection(device_id: str | None = None):
    """Trigger inventory collection on a specific device or all online devices."""
    import asyncio
    asyncio.run(_trigger_inventory(device_id))


async def _trigger_inventory(device_id: str | None):
    import uuid
    from app.core.ws_manager import manager

    msg = {
        "type": "command_dispatch",
        "payload": {"command_type": "inventory_collect"},
    }

    if device_id:
        await manager.send_to_agent(uuid.UUID(device_id), msg)
    else:
        await manager.broadcast_to_agents(msg)
