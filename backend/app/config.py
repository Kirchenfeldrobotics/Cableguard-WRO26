import json
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Cableguard API"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'cableguard.db'}"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # Signing key for the webapp access tokens. Leave empty only in development:
    # app.auth then falls back to a random per-process secret, so every restart
    # logs the operator out.
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 12 * 60

    # The single operator account, created on first start if it does not exist.
    DEFAULT_USERNAME: str = ""
    DEFAULT_PASSWORD: str = ""

    # Secret stored on the NFC tag on the robot. Tapping the tag opens
    # /login#nfc=<key> and signs in as the operator above. Empty disables it.
    NFC_LOGIN_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        """Accept either a JSON array or a comma-separated list from the environment."""
        if not isinstance(v, str):
            return v
        v = v.strip()
        if not v:
            return []
        if v.startswith("["):
            return json.loads(v)
        return [origin.strip() for origin in v.split(",") if origin.strip()]


settings = Settings()
