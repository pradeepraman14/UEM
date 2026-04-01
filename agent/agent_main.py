"""
UEM Agent - Windows Service Entry Point.

Usage:
  Install service:    python agent_main.py install
  Start service:      python agent_main.py start
  Stop service:       python agent_main.py stop
  Remove service:     python agent_main.py remove
  Run standalone:     python agent_main.py run

  Enroll device first:
    python agent_main.py enroll --server https://your-server --token YOUR_TOKEN
"""
import sys
import argparse
import asyncio
import platform


def cmd_enroll(args):
    """Enroll this device with the UEM server."""
    from src.config import AgentConfig
    from src.logger import setup_logging
    from src.enrollment import enroll

    setup_logging("INFO", log_to_file=False)
    config = AgentConfig()

    success = asyncio.run(enroll(config, args.server, args.token))
    if success:
        print(f"✅ Enrolled successfully. Device ID: {config.device_id}")
        print(f"   Server: {config.server_url}")
        print("   Start the agent service: python agent_main.py start")
    else:
        print("❌ Enrollment failed. Check the server URL and token.")
        sys.exit(1)


def cmd_run():
    """Run the agent in foreground (non-service mode, for testing)."""
    from src.config import AgentConfig
    from src.logger import setup_logging
    from src.service import run_agent

    config = AgentConfig()
    setup_logging("DEBUG", log_to_file=False)

    if not config.load():
        print("❌ Agent not enrolled. Run: python agent_main.py enroll")
        sys.exit(1)

    print(f"🚀 Starting UEM Agent (device: {config.device_id})")
    print(f"   Server: {config.server_url}")
    print("   Press Ctrl+C to stop")

    asyncio.run(run_agent(config))


def main():
    if len(sys.argv) < 2:
        sys.argv.append("--help")

    # Parse enroll command separately
    if sys.argv[1] == "enroll":
        parser = argparse.ArgumentParser(description="Enroll device with UEM server")
        parser.add_argument("enroll")
        parser.add_argument("--server", required=True, help="UEM server URL (e.g. https://uem.example.com)")
        parser.add_argument("--token", required=True, help="Enrollment token from UEM console")
        args = parser.parse_args()
        cmd_enroll(args)
        return

    if sys.argv[1] == "run":
        cmd_run()
        return

    # Windows service management
    if platform.system() == "Windows":
        from src.service import main as svc_main
        svc_main()
    else:
        if sys.argv[1] in ("install", "start", "stop", "remove"):
            print(f"❌ Service management only available on Windows. Use 'run' for foreground mode.")
            sys.exit(1)
        cmd_run()


if __name__ == "__main__":
    main()
