from dataclasses import asdict

from podcast_core.repository import (
    get_episode,
    list_episode_chunks,
    list_episodes,
    vector_search,
)

from .schemas import (
    EpisodeChunk,
    EpisodeDetailResponse,
    EpisodeListResponse,
    EpisodeSummary,
    SearchHit,
    SearchResponse,
)
from podcast_core.config import settings
from podcast_core.db import get_db_connection
from podcast_core.embeddings import embed_texts
from podcast_core.logger import get_logger
from podcast_core.utils import format_timestamp

logger = get_logger(__name__)


def run_search(
    query: str,
    top_k: int,
    min_score_override: float | None = None,
    episode_id: str | None = None,
) -> SearchResponse:
    logger.info(
        f"Search requested: query='{query[:120]}' top_k={top_k} episode_id={episode_id}"
    )

    query_vector = embed_texts([query])[0]
    logger.info(f"Query embedding generated (dimensions={len(query_vector)})")

    with get_db_connection() as conn:
        rows = vector_search(
            conn=conn,
            query_vector=query_vector,
            top_k=top_k,
            episode_id=episode_id,
        )

    hits = [
        SearchHit(
            score=row.score,
            chunk_id=row.chunk_id,
            episode_id=row.episode_id,
            episode_title=row.episode_title,
            text=row.text,
            start_time=row.start_time,
            end_time=row.end_time,
            timestamp_label="",
            snippet=row.text[:260],
            page_url=row.page_url,
            published_at=row.published_at,
        )
        for row in rows
    ]

    min_score = (
        settings.SEARCH_MIN_SCORE if min_score_override is None else min_score_override
    )
    filtered_hits = _apply_score_threshold(hits=hits, min_score=min_score)
    no_match_reason = None
    if not filtered_hits:
        no_match_reason = (
            f"No confident matches found (score threshold={min_score:.2f})"
        )

    enhanced_hits = [_enhance_hit(hit) for hit in filtered_hits]
    logger.info(
        f"Search response hits={len(enhanced_hits)} mode=vector min_score={min_score}",
    )
    return SearchResponse(
        query=query,
        search_mode="vector",
        min_score_applied=min_score,
        no_match_reason=no_match_reason,
        hits=enhanced_hits,
    )


def _apply_score_threshold(hits: list[SearchHit], min_score: float) -> list[SearchHit]:
    return [hit for hit in hits if hit.score >= min_score]


def _enhance_hit(hit: SearchHit) -> SearchHit:
    snippet = hit.text if len(hit.text) <= 260 else f"{hit.text[:257]}..."
    return hit.model_copy(
        update={
            "timestamp_label": format_timestamp(hit.start_time),
            "snippet": snippet,
        },
    )


def list_episode_summaries(limit: int = 100) -> EpisodeListResponse:
    """Map core's plain EpisodeSummaryRow dataclasses onto the API schema."""
    with get_db_connection() as conn:
        rows = list_episodes(conn=conn, limit=limit)
    return EpisodeListResponse(
        episodes=[EpisodeSummary(**asdict(row)) for row in rows]
    )


def get_episode_summary(episode_id: str) -> EpisodeDetailResponse | None:
    with get_db_connection() as conn:
        row = get_episode(conn=conn, episode_id=episode_id)
    if row is None:
        return None
    return EpisodeDetailResponse(episode=EpisodeSummary(**asdict(row)))


def list_episode_chunk_summaries(
    episode_id: str, limit: int = 500
) -> list[EpisodeChunk]:
    with get_db_connection() as conn:
        rows = list_episode_chunks(conn=conn, episode_id=episode_id, limit=limit)
    return [
        EpisodeChunk(
            chunk_id=row.chunk_id,
            chunk_index=row.chunk_index,
            text=row.text,
            start_time=row.start_time,
            end_time=row.end_time,
            timestamp_label=format_timestamp(row.start_time),
        )
        for row in rows
    ]
