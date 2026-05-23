from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        extra="ignore",
    )

    JWT_SECRET: str = Field(default="change-me-in-production-please-set-me", min_length=32)
    JWT_ALG: str = "HS256"
    JWT_EXP_MINUTES: int = 1440  # 24 hours


auth_settings = AuthConfig()
