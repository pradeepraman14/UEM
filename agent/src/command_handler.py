"""
Handles incoming commands from the UEM server dispatched over WebSocket.
"""
import asyncio
import platform
import subprocess
from typing import Any, Callable, Awaitable

from src.config import AgentConfig
from src.logger import get_logger

logger = get_logger(__name__)

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


class CommandHandler:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.send_fn: SendFn | None = None  # set after WSClient is created

    async def handle(self, message: dict[str, Any]) -> None:
        msg_type = message.get("type")
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")

        if msg_type == "command_dispatch":
            asyncio.create_task(self._handle_command(correlation_id, payload))
        elif msg_type == "policy_push":
            asyncio.create_task(self._handle_policy(correlation_id, payload))
        elif msg_type == "patch_trigger":
            asyncio.create_task(self._handle_patch(correlation_id, payload))
        elif msg_type == "config_update":
            self._handle_config_update(payload)
        elif msg_type == "ping":
            if self.send_fn:
                await self.send_fn({"type": "pong", "device_id": self.config.device_id})

    async def _handle_command(self, correlation_id: str | None, payload: dict[str, Any]) -> None:
        cmd_type = payload.get("command_type")
        logger.info("Handling command", type=cmd_type, correlation_id=correlation_id)

        if not self.send_fn:
            return

        if cmd_type in ("shell", "powershell", "cmd"):
            from src.remote.shell import run_command
            shell = "powershell" if cmd_type in ("shell", "powershell") else "cmd"
            await run_command(
                correlation_id=correlation_id or "",
                device_id=self.config.device_id,
                command=payload.get("command", ""),
                shell_type=shell,
                send_fn=self.send_fn,
                timeout=payload.get("timeout", 120),
            )

        elif cmd_type == "file_upload":
            # Server is uploading a file TO the device
            dest = payload.get("destination_path", "C:\\Temp\\uem_upload")
            chunk_data = payload.get("data")
            chunk_index = payload.get("chunk_index", 0)
            is_last = payload.get("done", False)
            sha256 = payload.get("sha256")
            if chunk_data:
                from src.remote.file_transfer import receive_file_chunk
                await receive_file_chunk(dest, chunk_data, chunk_index, is_last, sha256)

        elif cmd_type == "file_download":
            # Device uploads a file TO the server
            source_path = payload.get("source_path")
            if source_path:
                from src.remote.file_transfer import send_file
                await send_file(
                    correlation_id=correlation_id or "",
                    device_id=self.config.device_id,
                    file_path=source_path,
                    send_fn=self.send_fn,
                )

        elif cmd_type == "reboot":
            delay = payload.get("delay_seconds", 0)
            force = payload.get("force", False)
            if platform.system() == "Windows":
                args = f"/r /t {delay}"
                if force:
                    args += " /f"
                subprocess.Popen(f"shutdown {args}", shell=True)
            await self.send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": self.config.device_id,
                "payload": {"success": True, "output": f"Reboot scheduled in {delay}s"},
            })

        elif cmd_type == "shutdown":
            if platform.system() == "Windows":
                subprocess.Popen("shutdown /s /t 0 /f", shell=True)
            await self.send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": self.config.device_id,
                "payload": {"success": True, "output": "Shutdown initiated"},
            })

        elif cmd_type == "lock":
            if platform.system() == "Windows":
                subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            await self.send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": self.config.device_id,
                "payload": {"success": True, "output": "Screen locked"},
            })

        elif cmd_type == "wipe":
            # Full device wipe - reset Windows to factory
            if platform.system() == "Windows":
                subprocess.Popen(
                    "systemreset --factoryreset",
                    shell=True
                )
            await self.send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": self.config.device_id,
                "payload": {"success": True, "output": "Device wipe initiated"},
            })

        elif cmd_type in ("install", "uninstall"):
            pkg = payload.get("package", {})
            if pkg.get("winget_id"):
                from src.patch.thirdparty import install_via_winget, uninstall_via_winget
                if cmd_type == "install":
                    result = install_via_winget(pkg["winget_id"])
                else:
                    result = uninstall_via_winget(pkg["winget_id"])
            elif pkg.get("download_url"):
                import httpx
                from pathlib import Path
                import tempfile
                tmp = Path(tempfile.gettempdir()) / (pkg.get("name", "pkg") + ".msi")
                async with httpx.AsyncClient(verify=False) as client:
                    resp = await client.get(pkg["download_url"])
                    tmp.write_bytes(resp.content)
                from src.patch.thirdparty import install_msi
                result = install_msi(str(tmp), pkg.get("install_args"))
            else:
                result = {"success": False, "message": "No valid install source"}

            await self.send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": self.config.device_id,
                "payload": {**result, "exit_code": result.get("exit_code", 0)},
            })

        elif cmd_type == "policy_apply":
            from src.policy.executor import execute_policy
            action = payload.get("action")
            if action == "enable_bitlocker":
                result = await execute_policy("bitlocker", payload)
                await self.send_fn({
                    "type": "command_result",
                    "correlation_id": correlation_id,
                    "device_id": self.config.device_id,
                    "payload": {**result, "exit_code": 0 if result["success"] else 1},
                })

    async def _handle_policy(self, correlation_id: str | None, payload: dict[str, Any]) -> None:
        from src.policy.executor import execute_policy
        policy_type = payload.get("policy_type", "")
        config = payload.get("config", {})
        result = await execute_policy(policy_type, config)
        logger.info("Policy applied", type=policy_type, success=result.get("success"))

    async def _handle_patch(self, correlation_id: str | None, payload: dict[str, Any]) -> None:
        from src.patch.wua import install_patches
        patch_ids = payload.get("patch_ids", [])
        install_all = payload.get("install_all_approved", False)
        result = install_patches(kb_ids=patch_ids or None, install_all=install_all)
        logger.info("Patch installation complete", result=result)

    def _handle_config_update(self, payload: dict[str, Any]) -> None:
        logger.info("Config update received")
        if payload.get("heartbeat_interval"):
            self.config.heartbeat_interval = int(payload["heartbeat_interval"])
        if payload.get("inventory_interval"):
            self.config.inventory_interval = int(payload["inventory_interval"])
        self.config.save({
            "device_id": self.config.device_id,
            "server_url": self.config.server_url,
            "ws_url": self.config.ws_url,
            "heartbeat_interval": self.config.heartbeat_interval,
            "inventory_interval": self.config.inventory_interval,
            "patch_check_interval": self.config.patch_check_interval,
        })
