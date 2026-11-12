from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "DevHire"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://devhire_user:devhire_local_password@localhost:5432/devhire_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Authentication & Security
    SECRET_KEY: str = "insecure_dev_secret_key_change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "https://devhire.app"]
    ENVIRONMENT: str = "development"
    SENTRY_DSN: str | None = None

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "devhire-resumes"
    S3_ENDPOINT_URL: str | None = None
    RESUME_MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    RESUME_ALLOWED_CONTENT_TYPES: list[str] = ["application/pdf"]
    LOCAL_STORAGE_DIR: str = str(BASE_DIR / "uploads" / "resumes")

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in ["insecure_dev_secret_key_change_me", "devhire_docker_secret_key_change_in_prod", ""]:
                raise ValueError("In production, SECRET_KEY must be a secure randomly generated key and cannot use the development default.")
            if self.DEBUG is True:
                raise ValueError("DEBUG must be set to False in production.")
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"
    )


settings = Settings()
