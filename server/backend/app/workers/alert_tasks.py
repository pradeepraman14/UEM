"""Alert and notification Celery tasks."""
from datetime import datetime, timezone, timedelta

from celery import shared_task
from sqlalchemy import select, update

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.device import Device
from app.models.alert import Alert
from app.models.device import DeviceCertificate


@celery_app.task(name="app.workers.alert_tasks.check_offline_devices")
def check_offline_devices():
    """Alert when devices haven't sent a heartbeat in too long."""
    import asyncio
    asyncio.run(_check_offline_devices())


async def _check_offline_devices():
    threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device).where(
                Device.status == "active",
                Device.is_online == True,
                Device.last_heartbeat < threshold,
            )
        )
        stale_devices = result.scalars().all()

        for device in stale_devices:
            # Mark offline
            device.is_online = False

            # Create alert if not already open
            existing = await db.execute(
                select(Alert).where(
                    Alert.device_id == device.id,
                    Alert.alert_type == "device_offline",
                    Alert.status == "open",
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Alert(
                    device_id=device.id,
                    alert_type="device_offline",
                    severity="medium",
                    title=f"Device Offline: {device.hostname}",
                    message=f"Device {device.hostname} has not reported a heartbeat since "
                            f"{device.last_heartbeat.isoformat() if device.last_heartbeat else 'never'}",
                ))

        await db.commit()


@celery_app.task(name="app.workers.alert_tasks.check_certificate_expiry")
def check_certificate_expiry():
    import asyncio
    asyncio.run(_check_certificate_expiry())


async def _check_certificate_expiry():
    warning_threshold = datetime.now(timezone.utc) + timedelta(days=30)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DeviceCertificate)
            .where(
                DeviceCertificate.is_active == True,
                DeviceCertificate.expires_at < warning_threshold,
                DeviceCertificate.revoked_at.is_(None),
            )
        )
        expiring = result.scalars().all()

        for cert in expiring:
            days_left = (cert.expires_at - datetime.now(timezone.utc)).days
            existing = await db.execute(
                select(Alert).where(
                    Alert.device_id == cert.device_id,
                    Alert.alert_type == "certificate_expiry",
                    Alert.status == "open",
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Alert(
                    device_id=cert.device_id,
                    alert_type="certificate_expiry",
                    severity="high" if days_left <= 7 else "medium",
                    title=f"Device Certificate Expiring in {days_left} Days",
                    message=f"The mTLS client certificate expires on {cert.expires_at.date()}. "
                            f"Re-enroll the device to renew.",
                ))

        await db.commit()


@celery_app.task(name="app.workers.alert_tasks.send_daily_summary")
def send_daily_summary():
    """Send daily summary email if SMTP is configured."""
    import asyncio
    asyncio.run(_send_daily_summary())


async def _send_daily_summary():
    from app.config import settings
    if not settings.SMTP_USER:
        return  # SMTP not configured

    async with AsyncSessionLocal() as db:
        from sqlalchemy import func
        from app.models.device import Device
        from app.models.alert import Alert

        total = (await db.execute(select(func.count(Device.id)))).scalar()
        online = (await db.execute(
            select(func.count(Device.id)).where(Device.is_online == True)
        )).scalar()
        open_alerts = (await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "open")
        )).scalar()
        critical = (await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "open", Alert.severity == "critical")
        )).scalar()

    # Send email (simplified - would use aiosmtplib in production)
    subject = f"UEM Daily Summary - {datetime.now().strftime('%Y-%m-%d')}"
    body = f"""
UEM Platform Daily Summary
--------------------------
Total Devices: {total}
Online Devices: {online}
Open Alerts: {open_alerts} ({critical} critical)
"""
    # TODO: integrate aiosmtplib for actual email sending
