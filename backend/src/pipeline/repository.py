from pathlib import Path
from typing import Any

from psycopg import Connection
from psycopg.types.json import Json

from models import Chunk, Episode


def upsert_episode(conn: Connection, episode: Episode) -> str:
    with conn.cursor() as cur:
        cur.execute(
            query="""
            INSERT INTO episodes (external_episode_id, title, published_at, audio_url, page_url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (external_episode_id) DO UPDATE
            SET title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                audio_url = EXCLUDED.audio_url,
                page_url = EXCLUDED.page_url,
                updated_at = NOW()
            RETURNING id
            """,
            params=(
                episode.episode_id,
                episode.title,
                episode.published_at,
                episode.audio_url,
                episode.page_url,
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Failed to upsert episode")
        return str(row[0])


def upsert_audio_asset(conn: Connection, episode_db_id: str, file_path: Path) -> None:
    with conn.cursor() as cur:
        cur.execute(
            query="""
            INSERT INTO audio_assets (episode_id, file_path, file_size_bytes)
            VALUES (%s, %s, %s)
            ON CONFLICT (episode_id) DO UPDATE
            SET file_path = EXCLUDED.file_path,
                file_size_bytes = EXCLUDED.file_size_bytes
            """,
            params=(episode_db_id, str(file_path), file_path.stat().st_size),
        )


def upsert_transcript(
    conn: Connection,
    episode_db_id: str,
    transcript_path: Path,
    transcript: dict[str, Any],
    model_name: str,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            query="""
            INSERT INTO transcripts (
                episode_id, transcript_path, transcript_json, transcription_model, language, duration_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (episode_id) DO UPDATE
            SET transcript_path = EXCLUDED.transcript_path,
                transcript_json = EXCLUDED.transcript_json,
                transcription_model = EXCLUDED.transcription_model,
                language = EXCLUDED.language,
                duration_seconds = EXCLUDED.duration_seconds
            RETURNING id
            """,
            params=(
                episode_db_id,
                str(transcript_path),
                Json(transcript),
                model_name,
                transcript.get("language"),
                transcript.get("duration"),
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Failed to upsert transcript")
        return str(row[0])


def replace_chunks(
    conn: Connection,
    episode_db_id: str,
    transcript_db_id: str,
    chunks: list[Chunk],
    vectors: list[list[float]] | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE episode_id = %s", (episode_db_id,))

        for idx, chunk in enumerate(chunks):
            embedding = vectors[idx] if vectors is not None else None
            cur.execute(
                query="""
                INSERT INTO chunks (
                    external_chunk_id, episode_id, transcript_id, chunk_index, text_content,
                    start_time_seconds, end_time_seconds, metadata_json, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params=(
                    chunk.chunk_id,
                    episode_db_id,
                    transcript_db_id,
                    idx,
                    chunk.text,
                    chunk.start_time,
                    chunk.end_time,
                    Json(chunk.model_dump()),
                    embedding,
                ),
            )


def start_ingest_run(conn: Connection) -> str:
    with conn.cursor() as cur:
        cur.execute(
            query="INSERT INTO ingest_runs (status) VALUES ('running') RETURNING id",
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Failed to start ingest run")
        return str(row[0])


def finish_ingest_run(
    conn: Connection,
    run_id: str,
    *,
    status: str,
    episodes_processed: int,
    error: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            query="""
            UPDATE ingest_runs
            SET status = %s,
                episodes_processed = %s,
                error = %s,
                finished_at = NOW()
            WHERE id = %s
            """,
            params=(status, episodes_processed, error, run_id),
        )
