import argparse
from pathlib import Path

from config import settings
from db import get_db_connection
from logger import get_logger
from pipeline.audio import download_episode_audio
from pipeline.chunking import build_chunks_from_transcript
from pipeline.embeddings import embed_texts
from pipeline.repository import (
    replace_chunks,
    upsert_audio_asset,
    upsert_episode,
    upsert_transcript,
)
from pipeline.rss import fetch_episodes
from pipeline.transcription import load_or_transcribe_episode, transcript_cache_path
from utils import read_json, write_json

logger = get_logger(__name__)

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
EPISODES_PATH = DATA_ROOT / "episodes.json"
AUDIO_DIR = DATA_ROOT / "audio"
TRANSCRIPT_DIR = DATA_ROOT / "transcripts"
DEFAULT_TRUNCATION_SECONDS = 120


def run_ingestion(args: argparse.Namespace) -> None:
    feed_url = args.feed_url or settings.PODCAST_FEED_URL
    episodes = fetch_episodes(feed_url, limit=args.limit)
    write_json(EPISODES_PATH, [episode.model_dump() for episode in episodes])
    logger.info(f"Fetched {len(episodes)} episodes")

    with get_db_connection() as conn:
        for episode in episodes:
            logger.info(f"Processing episode: {episode.title}")
            episode_db_id = upsert_episode(conn, episode)

            audio_path = None
            if args.download_audio:
                audio_path = download_episode_audio(episode, AUDIO_DIR)
            else:
                possible_audio = AUDIO_DIR / f"{episode.episode_id}.mp3"
                if possible_audio.exists():
                    audio_path = possible_audio

            if audio_path and audio_path.exists():
                upsert_audio_asset(conn, episode_db_id, audio_path)

            transcript = None
            if audio_path and audio_path.exists():
                transcript = load_or_transcribe_episode(
                    episode=episode,
                    audio_path=audio_path,
                    cache_dir=TRANSCRIPT_DIR,
                    full_audio=args.full_audio,
                    truncation_seconds=DEFAULT_TRUNCATION_SECONDS,
                )
            else:
                cached_path = transcript_cache_path(
                    TRANSCRIPT_DIR,
                    episode,
                    full_audio=args.full_audio,
                    truncation_seconds=DEFAULT_TRUNCATION_SECONDS,
                )
                if cached_path.exists():
                    transcript = read_json(cached_path)

            if transcript is None:
                logger.warning("Skipping episode: no transcript available")
                conn.commit()
                continue

            transcript_path = transcript_cache_path(
                TRANSCRIPT_DIR,
                episode,
                full_audio=args.full_audio,
                truncation_seconds=DEFAULT_TRUNCATION_SECONDS,
            )
            transcript_db_id = upsert_transcript(
                conn=conn,
                episode_db_id=episode_db_id,
                transcript_path=transcript_path,
                transcript=transcript,
                model_name=settings.TRANSCRIPTION_MODEL,
            )

            chunks = build_chunks_from_transcript(
                episode=episode,
                transcript=transcript,
                max_chars=args.max_chunk_chars,
            )
            if not chunks:
                logger.warning("Skipping episode: transcript yielded no chunks")
                conn.commit()
                continue

            vectors = embed_texts([chunk.text for chunk in chunks])
            replace_chunks(
                conn=conn,
                episode_db_id=episode_db_id,
                transcript_db_id=transcript_db_id,
                chunks=chunks,
                vectors=vectors,
            )
            conn.commit()
            logger.info(f"Stored {len(chunks)} chunks for episode")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Podcast ingestion pipeline")
    parser.add_argument("--feed-url", default=None, help="RSS feed URL")
    parser.add_argument(
        "--limit", type=int, default=3, help="Number of episodes to process"
    )
    parser.add_argument(
        "--download-audio",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Download episode audio files",
    )
    parser.add_argument("--max-chunk-chars", type=int, default=600)
    parser.add_argument(
        "--full-audio",
        action="store_true",
        help="Transcribe full episode audio (default transcribes first 120 seconds)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_ingestion(args)


if __name__ == "__main__":
    main()
