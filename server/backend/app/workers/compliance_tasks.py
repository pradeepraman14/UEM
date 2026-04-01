"""Compliance evaluation Celery tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.compliance_tasks.run_compliance_check_all")
def run_compliance_check_all():
    """Push compliance check request to all online devices."""
    import asyncio
    asyncio.run(_run_compliance_check_all())


async def _run_compliance_check_all():
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.device import Device
    from app.models.compliance import ComplianceRule
    from app.core.ws_manager import manager

    async with AsyncSessionLocal() as db:
        rules = (await db.execute(
            select(ComplianceRule).where(ComplianceRule.is_active == True)
        )).scalars().all()

        rules_payload = [
            {
                "rule_id": str(r.id),
                "check_type": r.check_type,
                "operator": r.operator,
                "expected_value": r.expected_value,
            }
            for r in rules
        ]

    # Dispatch compliance check to all online agents
    await manager.broadcast_to_agents({
        "type": "command_dispatch",
        "payload": {
            "command_type": "compliance_check",
            "rules": rules_payload,
        },
    })
