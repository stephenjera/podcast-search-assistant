"""Shared embedding client for the pipeline and the API.

Both the ingestion path and the query path MUST embed with the same model,
otherwise corpus and query vectors live in different spaces and search breaks.
This module is the single place that talks to the embedding provider.
"""

import httpx

from podcast_core.config import settings
from podcast_core.logger import get_logger

logger = get_logger(__name__)

# Ollama accepts lists of arbitrary length, but keep requests bounded so a
# full-episode chunk batch doesn't become one huge HTTP body.
_BATCH_SIZE = 64


class EmbeddingError(RuntimeError):
    """Raised when the embedding provider is unavailable or misconfigured."""


def embed_texts(
    texts: list[str], model: str | None = None
) -> list[list[float]]:
    """Embed a list of texts and return their vectors in the same order.

    `model` defaults to settings.EMBEDDING_MODEL. Callers comparing models
    (eval harness) must embed corpus AND queries with the same `model`.
    """
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + _BATCH_SIZE], model))
    logger.info(
        f"Embedded {len(texts)} texts ({len(vectors[0])} dims each, "
        f"model={model or settings.EMBEDDING_MODEL})"
    )
    return vectors


def _embed_batch(batch: list[str], model: str | None = None) -> list[list[float]]:
    model = model or settings.EMBEDDING_MODEL
    try:
        response = httpx.post(
            f"{settings.OLLAMA_URL.rstrip('/')}/api/embed",
            json={"model": model, "input": batch},
            timeout=httpx.Timeout(120.0),
        )
    except httpx.HTTPError as exc:
        raise EmbeddingError(
            f"Cannot reach Ollama at {settings.OLLAMA_URL}. "
            "Is `ollama serve` running?"
        ) from exc

    if response.status_code == 404:
        raise EmbeddingError(
            f"Embedding model '{model}' not found on Ollama. "
            f"Run: ollama pull {model}"
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
