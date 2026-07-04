from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"
    PODCAST_FEED_URL: str = "https://feeds.captivate.fm/the-news-agents/"
    TRANSCRIPTION_MODEL: str = "whisper-1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    SEARCH_MIN_SCORE: float = 0.10
    DATABASE_URL: str = "postgresql://docker:docker@localhost:5432/postgres"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
