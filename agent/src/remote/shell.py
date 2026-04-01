"""Remote shell execution - runs commands and streams output back via WebSocket."""
import asyncio
import subprocess
import platform
from typing import Any, Callable, Awaitable

from src.logger import get_logger

logger = get_logger(__name__)

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


async def run_command(
    correlation_id: str,
    device_id: str,
    command: str,
    shell_type: str,
    send_fn: SendFn,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    Execute a shell command and stream output back over WebSocket.
    Returns final result dict.
    """
    logger.info("Executing remote command", shell=shell_type, cmd=command[:100])

    if shell_type == "powershell":
        if platform.system() == "Windows":
            cmd_args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            cmd_args = ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command]
    elif shell_type == "cmd":
        cmd_args = ["cmd", "/c", command]
    else:
        cmd_args = ["/bin/sh", "-c", command]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_chunks = []

        async def read_output():
            while True:
                chunk = await proc.stdout.read(4096)  # type: ignore
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                output_chunks.append(text)
                # Stream output in real-time
                await send_fn({
                    "type": "command_result",
                    "correlation_id": correlation_id,
                    "device_id": device_id,
                    "payload": {
                        "type": "stdout_chunk",
                        "data": text,
                    },
                })

        try:
            await asyncio.wait_for(
                asyncio.gather(read_output(), proc.wait()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await send_fn({
                "type": "command_result",
                "correlation_id": correlation_id,
                "device_id": device_id,
                "payload": {
                    "success": False,
                    "output": "".join(output_chunks),
                    "exit_code": -1,
                    "error": f"Command timed out after {timeout}s",
                },
            })
            return {"success": False, "error": "Timeout", "exit_code": -1}

        exit_code = proc.returncode
        full_output = "".join(output_chunks)

        result = {
            "success": exit_code == 0,
            "output": full_output,
            "exit_code": exit_code,
            "error": None if exit_code == 0 else f"Command exited with code {exit_code}",
        }

        await send_fn({
            "type": "command_result",
            "correlation_id": correlation_id,
            "device_id": device_id,
            "payload": result,
        })

        return result

    except Exception as e:
        error_result = {"success": False, "output": "", "exit_code": -1, "error": str(e)}
        await send_fn({
            "type": "command_result",
            "correlation_id": correlation_id,
            "device_id": device_id,
            "payload": error_result,
        })
        return error_result
