from pgvector import Vector
from psycopg import Connection

from api.schemas import EpisodeChunk, EpisodeSummary, SearchHit
from logger import get_logger
from utils import format_timestamp

logger = get_logger(__name__)


def list_episodes(conn: Connection, limit: int = 100) -> list[EpisodeSummary]:
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
        EpisodeSummary(
            episode_id=row[0],
            title=row[1],
            published_at=row[2],
            audio_url=row[3],
            page_url=row[4],
        )
        for row in rows
    ]


def get_episode(conn: Connection, episode_id: str) -> EpisodeSummary | None:
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
    return EpisodeSummary(
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
) -> list[SearchHit]:
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
        SearchHit(
            score=float(row[8]),
            chunk_id=row[0],
            episode_id=row[1],
            episode_title=row[2],
            text=row[3],
            start_time=float(row[4]),
            end_time=float(row[5]),
            timestamp_label="",
            snippet="",
            page_url=row[6],
            published_at=row[7],
        )
        for row in rows
    ]
    logger.info(f"Vector search returned {len(hits)} hits")
    return hits


def list_episode_chunks(
    conn: Connection, episode_id: str, limit: int = 500
) -> list[EpisodeChunk]:
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
        EpisodeChunk(
            chunk_id=row[0],
            chunk_index=int(row[1]),
            text=row[2],
            start_time=float(row[3]),
            end_time=float(row[4]),
            timestamp_label=format_timestamp(float(row[3])),
        )
        for row in rows
    ]
