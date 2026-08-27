from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    PODCAST_FEED_URL: str = "https://feeds.captivate.fm/the-news-agents/"
    # Transcription (faster-whisper, local)
    TRANSCRIPTION_MODEL: str = "large-v3"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    # Embeddings (Ollama, local — used by BOTH pipeline and API)
    OLLAMA_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "qwen3-embedding:8b"
    # Calibrated via `pipeline.benchmark` on the 5-episode corpus:
    # gold top-1 min 0.493 vs probe top-1 max 0.379 (2026-08-27)
    SEARCH_MIN_SCORE: float = 0.44
    DATABASE_URL: str = "postgresql://docker:docker@localhost:5432/postgres"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
