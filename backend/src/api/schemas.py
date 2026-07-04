from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


class EpisodeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode_id: str
    title: str
    published_at: str | None = None
    audio_url: str | None = None
    page_url: str | None = None


class EpisodeDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode: EpisodeSummary


class EpisodeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episodes: list[EpisodeSummary]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=25)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    episode_id: str | None = Field(default=None, min_length=1, max_length=200)


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float
    chunk_id: str
    episode_id: str
    episode_title: str
    text: str
    start_time: float
    end_time: float
    timestamp_label: str
    snippet: str
    page_url: str | None = None
    published_at: str | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    search_mode: str
    min_score_applied: float
    no_match_reason: str | None = None
    hits: list[SearchHit]


class EpisodeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    timestamp_label: str


class EpisodeChunksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    episode_id: str
    episode_title: str
    published_at: str | None = None
    page_url: str | None = None
    chunks: list[EpisodeChunk]
