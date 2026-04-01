"""
PKI module for issuing and managing device client certificates.
The UEM server acts as its own CA.
"""
import datetime
import hashlib
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import settings


def _load_ca() -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    ca_cert_path = settings.ca_cert_path
    ca_key_path = settings.ca_key_path

    if not ca_cert_path.exists() or not ca_key_path.exists():
        raise RuntimeError(
            f"CA certificate not found at {ca_cert_path}. "
            "Run 'make pki' to generate the CA."
        )

    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())

    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None)

    return ca_cert, ca_key  # type: ignore[return-value]


def issue_device_certificate(
    device_uuid: str,
    hostname: str,
) -> tuple[str, str, str, str]:
    """
    Issue a client certificate for the device.

    Returns:
        (cert_pem, private_key_pem, serial_number_hex, thumbprint)
    """
    ca_cert, ca_key = _load_ca()

    # Generate device key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    validity_days = settings.CERT_VALIDITY_DAYS

    cert = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, f"uem-device-{device_uuid}"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "UEM Platform"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Managed Device"),
            ])
        )
        .issuer_name(ca_cert.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=validity_days))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(hostname),
                x509.OtherName(
                    x509.oid.ObjectIdentifier("1.3.6.1.4.1.99999.1"),
                    device_uuid.encode(),
                ),
            ]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    serial_hex = f"{cert.serial_number:x}"
    thumbprint = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()

    return cert_pem, key_pem, serial_hex, thumbprint


def verify_client_certificate(cert_pem: str) -> dict:
    """Verify a client certificate against the CA and return device info."""
    ca_cert, _ = _load_ca()

    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
    except Exception as exc:
        raise ValueError(f"Invalid certificate PEM: {exc}") from exc

    # Verify signature against CA
    try:
        ca_cert.public_key().verify(  # type: ignore[attr-defined]
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_hash_algorithm,  # type: ignore[arg-type]
        )
    except Exception:
        raise ValueError("Certificate signature verification failed")

    now = datetime.datetime.now(datetime.timezone.utc)
    if cert.not_valid_after_utc < now:
        raise ValueError("Certificate has expired")
    if cert.not_valid_before_utc > now:
        raise ValueError("Certificate is not yet valid")

    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    device_uuid = cn.replace("uem-device-", "")

    return {
        "device_uuid": device_uuid,
        "serial_number": f"{cert.serial_number:x}",
        "thumbprint": hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest(),
        "not_after": cert.not_valid_after_utc.isoformat(),
    }


def get_ca_cert_pem() -> str:
    ca_cert, _ = _load_ca()
    return ca_cert.public_bytes(serialization.Encoding.PEM).decode()
