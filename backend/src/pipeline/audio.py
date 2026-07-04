import urllib.request
from pathlib import Path

from logger import get_logger
from models import Episode
from utils import ensure_parent

logger = get_logger(__name__)


def download_episode_audio(episode: Episode, output_dir: Path) -> Path | None:
    if not episode.audio_url:
        logger.warning("Episode has no audio URL; skipping download")
        return None

    output_path = output_dir / f"{episode.episode_id}.mp3"
    if output_path.exists():
        logger.info("Audio already exists locally, using cached file")
        return output_path

    ensure_parent(output_path)
    logger.info("Downloading episode audio")
    urllib.request.urlretrieve(episode.audio_url, output_path)  # nosec: B310
    return output_path
