"""Store-is-source-of-truth helpers.

The corpus stamps which models produced it (embedding model, dimensions,
transcription model). The API validates the stamp at startup and fails
loudly if its configured embedding model doesn't match the corpus, so a
model change can never silently mix incompatible vectors.
"""

from datetime import datetime, timezone

from psycopg import Connection

from podcast_core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingModelMismatchError(RuntimeError):
    """Corpus embeddings were produced by a different model than configured."""


def stamp_schema_meta(
    conn: Connection,
    *,
    embedding_model: str,
    transcription_model: str,
) -> None:
    rows = {
        "embedding_model": embedding_model,
        "embedding_dimensions": str(vector_width(conn)),
        "transcription_model": transcription_model,
        "stamped_at": datetime.now(timezone.utc).isoformat(),
    }
    with conn.cursor() as cur:
        for key, value in rows.items():
            cur.execute(
                """
                INSERT INTO schema_meta (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                """,
                (key, value),
            )
    conn.commit()
    logger.info(f"Stamped schema_meta: {rows}")


def vector_width(conn: Connection) -> int | None:
    """Width of chunks.embedding, from a stored vector (fallback: column attr)."""
    with conn.cursor() as cur:
        cur.execute("SELECT vector_dims(embedding) FROM chunks LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        cur.execute(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
        )
        row = cur.fetchone()
    # pgvector stores the dimension in atttypmod directly (no varlena offset)
    return int(row[0]) if row and row[0] > 0 else None


def get_schema_meta(conn: Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT key, value FROM schema_meta")
        return {key: value for key, value in cur.fetchall()}


def corpus_size(conn: Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks")
        return int(cur.fetchone()[0])


def warn_if_corpus_mismatch(conn: Connection, configured_model: str) -> None:
    """Pipeline-side soft check: warn (don't block) when ingesting with a
    different embedding model than the existing corpus."""
    if corpus_size(conn) == 0:
        return
    stored = get_schema_meta(conn).get("embedding_model")
    if stored and stored != configured_model:
        logger.warning(
            f"Corpus embedded with {stored!r} but ingesting with {configured_model!r}. "
            "This will create a mixed-vector corpus — search quality will degrade."
        )


def validate_embedding_model(conn: Connection, configured_model: str) -> None:
    """API-side hard check: fail loudly on model mismatch with a non-empty corpus."""
    if corpus_size(conn) == 0:
        logger.info("Corpus empty — skipping embedding model validation")
        return
    stored = get_schema_meta(conn).get("embedding_model")
    if stored is None:
        logger.warning(
            "Corpus present but schema_meta has no embedding_model stamp — "
            "cannot validate; stamp the corpus after next ingest."
        )
        return
    if stored != configured_model:
        raise EmbeddingModelMismatchError(
            f"Corpus was embedded with {stored!r} but the API is configured for "
            f"{configured_model!r}. Re-ingest the corpus with the new model, or "
            "set EMBEDDING_MODEL back to the stored model."
        )
    logger.info(f"Embedding model validated: {stored!r}")
