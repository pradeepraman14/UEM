import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user
from app.models.software import SoftwarePackage, SoftwareDeployment
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/software", tags=["Software Management"])


@router.get("")
async def list_packages(
    _: Annotated[User, require_permission("software:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=200),
):
    query = select(SoftwarePackage).where(SoftwarePackage.is_active == True)
    if category:
        query = query.where(SoftwarePackage.category == category)
    if search:
        query = query.where(SoftwarePackage.name.ilike(f"%{search}%"))
    result = await db.execute(query.order_by(SoftwarePackage.name).limit(limit))
    packages = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "publisher": p.publisher,
            "version": p.version,
            "category": p.category,
            "install_type": p.install_type,
            "file_size_bytes": p.file_size_bytes,
            "reboot_required": p.reboot_required,
            "icon_url": p.icon_url,
        }
        for p in packages
    ]


@router.post("/upload", status_code=201)
async def upload_package(
    current_user: Annotated[User, require_permission("software:upload")],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str = Form(...),
    version: str = Form(...),
    install_type: str = Form(...),
    publisher: str | None = Form(None),
    category: str | None = Form(None),
    install_args: str | None = Form(None),
    uninstall_args: str | None = Form(None),
    winget_id: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    import aiofiles
    import hashlib
    import os
    from pathlib import Path

    packages_dir = Path(settings.PACKAGES_DIR)
    packages_dir.mkdir(parents=True, exist_ok=True)

    file_path = None
    file_size = None
    sha256_hash = None
    filename = None

    if file:
        filename = file.filename
        dest_path = packages_dir / f"{uuid.uuid4()}_{filename}"
        hasher = hashlib.sha256()
        size = 0
        async with aiofiles.open(dest_path, "wb") as f:
            while chunk := await file.read(65536):
                await f.write(chunk)
                hasher.update(chunk)
                size += len(chunk)
        file_path = str(dest_path)
        file_size = size
        sha256_hash = hasher.hexdigest()

    package = SoftwarePackage(
        name=name,
        version=version,
        install_type=install_type,
        publisher=publisher,
        category=category,
        install_args=install_args,
        uninstall_args=uninstall_args,
        winget_id=winget_id,
        filename=filename,
        file_path=file_path,
        file_size_bytes=file_size,
        sha256_hash=sha256_hash,
        uploaded_by_id=current_user.id,
    )
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return {"id": str(package.id), "message": "Package uploaded"}


@router.post("/{package_id}/deploy")
async def deploy_package(
    package_id: uuid.UUID,
    current_user: Annotated[User, require_permission("software:deploy")],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_ids: list[uuid.UUID] = ...,
    action: str = "install",
):
    result = await db.execute(select(SoftwarePackage).where(SoftwarePackage.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    dispatched = 0
    for device_id in device_ids:
        deployment = SoftwareDeployment(
            package_id=package_id,
            device_id=device_id,
            action=action,
            initiated_by_id=current_user.id,
        )
        db.add(deployment)
        await db.flush()

        sent = await ws_manager.send_to_agent(
            device_id,
            {
                "type": "command_dispatch",
                "payload": {
                    "command_type": action,
                    "deployment_id": str(deployment.id),
                    "package": {
                        "id": str(package.id),
                        "name": package.name,
                        "version": package.version,
                        "install_type": package.install_type,
                        "install_args": package.install_args,
                        "winget_id": package.winget_id,
                        "choco_id": package.choco_id,
                        "download_url": (
                            f"{settings.SERVER_BASE_URL}/api/v1/software/{package_id}/download"
                            if package.file_path else None
                        ),
                    },
                },
            },
        )
        if sent:
            deployment.status = "sent"
            dispatched += 1

    await db.commit()
    return {
        "message": f"Deployment initiated on {dispatched} devices",
        "devices_notified": dispatched,
    }
