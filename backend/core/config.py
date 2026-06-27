from functools import lru_cache
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SmartCheckout"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver,test"

    # Sécurité — Verrouillage de compte
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # PostgreSQL
    DATABASE_URL: str

    # Redis
    REDIS_URL: str
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP (clients)
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6

    # SMS
    SMS_PROVIDER: Literal["africas_talking", "twilio", "mock"] = "mock"
    AFRICAS_TALKING_API_KEY: str = ""
    AFRICAS_TALKING_USERNAME: str = "sandbox"
    SMS_SENDER_ID: str = "Fiissa"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Identity tokens
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    PASSWORD_RESET_TTL_MINUTES: int = 15

    # Stockage
    STORAGE_BACKEND: Literal["minio", "s3", "local"] = "local"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_RECEIPTS: str = "receipts"
    MINIO_BUCKET_PRODUCTS: str = "products"
    MINIO_USE_SSL: bool = False
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = "eu-west-1"

    # Paiement
    PAYMENT_MANUAL_TIMEOUT_MINUTES: int = 30
    PAYMENT_MANUAL_REMINDER_MINUTES: int = 15
    FEDAPAY_API_KEY: str = ""
    FEDAPAY_PUBLIC_KEY: str = ""
    FEDAPAY_WEBHOOK_SECRET: str = ""
    FEDAPAY_SANDBOX: bool = True
    PAYGATE_WEBHOOK_SECRET: str = ""

    # Email
    EMAIL_PROVIDER: Literal["smtp", "brevo_api", "mock"] = "smtp"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 20
    EMAIL_FROM: str = "noreply@smartcheckout.africa"
    EMAIL_FROM_NAME: str = "Fiissa"
    EMAIL_REPLY_TO: str = ""
    EMAIL_REPLY_TO_NAME: str = ""
    BREVO_API_KEY: str = ""

    # Super admin seed
    SUPERADMIN_EMAIL: str = "admin@smartcheckout.africa"
    SUPERADMIN_PASSWORD: str = ""
    SUPERADMIN_PHONE: str = "+221000000000"

    # Monitoring
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        # Render returns postgres:// or postgresql://, SQLAlchemy async needs postgresql+asyncpg://
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def normalize_redis_url(cls, v: str) -> str:
        # Render Redis URL may not include /0 database suffix — normalize it
        import re
        if v and not re.search(r"/\d+$", v):
            v = v.rstrip("/") + "/0"
        return v

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def set_celery_broker(cls, v: str, info) -> str:
        import re
        if v:
            return v
        redis_url = info.data.get("REDIS_URL", "")
        return re.sub(r"/\d+$", "/1", redis_url) if redis_url else ""

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def set_celery_result(cls, v: str, info) -> str:
        import re
        if v:
            return v
        redis_url = info.data.get("REDIS_URL", "")
        return re.sub(r"/\d+$", "/2", redis_url) if redis_url else ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @field_validator("DEBUG", mode="after")
    @classmethod
    def force_debug_off_in_prod(cls, v: bool, info) -> bool:
        if info.data.get("ENVIRONMENT") == "production" and v:
            return False
        return v

    @field_validator("MINIO_ACCESS_KEY", mode="after")
    @classmethod
    def validate_minio_credentials(cls, v: str, info) -> str:
        if info.data.get("STORAGE_BACKEND") == "minio" and info.data.get("ENVIRONMENT") == "production":
            if not v or v == "minioadmin":
                raise ValueError("MINIO_ACCESS_KEY must be set and not default in production")
        return v

    @field_validator("MINIO_SECRET_KEY", mode="after")
    @classmethod
    def validate_minio_secret(cls, v: str, info) -> str:
        if info.data.get("STORAGE_BACKEND") == "minio" and info.data.get("ENVIRONMENT") == "production":
            if not v or v == "minioadmin123":
                raise ValueError("MINIO_SECRET_KEY must be set and not default in production")
        return v

    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
