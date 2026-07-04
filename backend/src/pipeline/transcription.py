import io
import tempfile
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydub import AudioSegment

from config import settings
from logger import get_logger
from models import Episode
from utils import ensure_parent, read_json, write_json

logger = get_logger(__name__)


def transcript_cache_path(
    cache_dir: Path,
    episode: Episode,
    *,
    full_audio: bool = False,
    truncation_seconds: int = 120,
) -> Path:
    return _mode_specific_transcript_cache_path(
        cache_dir=cache_dir,
        episode=episode,
        full_audio=full_audio,
        truncation_seconds=truncation_seconds,
    )


def load_or_transcribe_episode(
    episode: Episode,
    audio_path: Path,
    cache_dir: Path,
    full_audio: bool = False,
    truncation_seconds: int = 120,
) -> dict[str, Any]:
    cache_path = _mode_specific_transcript_cache_path(
        cache_dir=cache_dir,
        episode=episode,
        full_audio=full_audio,
        truncation_seconds=truncation_seconds,
    )
    if cache_path.exists():
        logger.info("Loaded transcript from cache")
        return read_json(cache_path)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for transcription when cache is empty")

    ensure_parent(cache_path)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    if full_audio:
        logger.info("Transcribing full episode audio with OpenAI")
        transcript = _transcribe_with_auto_chunking(client=client, audio_path=audio_path)
    else:
        logger.info(f"Transcribing truncated audio (first {truncation_seconds}s)")
        transcript = _transcribe_truncated_audio(
            client=client,
            audio_path=audio_path,
            truncation_seconds=truncation_seconds,
        )
    write_json(cache_path, transcript)
    return transcript


def _mode_specific_transcript_cache_path(
    cache_dir: Path,
    episode: Episode,
    full_audio: bool,
    truncation_seconds: int,
) -> Path:
    if full_audio:
        return cache_dir / f"{episode.episode_id}.full.json"
    return cache_dir / f"{episode.episode_id}.{truncation_seconds}s.json"


def _transcribe_truncated_audio(
    client: OpenAI,
    audio_path: Path,
    truncation_seconds: int,
) -> dict[str, Any]:
    full_audio = AudioSegment.from_file(audio_path)
    truncated = full_audio[: truncation_seconds * 1000]
    audio_buffer = io.BytesIO()
    truncated.export(audio_buffer, format="mp3", bitrate="48k")
    audio_buffer.seek(0)
    audio_buffer.name = "truncated_clip.mp3"

    response = client.audio.transcriptions.create(
        model=settings.TRANSCRIPTION_MODEL,
        file=audio_buffer,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )
    return response.model_dump()


def _transcribe_with_auto_chunking(client: OpenAI, audio_path: Path) -> dict[str, Any]:
    max_upload_bytes = 24 * 1024 * 1024
    if audio_path.stat().st_size <= max_upload_bytes:
        with audio_path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=settings.TRANSCRIPTION_MODEL,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        return response.model_dump()

    logger.warning("Audio exceeds single-request limit; using segmented transcription")
    return _transcribe_segmented(client=client, audio_path=audio_path)


def _transcribe_segmented(client: OpenAI, audio_path: Path) -> dict[str, Any]:
    audio = AudioSegment.from_file(audio_path)
    chunk_ms = 10 * 60 * 1000
    total_ms = len(audio)

    merged_text_parts: list[str] = []
    merged_segments: list[dict[str, Any]] = []
    next_segment_id = 0
    language = "unknown"

    with tempfile.TemporaryDirectory(prefix="podcast_transcribe_") as tmp_dir:
        for start_ms in range(0, total_ms, chunk_ms):
            end_ms = min(start_ms + chunk_ms, total_ms)
            clip = audio[start_ms:end_ms]
            clip_path = Path(tmp_dir) / f"segment_{start_ms}_{end_ms}.mp3"
            clip.export(clip_path, format="mp3", bitrate="48k")

            logger.info(f"Transcribing segment {(start_ms / 1000):.1f}s -> {(end_ms / 1000):.1f}s")
            with clip_path.open("rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=settings.TRANSCRIPTION_MODEL,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            data = response.model_dump()

            if data.get("language"):
                language = str(data["language"])
            if data.get("text"):
                merged_text_parts.append(str(data["text"]).strip())

            offset_seconds = start_ms / 1000.0
            for segment in data.get("segments", []):
                mapped = dict(segment)
                mapped["id"] = next_segment_id
                mapped["start"] = float(segment.get("start", 0.0)) + offset_seconds
                mapped["end"] = float(segment.get("end", 0.0)) + offset_seconds
                merged_segments.append(mapped)
                next_segment_id += 1

    return {
        "task": "transcribe",
        "language": language,
        "duration": total_ms / 1000.0,
        "text": " ".join(part for part in merged_text_parts if part).strip(),
        "segments": merged_segments,
    }
