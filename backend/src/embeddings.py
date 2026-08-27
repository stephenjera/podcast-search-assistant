"""Shared embedding client for the pipeline and the API.

Both the ingestion path and the query path MUST embed with the same model,
otherwise corpus and query vectors live in different spaces and search breaks.
This module is the single place that talks to the embedding provider.
"""

import httpx

from config import settings
from logger import get_logger

logger = get_logger(__name__)

# qwen3-embedding:8b output dimension. Keep in sync with EMBEDDING_MODEL.
EMBEDDING_DIMENSIONS = 4096

# Ollama accepts lists of arbitrary length, but keep requests bounded so a
# full-episode chunk batch doesn't become one huge HTTP body.
_BATCH_SIZE = 64


class EmbeddingError(RuntimeError):
    """Raised when the embedding provider is unavailable or misconfigured."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts and return their vectors in the same order."""
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + _BATCH_SIZE]))
    logger.info(f"Embedded {len(texts)} texts ({EMBEDDING_DIMENSIONS} dims each)")
    return vectors


def _embed_batch(batch: list[str]) -> list[list[float]]:
    try:
        response = httpx.post(
            f"{settings.OLLAMA_URL.rstrip('/')}/api/embed",
            json={"model": settings.EMBEDDING_MODEL, "input": batch},
            timeout=httpx.Timeout(120.0),
        )
    except httpx.HTTPError as exc:
        raise EmbeddingError(
            f"Cannot reach Ollama at {settings.OLLAMA_URL}. "
            "Is `ollama serve` running?"
        ) from exc

    if response.status_code == 404:
        raise EmbeddingError(
            f"Embedding model '{settings.EMBEDDING_MODEL}' not found on Ollama. "
            f"Run: ollama pull {settings.EMBEDDING_MODEL}"
        )
    if response.status_code >= 400:
        raise EmbeddingError(
            f"Ollama embed failed ({response.status_code}): {response.text[:300]}"
        )

    embeddings = response.json().get("embeddings", [])
    if len(embeddings) != len(batch):
        raise EmbeddingError(
            f"Expected {len(batch)} embeddings, got {len(embeddings)}"
        )
    return embeddings
