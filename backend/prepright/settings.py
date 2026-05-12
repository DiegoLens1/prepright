from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./prepright.db"
    cors_origins: str = "*"

    class Config:
        env_prefix = ""
        env_file = ".env"


def get_cors_origins() -> list:
    if settings.cors_origins == "*":
        return ["*"]
    return [origin.strip() for origin in settings.cors_origins.split(",")]


settings = Settings()
