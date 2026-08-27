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
    SEARCH_MIN_SCORE: float = 0.10
    DATABASE_URL: str = "postgresql://docker:docker@localhost:5432/postgres"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
