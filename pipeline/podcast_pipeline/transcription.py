import tempfile
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from pydub import AudioSegment

from podcast_core.config import settings
from podcast_core.logger import get_logger
from podcast_core.models import Episode
from podcast_core.utils import ensure_parent, read_json, write_json

logger = get_logger(__name__)

_model_cache: dict[tuple[str, str, str], WhisperModel] = {}


def get_whisper_model(
    model_size: str,
    device: str,
    compute_type: str,
) -> WhisperModel:
    cache_key = (model_size, device, compute_type)
    if cache_key not in _model_cache:
        logger.info(f"Loading faster-whisper {model_size} on {device} with {compute_type}")
        _model_cache[cache_key] = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
    return _model_cache[cache_key]


def transcript_cache_path(
    cache_dir: Path,
    episode: Episode,
    *,
    model_name: str,
    full_audio: bool = False,
    truncation_seconds: int = 120,
) -> Path:
    return _mode_specific_transcript_cache_path(
        cache_dir=cache_dir,
        episode=episode,
        model_name=model_name,
        full_audio=full_audio,
        truncation_seconds=truncation_seconds,
    )


def load_or_transcribe_episode(
    episode: Episode,
    audio_path: Path,
    cache_dir: Path,
    *,
    model_name: str,
    full_audio: bool = False,
    truncation_seconds: int = 120,
) -> dict[str, Any]:
    cache_path = _mode_specific_transcript_cache_path(
        cache_dir=cache_dir,
        episode=episode,
        model_name=model_name,
        full_audio=full_audio,
        truncation_seconds=truncation_seconds,
    )
    if cache_path.exists():
        logger.info("Loaded transcript from cache")
        return read_json(cache_path)

    ensure_parent(cache_path)
    whisper_model = get_whisper_model(
        model_size=settings.TRANSCRIPTION_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )
    if full_audio:
        logger.info("Transcribing full episode audio with local Whisper")
        transcript = _transcribe_with_whisper(whisper_model, audio_path)
    else:
        logger.info(f"Transcribing truncated audio (first {truncation_seconds}s)")
        transcript = _transcribe_truncated_audio(
            whisper_model=whisper_model,
            audio_path=audio_path,
            truncation_seconds=truncation_seconds,
        )
    write_json(cache_path, transcript)
    return transcript


def _mode_specific_transcript_cache_path(
    cache_dir: Path,
    episode: Episode,
    *,
    model_name: str,
    full_audio: bool,
    truncation_seconds: int,
) -> Path:
    # Model name is part of the key: changing TRANSCRIPTION_MODEL must not
    # silently serve transcripts produced by a different model.
    if full_audio:
        return cache_dir / f"{episode.episode_id}.{model_name}.full.json"
    return cache_dir / f"{episode.episode_id}.{model_name}.{truncation_seconds}s.json"


def _transcribe_with_whisper(
    whisper_model: WhisperModel,
    audio_path: Path,
) -> dict[str, Any]:
    segments_iter, info = whisper_model.transcribe(str(audio_path), language=None)

    segments = []
    next_segment_id = 0
    for seg in segments_iter:
        segments.append(
            {
                "id": next_segment_id,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            }
        )
        next_segment_id += 1

    full_text = " ".join(s["text"] for s in segments if s["text"]).strip()
    audio = AudioSegment.from_file(audio_path)
    duration = len(audio) / 1000.0

    return {
        "task": "transcribe",
        "language": info.language,
        "duration": round(duration, 1),
        "text": full_text,
        "segments": segments,
    }


def _transcribe_truncated_audio(
    whisper_model: WhisperModel,
    audio_path: Path,
    truncation_seconds: int,
) -> dict[str, Any]:
    full_audio = AudioSegment.from_file(audio_path)
    truncated = full_audio[: truncation_seconds * 1000]
    with tempfile.TemporaryDirectory(prefix="podcast_transcribe_") as tmp_dir:
        temp_path = Path(tmp_dir) / "truncated_clip.mp3"
        truncated.export(temp_path, format="mp3", bitrate="48k")
        return _transcribe_with_whisper(whisper_model, temp_path)
