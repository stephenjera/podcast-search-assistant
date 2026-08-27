from contextlib import asynccontextmanager
from typing import NoReturn

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from podcast_core.config import settings
from podcast_core.db import get_db_connection
from podcast_core.logger import get_logger
from podcast_core.meta import validate_embedding_model
from podcast_core.repository import get_episode, list_episode_chunks, list_episodes
from podcast_backend.schemas import (
    EpisodeChunksResponse,
    EpisodeDetailResponse,
    EpisodeListResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
)
from podcast_backend.service import run_search

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail loudly if the corpus was embedded by a different model than this API's.
    with get_db_connection() as conn:
        validate_embedding_model(conn, settings.EMBEDDING_MODEL)
    yield


app = FastAPI(title="Podcast Search Assistant API", version="0.1.0", lifespan=lifespan)


def _raise_internal_error(route_label: str, exc: Exception) -> NoReturn:
    logger.exception(f"Unhandled error in {route_label}: {exc}")
    raise HTTPException(status_code=500, detail="internal error") from exc

app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> HealthResponse:
    try:
        return HealthResponse(status="ok")
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error("GET /health", exc)


@app.get("/episodes", response_model=EpisodeListResponse)
def get_episodes() -> EpisodeListResponse:
    try:
        logger.info("GET /episodes called")
        with get_db_connection() as conn:
            episodes = list_episodes(conn=conn)
        logger.info(f"GET /episodes returning {len(episodes)} episodes")
        return EpisodeListResponse(episodes=episodes)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error("GET /episodes", exc)


@app.get("/episodes/{episode_id}", response_model=EpisodeDetailResponse)
def get_episode_detail(episode_id: str) -> EpisodeDetailResponse:
    try:
        logger.info(f"GET /episodes/{episode_id} called")
        with get_db_connection() as conn:
            episode = get_episode(conn=conn, episode_id=episode_id)
        if episode is None:
            raise HTTPException(status_code=404, detail="Episode not found")
        return EpisodeDetailResponse(episode=episode)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(f"GET /episodes/{episode_id}", exc)


@app.get("/episodes/{episode_id}/chunks", response_model=EpisodeChunksResponse)
def get_episode_chunks(
    episode_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
) -> EpisodeChunksResponse:
    try:
        logger.info(f"GET /episodes/{episode_id}/chunks called limit={limit}")
        with get_db_connection() as conn:
            episode = get_episode(conn=conn, episode_id=episode_id)
            if episode is None:
                raise HTTPException(status_code=404, detail="Episode not found")
            chunks = list_episode_chunks(conn=conn, episode_id=episode_id, limit=limit)
        return EpisodeChunksResponse(
            episode_id=episode.episode_id,
            episode_title=episode.title,
            published_at=episode.published_at,
            page_url=episode.page_url,
            chunks=chunks,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error(f"GET /episodes/{episode_id}/chunks", exc)


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    try:
        logger.info(
            f"POST /search called query='{request.query[:120]}' top_k={request.top_k} episode_id={request.episode_id}"
        )
        response = run_search(
            query=request.query,
            top_k=request.top_k,
            min_score_override=request.min_score,
            episode_id=request.episode_id,
        )
        logger.info(f"POST /search returning {len(response.hits)} hits")
        return response
    except HTTPException:
        raise
    except Exception as exc:
        _raise_internal_error("POST /search", exc)
