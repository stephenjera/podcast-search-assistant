from pydantic import BaseModel, ConfigDict, Field


class Episode(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    episode_id: str
    title: str
    published_at: str | None = None
    audio_url: str | None = None
    page_url: str | None = None


class Chunk(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    chunk_id: str
    episode_id: str
    episode_title: str
    text: str = Field(min_length=1)
    start_time: float
    end_time: float
    published_at: str | None = None
    audio_url: str | None = None
    page_url: str | None = None
