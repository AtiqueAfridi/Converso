"""Application configuration settings module."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_chroma_path() -> Path:
    """Compute the default on-disk location for the Chroma vector store."""

    return (Path(__file__).resolve().parents[1] / "storage" / "chroma").resolve()


def _find_env_file() -> Path:
    """Locate .env file starting from project root."""
    # Start from backend/app/core/config.py
    # Go up to project root (3 levels: core -> app -> backend -> project root)
    project_root = Path(__file__).resolve().parents[3]
    env_file = project_root / ".env"
    if env_file.exists():
        return env_file
    # Fallback to current directory
    return Path(".env").resolve()


class Settings(BaseSettings):
    """Strongly typed application settings loaded from the environment."""

    app_name: str = "LangChain GPT-5 Chatbot"
    debug: bool = False
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_directory: Path = Field(default_factory=_default_chroma_path)
    max_context_messages: int = 6

    model_config = SettingsConfigDict(
        env_file=str(_find_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    settings = Settings()
    # Ensure persist directory exists even if it is overridden.
    settings.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
    return settings
