import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    """Locate the repo root.

    podcast-core is installed as a wheel in consumer venvs, so __file__ may
    live inside .venv — walk up from both __file__ and the CWD looking for
    a repo marker (docker-compose.yml). Set PODCAST_DATA_ROOT to override.
    """
    here = Path(__file__).resolve()
    for base in (here, Path.cwd()):
        for parent in (base, *base.parents):
            if (parent / "docker-compose.yml").is_file():
                return parent
    return here.parents[2]  # fallback: source-checkout layout (<repo>/core/podcast_core)


REPO_ROOT = _find_repo_root()


def _find_env_file() -> Path | None:
    """Locate the .env file, normally at the repo root."""
    candidates = [
        REPO_ROOT / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    PODCAST_FEED_URL: str = "https://feeds.captivate.fm/the-news-agents/"
    # Transcription (faster-whisper, local)
    TRANSCRIPTION_MODEL: str = "large-v3"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    # Embeddings (Ollama, local — used by BOTH pipeline and API)
    OLLAMA_URL: str = "http://localhost:11434"
    # A/B (2026-08-27, eval/results/ab-*.json): 0.6b matched 8b at 11/11 hit@1
    # with the best gold/probe margin and 1024 dims fit the pgvector HNSW cap.
    EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    # Calibrated via the A/B on the 5-episode corpus with qwen3-embedding:0.6b:
    # gold top-1 min 0.4986 vs probe top-1 max 0.3464 (2026-08-27)
    SEARCH_MIN_SCORE: float = 0.42
    DATABASE_URL: str = "postgresql://docker:docker@localhost:5432/postgres"

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()

# Shared on-disk data locations (owned by the pipeline, read by eval/docs)
DATA_ROOT = Path(os.environ.get("PODCAST_DATA_ROOT", REPO_ROOT / "data"))
AUDIO_DIR = DATA_ROOT / "audio"
TRANSCRIPT_DIR = DATA_ROOT / "transcripts"
