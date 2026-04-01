"""
First-run enrollment: generates a key/CSR, sends it to the server,
receives a signed certificate, and saves all config.
"""
import platform
import socket
import subprocess
import uuid
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.config import AgentConfig, CERT_DIR, AGENT_VERSION
from src.logger import get_logger

logger = get_logger(__name__)


def get_machine_uuid() -> str:
    """Get a stable hardware UUID for this machine."""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "csproduct", "get", "UUID"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and l.strip() != "UUID"]
            if lines:
                return lines[0]
        except Exception:
            pass
    # Fallback: use MAC address + hostname as stable UUID
    mac = hex(uuid.getnode())[2:].upper()
    hostname = socket.gethostname()
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{hostname}-{mac}"))


def get_serial_number() -> str | None:
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "bios", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().splitlines()
                     if l.strip() and l.strip() != "SerialNumber"]
            if lines and lines[0] != "To Be Filled By O.E.M.":
                return lines[0]
        except Exception:
            pass
    return None


def generate_csr(device_uuid: str, hostname: str) -> tuple[str, str]:
    """Generate RSA key pair and CSR. Returns (csr_pem, key_pem)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"uem-device-{device_uuid}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "UEM Platform"),
        ]))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    return csr_pem, key_pem


async def enroll(config: AgentConfig, server_url: str, enrollment_token: str) -> bool:
    """
    Perform first-run enrollment against the UEM server.
    Returns True on success.
    """
    logger.info("Starting device enrollment", server_url=server_url)

    device_uuid = get_machine_uuid()
    hostname = socket.gethostname()
    try:
        fqdn = socket.getfqdn()
    except Exception:
        fqdn = hostname

    # Get OS info
    os_version = platform.version()
    os_build = None
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                os_version = winreg.QueryValueEx(k, "ProductName")[0]
                os_build = winreg.QueryValueEx(k, "CurrentBuildNumber")[0]
        except Exception:
            pass

    csr_pem, key_pem = generate_csr(device_uuid, hostname)

    payload = {
        "enrollment_token": enrollment_token,
        "device_uuid": device_uuid,
        "hostname": hostname,
        "fqdn": fqdn,
        "serial_number": get_serial_number(),
        "os_version": os_version,
        "os_build": os_build,
        "os_architecture": platform.machine(),
        "agent_version": AGENT_VERSION,
        "csr_pem": csr_pem,
    }

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            resp = await client.post(
                f"{server_url}/api/v1/devices/enroll",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("Enrollment HTTP error", status=e.response.status_code, body=e.response.text)
        return False
    except Exception as e:
        logger.error("Enrollment failed", error=str(e))
        return False

    data = resp.json()
    device_id = data["device_id"]
    cert_pem = data["cert_pem"]
    ca_cert_pem = data["ca_cert_pem"]
    agent_config = data.get("config", {})

    # Save certificates
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    (CERT_DIR / "device.crt").write_text(cert_pem)
    (CERT_DIR / "device.key").write_text(key_pem)
    (CERT_DIR / "ca.crt").write_text(ca_cert_pem)

    # Save config
    config.save({
        "device_id": device_id,
        "server_url": server_url,
        "ws_url": agent_config.get("ws_url", f"{server_url.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/agent/{device_id}"),
        "heartbeat_interval": agent_config.get("heartbeat_interval", 30),
        "inventory_interval": agent_config.get("inventory_interval", 3600),
        "patch_check_interval": agent_config.get("patch_check_interval", 86400),
    })

    logger.info("Enrollment successful", device_id=device_id)
    return True
