"""
Windows Service wrapper for the UEM Agent.
Uses pywin32 to register as a Windows Service that starts automatically.
"""
import asyncio
import platform
import sys

if platform.system() == "Windows":
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager


from src.config import AgentConfig
from src.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def run_agent(config: AgentConfig) -> None:
    """Main agent async loop - starts all background services."""
    from src.transport.ws_client import WSClient
    from src.heartbeat import HeartbeatService
    from src.inventory.collector import InventoryCollector
    from src.command_handler import CommandHandler

    handler = CommandHandler(config)

    ws_client = WSClient(
        ws_url=config.ws_url,
        device_id=config.device_id,
        cert_path=config.cert_path,
        key_path=config.key_path,
        ca_cert_path=config.ca_cert_path,
        on_message=handler.handle,
    )

    heartbeat = HeartbeatService(
        device_id=config.device_id,
        interval=config.heartbeat_interval,
        send_fn=ws_client.send,
    )

    inventory = InventoryCollector(
        device_id=config.device_id,
        interval=config.inventory_interval,
        send_fn=ws_client.send,
    )

    handler.send_fn = ws_client.send

    await asyncio.gather(
        ws_client.run(),
        heartbeat.run(),
        inventory.run(),
    )


if platform.system() == "Windows":
    class UEMAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "UEMAgent"
        _svc_display_name_ = "UEM Agent"
        _svc_description_ = "Unified Endpoint Management Agent - Managed by UEM Platform"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._loop: asyncio.AbstractEventLoop | None = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            config = AgentConfig()
            setup_logging(config.log_level)

            if not config.load():
                servicemanager.LogErrorMsg("UEM Agent: Not enrolled. Run enrollment first.")
                return

            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(run_agent(config))
            except Exception as e:
                logger.error("Service error", error=str(e))
            finally:
                self._loop.close()

    def main():
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(UEMAgentService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(UEMAgentService)

else:
    # Non-Windows entry point (dev/Linux)
    def main():
        config = AgentConfig()
        setup_logging("DEBUG", log_to_file=False)

        if not config.load():
            print("Agent not enrolled. Run: python -m agent.src.enroll_cli")
            return

        asyncio.run(run_agent(config))


if __name__ == "__main__":
    main()
