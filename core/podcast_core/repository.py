"""Shared read-path SQL, used by the API and the eval harness.

Returns plain dataclass rows (no service schemas) so that this module
stays free of any service-specific dependencies.
"""

from dataclasses import dataclass

from pgvector import Vector
from psycopg import Connection

from podcast_core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class EpisodeSummaryRow:
    episode_id: str
    title: str
    published_at: str | None
    audio_url: str | None
    page_url: str | None


@dataclass(frozen=True)
class SearchHitRow:
    chunk_id: str
    episode_id: str
    episode_title: str
    text: str
    start_time: float
    end_time: float
    page_url: str | None
    published_at: str | None
    score: float


@dataclass(frozen=True)
class ChunkRow:
    chunk_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float


def list_episodes(conn: Connection, limit: int = 100) -> list[EpisodeSummaryRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT external_episode_id, title, published_at::text, audio_url, page_url
            FROM episodes
            ORDER BY published_at DESC NULLS LAST, created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

    return [
        EpisodeSummaryRow(
            episode_id=row[0],
            title=row[1],
            published_at=row[2],
            audio_url=row[3],
            page_url=row[4],
        )
        for row in rows
    ]


def get_episode(conn: Connection, episode_id: str) -> EpisodeSummaryRow | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT external_episode_id, title, published_at::text, audio_url, page_url
            FROM episodes
            WHERE external_episode_id = %s
            LIMIT 1
            """,
            (episode_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return EpisodeSummaryRow(
        episode_id=row[0],
        title=row[1],
        published_at=row[2],
        audio_url=row[3],
        page_url=row[4],
    )


def vector_search(
    conn: Connection,
    query_vector: list[float],
    top_k: int,
    episode_id: str | None = None,
) -> list[SearchHitRow]:
    vector = Vector(query_vector)
    with conn.cursor() as cur:
        if episode_id:
            cur.execute(
                """
                SELECT
                    c.external_chunk_id,
                    e.external_episode_id,
                    e.title,
                    c.text_content,
                    c.start_time_seconds,
                    c.end_time_seconds,
                    e.page_url,
                    e.published_at::text,
                    1 - (c.embedding <=> %s) AS score
                FROM chunks c
                JOIN episodes e ON e.id = c.episode_id
                WHERE c.embedding IS NOT NULL
                  AND e.external_episode_id = %s
                ORDER BY c.embedding <=> %s
                LIMIT %s
                """,
                (vector, episode_id, vector, top_k),
            )
        else:
            cur.execute(
                """
                SELECT
                    c.external_chunk_id,
                    e.external_episode_id,
                    e.title,
                    c.text_content,
                    c.start_time_seconds,
                    c.end_time_seconds,
                    e.page_url,
                    e.published_at::text,
                    1 - (c.embedding <=> %s) AS score
                FROM chunks c
                JOIN episodes e ON e.id = c.episode_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s
                LIMIT %s
                """,
                (vector, vector, top_k),
            )
        rows = cur.fetchall()

    hits = [
        SearchHitRow(
            score=float(row[8]),
            chunk_id=row[0],
            episode_id=row[1],
            episode_title=row[2],
            text=row[3],
            start_time=float(row[4]),
            end_time=float(row[5]),
            page_url=row[6],
            published_at=row[7],
        )
        for row in rows
    ]
    logger.info(f"Vector search returned {len(hits)} hits")
    return hits


def list_episode_chunks(
    conn: Connection, episode_id: str, limit: int = 500
) -> list[ChunkRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.external_chunk_id, c.chunk_index, c.text_content, c.start_time_seconds, c.end_time_seconds
            FROM chunks c
            JOIN episodes e ON e.id = c.episode_id
            WHERE e.external_episode_id = %s
            ORDER BY c.chunk_index ASC
            LIMIT %s
            """,
            (episode_id, limit),
        )
        rows = cur.fetchall()

    return [
        ChunkRow(
            chunk_id=row[0],
            chunk_index=int(row[1]),
            text=row[2],
            start_time=float(row[3]),
            end_time=float(row[4]),
        )
        for row in rows
    ]
