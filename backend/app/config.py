from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Cableguard API"
    DATABASE_URL: str = "sqlite:///./data/cableguard.db"
    CORS_ORIGINS: list[str] = []


settings = Settings()   # ← this line