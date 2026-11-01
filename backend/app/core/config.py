from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "DevHire"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://devhire_user:devhire_local_password@localhost:5432/devhire_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication & Security
    SECRET_KEY: str = "insecure_dev_secret_key_change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "devhire-resumes"
    S3_ENDPOINT_URL: str | None = None
    RESUME_MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    RESUME_ALLOWED_CONTENT_TYPES: list[str] = ["application/pdf"]
    LOCAL_STORAGE_DIR: str = str(BASE_DIR / "uploads" / "resumes")

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"
    )


settings = Settings()
