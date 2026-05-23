from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "bagtag.aero"
    ENVIRONMENT: str = "local"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/bagtag.db"
    UPLOAD_DIR: Path = BASE_DIR / "static" / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    FLIGHTRADAR24_API_KEY: str | None = None


settings = Settings()
