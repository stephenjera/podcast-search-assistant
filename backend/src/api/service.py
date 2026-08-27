from api.repository import vector_search
from api.schemas import SearchHit, SearchResponse
from config import settings
from db import get_db_connection
from embeddings import embed_texts
from logger import get_logger
from utils import format_timestamp

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
        hits = vector_search(
            conn=conn,
            query_vector=query_vector,
            top_k=top_k,
            episode_id=episode_id,
        )

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
