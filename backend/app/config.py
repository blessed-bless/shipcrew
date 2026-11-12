from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHIPCREW_", env_file=".env", extra="ignore")

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    demo_mode: bool = True
    data_dir: Path = Path("./data")
    host: str = "127.0.0.1"
    port: int = 8787
    max_review_rounds: int = 2
    request_timeout_s: float = 120.0
    # Куда вернуть пользователя после OAuth (Vite dev или собранный UI).
    frontend_url: str = "http://127.0.0.1:5173"
    # Публичный origin бэкенда для callback_url OpenRouter.
    public_base_url: str = "http://127.0.0.1:8787"
    runner_timeout_s: float = 600.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
