"""Patch management Celery tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.patch_tasks.sync_patch_catalog")
def sync_patch_catalog():
    """Trigger patch scanning on all online devices and collect results."""
    import asyncio
    asyncio.run(_sync_patch_catalog())


async def _sync_patch_catalog():
    from app.core.ws_manager import manager
    # Ask all online agents to scan and report missing patches
    await manager.broadcast_to_agents({
        "type": "command_dispatch",
        "payload": {
            "command_type": "patch_scan",
        },
    })


@celery_app.task(name="app.workers.patch_tasks.deploy_approved_patches")
def deploy_approved_patches(device_id: str):
    """Deploy all approved patches to a specific device."""
    import asyncio
    asyncio.run(_deploy_to_device(device_id))


async def _deploy_to_device(device_id: str):
    import uuid
    from app.core.ws_manager import manager
    await manager.send_to_agent(
        uuid.UUID(device_id),
        {
            "type": "patch_trigger",
            "payload": {"install_all_approved": True},
        },
    )
