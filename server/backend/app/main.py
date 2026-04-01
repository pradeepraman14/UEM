"""
UEM Platform - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.database import AsyncSessionLocal, engine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("Starting UEM Platform", version=settings.APP_VERSION)

    # Run database migrations / create initial data
    await _init_db()

    yield

    # Cleanup
    await engine.dispose()
    from app.redis_client import close_redis_pool
    await close_redis_pool()
    logger.info("UEM Platform shutdown complete")


async def _init_db():
    """Create tables and seed initial admin user if needed."""
    from sqlalchemy import select, text
    from app.models import (  # noqa: F401 - import all models to register them
        User, RefreshToken, Device, DeviceCertificate, DeviceGroup, DeviceGroupMember,
        HardwareInventory, InstalledSoftware, NetworkInterface,
        Policy, PolicyAssignment, Patch, DevicePatch, PatchApproval,
        SoftwarePackage, SoftwareDeployment, Command,
        ComplianceRule, DeviceCompliance, Alert, AuditLog, BitLockerStatus,
    )
    from app.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial admin
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            from app.core.security import hash_password
            admin = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                full_name="System Administrator",
                role="superadmin",
            )
            db.add(admin)
            await db.commit()
            logger.info("Created initial admin user", email=settings.INITIAL_ADMIN_EMAIL)

        # Seed default compliance rules
        await _seed_compliance_rules(db)


async def _seed_compliance_rules(db):
    from sqlalchemy import select
    from app.models.compliance import ComplianceRule

    result = await db.execute(select(ComplianceRule).limit(1))
    if result.scalar_one_or_none():
        return  # Already seeded

    default_rules = [
        ComplianceRule(
            name="Windows 10/11 Required",
            category="os",
            check_type="os_version",
            operator="contains",
            expected_value="Windows 10,Windows 11",
            severity="critical",
            remediation_hint="Upgrade to Windows 10 or Windows 11",
        ),
        ComplianceRule(
            name="BitLocker Encryption Required",
            category="security",
            check_type="bitlocker_enabled",
            operator="equals",
            expected_value="true",
            severity="critical",
            remediation_hint="Enable BitLocker on the OS drive",
        ),
        ComplianceRule(
            name="Windows Defender Enabled",
            category="antivirus",
            check_type="defender_enabled",
            operator="equals",
            expected_value="true",
            severity="high",
            remediation_hint="Enable Windows Defender / Microsoft Defender Antivirus",
        ),
        ComplianceRule(
            name="Firewall Enabled",
            category="security",
            check_type="firewall_enabled",
            operator="equals",
            expected_value="true",
            severity="high",
            remediation_hint="Enable Windows Firewall on all profiles",
        ),
        ComplianceRule(
            name="Screen Lock Timeout <= 15 min",
            category="security",
            check_type="screen_lock",
            operator="less_than",
            expected_value="15",
            severity="medium",
            remediation_hint="Set screen lock timeout to 15 minutes or less",
        ),
        ComplianceRule(
            name="Secure Boot Enabled",
            category="os",
            check_type="registry_value",
            operator="equals",
            expected_value="true",
            severity="medium",
            remediation_hint="Enable Secure Boot in BIOS/UEFI settings",
        ),
        ComplianceRule(
            name="No Critical Patches Missing",
            category="patch",
            check_type="patch_level",
            operator="equals",
            expected_value="0_critical_missing",
            severity="critical",
            remediation_hint="Install all critical Windows updates",
        ),
        ComplianceRule(
            name="TPM 2.0 Present",
            category="security",
            check_type="registry_value",
            operator="equals",
            expected_value="true",
            severity="low",
            remediation_hint="Device should have TPM 2.0 chip",
        ),
    ]
    for rule in default_rules:
        db.add(rule)
    await db.commit()
    logger.info("Seeded default compliance rules", count=len(default_rules))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Unified Endpoint Management Platform API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [settings.SERVER_BASE_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    from app.api.v1 import auth, devices, inventory, policies, commands, patches
    from app.api.v1 import software, bitlocker, compliance, alerts, users, groups, reports
    from app.api import websocket as ws_router

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(devices.router, prefix=api_prefix)
    app.include_router(inventory.router, prefix=api_prefix)
    app.include_router(policies.router, prefix=api_prefix)
    app.include_router(commands.router, prefix=api_prefix)
    app.include_router(patches.router, prefix=api_prefix)
    app.include_router(software.router, prefix=api_prefix)
    app.include_router(bitlocker.router, prefix=api_prefix)
    app.include_router(compliance.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(groups.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)
    app.include_router(ws_router.router)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "agents_online": 0,  # will be replaced with ws_manager.agent_count
        }

    @app.get("/api/v1/dashboard/stats", tags=["Dashboard"])
    async def dashboard_stats():
        from app.core.ws_manager import manager
        return {
            "agents_online": manager.agent_count,
            "console_connections": manager.console_count,
        }

    return app


app = create_app()
