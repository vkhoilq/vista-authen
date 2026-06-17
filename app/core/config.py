from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Project
    PROJECT_NAME: str = "Vista Authen"
    VERSION: str = "0.1.0"

    # Domain configs
    DOMAIN_NAME: str = "example.com"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vista:vista@localhost:5432/vista_authen"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Activation token
    ACTIVATION_TOKEN_TTL_HOURS: int = 24

    # QR verification
    QR_TIMESTAMP_TOLERANCE_SEC: int = 60

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    # Maintenance / Security
    AUDIT_LOG_RETENTION_DAYS: int = 90
    CLEANUP_INTERVAL_SECONDS: int = 3600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()