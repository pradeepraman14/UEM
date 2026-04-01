from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "UEM Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SERVER_BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://uem:uem_secret@localhost:5432/uem"

    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change_me_very_long_random_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Admin
    INITIAL_ADMIN_EMAIL: str = "admin@uem.local"
    INITIAL_ADMIN_PASSWORD: str = "Admin@123456"

    # PKI
    CA_CERT_PATH: str = "/app/pki/ca/ca.crt"
    CA_KEY_PATH: str = "/app/pki/ca/ca.key"
    CERT_VALIDITY_DAYS: int = 365

    # Agent behavior
    AGENT_HEARTBEAT_INTERVAL: int = 30
    AGENT_INVENTORY_INTERVAL: int = 3600
    AGENT_PATCH_CHECK_INTERVAL: int = 86400

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@uem.local"
    SMTP_TLS: bool = True

    # Paths
    PACKAGES_DIR: str = "/app/packages"
    LOGS_DIR: str = "/app/logs"

    # Celery
    CELERY_RESULT_BACKEND: str = "redis://:redis_secret@localhost:6379/1"

    @property
    def celery_broker_url(self) -> str:
        return self.REDIS_URL

    @property
    def ca_cert_path(self) -> Path:
        return Path(self.CA_CERT_PATH)

    @property
    def ca_key_path(self) -> Path:
        return Path(self.CA_KEY_PATH)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
