"""Chunked file transfer over WebSocket."""
import asyncio
import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Awaitable

from agent.src.logger import get_logger

logger = get_logger(__name__)

SendFn = Callable[[dict[str, Any]], Awaitable[None]]
CHUNK_SIZE = 65536  # 64 KB


async def send_file(
    correlation_id: str,
    device_id: str,
    file_path: str,
    send_fn: SendFn,
) -> dict[str, Any]:
    """Upload a file from the device to the server (chunked over WebSocket)."""
    path = Path(file_path)
    if not path.exists():
        err = {"success": False, "error": f"File not found: {file_path}"}
        await send_fn({
            "type": "file_chunk",
            "correlation_id": correlation_id,
            "device_id": device_id,
            "payload": {**err, "done": True},
        })
        return err

    file_size = path.stat().st_size
    hasher = hashlib.sha256()
    chunk_index = 0

    await send_fn({
        "type": "file_chunk",
        "correlation_id": correlation_id,
        "device_id": device_id,
        "payload": {
            "filename": path.name,
            "file_size": file_size,
            "total_chunks": (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE,
            "start": True,
        },
    })

    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            encoded = base64.b64encode(chunk).decode()
            await send_fn({
                "type": "file_chunk",
                "correlation_id": correlation_id,
                "device_id": device_id,
                "payload": {
                    "chunk_index": chunk_index,
                    "data": encoded,
                },
            })
            chunk_index += 1
            await asyncio.sleep(0)  # yield control

    sha256 = hasher.hexdigest()
    await send_fn({
        "type": "file_chunk",
        "correlation_id": correlation_id,
        "device_id": device_id,
        "payload": {
            "done": True,
            "success": True,
            "sha256": sha256,
            "total_chunks": chunk_index,
        },
    })

    return {"success": True, "sha256": sha256, "size": file_size}


async def receive_file_chunk(
    destination_path: str,
    chunk_data: str,
    chunk_index: int,
    is_last: bool = False,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Receive a file chunk sent from the server."""
    path = Path(destination_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = "ab" if chunk_index > 0 else "wb"
    chunk_bytes = base64.b64decode(chunk_data)

    with open(path, mode) as f:
        f.write(chunk_bytes)

    if is_last and expected_sha256:
        with open(path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        if actual != expected_sha256:
            return {"success": False, "error": "SHA256 mismatch - file corrupted"}

    return {"success": True, "done": is_last}
