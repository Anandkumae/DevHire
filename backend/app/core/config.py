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

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"
    )


settings = Settings()
