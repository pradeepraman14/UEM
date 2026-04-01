from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "uem",
    broker=settings.celery_broker_url,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.inventory_tasks",
        "app.workers.patch_tasks",
        "app.workers.compliance_tasks",
        "app.workers.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # Check for offline devices every 5 minutes
    "check-offline-devices": {
        "task": "app.workers.alert_tasks.check_offline_devices",
        "schedule": crontab(minute="*/5"),
    },
    # Run compliance check every hour
    "run-compliance-check": {
        "task": "app.workers.compliance_tasks.run_compliance_check_all",
        "schedule": crontab(minute=0),
    },
    # Check patch catalog daily at 2 AM
    "sync-patch-catalog": {
        "task": "app.workers.patch_tasks.sync_patch_catalog",
        "schedule": crontab(hour=2, minute=0),
    },
    # Generate daily report at 6 AM
    "daily-summary-report": {
        "task": "app.workers.alert_tasks.send_daily_summary",
        "schedule": crontab(hour=6, minute=0),
    },
    # Check expiring device certificates weekly
    "check-cert-expiry": {
        "task": "app.workers.alert_tasks.check_certificate_expiry",
        "schedule": crontab(day_of_week=1, hour=9, minute=0),
    },
}
