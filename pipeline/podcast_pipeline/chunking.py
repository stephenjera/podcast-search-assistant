from typing import Any

from podcast_core.models import Chunk, Episode
from podcast_core.utils import stable_id


def build_chunks_from_transcript(
    episode: Episode,
    transcript: dict[str, Any],
    max_chars: int = 600,
) -> list[Chunk]:
    segments = transcript.get("segments", [])
    if not segments:
        full_text = (transcript.get("text") or "").strip()
        if not full_text:
            return []
        return [
            Chunk(
                chunk_id=stable_id(episode.episode_id, "0", full_text[:100]),
                episode_id=episode.episode_id,
                episode_title=episode.title,
                text=full_text,
                start_time=0.0,
                end_time=float(transcript.get("duration", 0.0)),
                published_at=episode.published_at,
                audio_url=episode.audio_url,
                page_url=episode.page_url,
            ),
        ]

    chunks: list[Chunk] = []
    current_text_parts: list[str] = []
    chunk_start: float | None = None
    chunk_end = 0.0
    chunk_idx = 0

    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        seg_start = float(segment.get("start", chunk_end))
        seg_end = float(segment.get("end", seg_start))

        if current_text_parts and len(" ".join([*current_text_parts, text])) > max_chars:
            chunk_text = " ".join(current_text_parts).strip()
            chunks.append(
                Chunk(
                    chunk_id=stable_id(episode.episode_id, str(chunk_idx), chunk_text[:100]),
                    episode_id=episode.episode_id,
                    episode_title=episode.title,
                    text=chunk_text,
                    start_time=chunk_start or 0.0,
                    end_time=chunk_end,
                    published_at=episode.published_at,
                    audio_url=episode.audio_url,
                    page_url=episode.page_url,
                ),
            )
            chunk_idx += 1
            current_text_parts = []
            chunk_start = None

        if chunk_start is None:
            chunk_start = seg_start
        chunk_end = seg_end
        current_text_parts.append(text)

    if current_text_parts:
        chunk_text = " ".join(current_text_parts).strip()
        chunks.append(
            Chunk(
                chunk_id=stable_id(episode.episode_id, str(chunk_idx), chunk_text[:100]),
                episode_id=episode.episode_id,
                episode_title=episode.title,
                text=chunk_text,
                start_time=chunk_start or 0.0,
                end_time=chunk_end,
                published_at=episode.published_at,
                audio_url=episode.audio_url,
                page_url=episode.page_url,
            ),
        )

    return chunks
