import email.utils
import urllib.request
import xml.etree.ElementTree as ET

from logger import get_logger
from models import Episode
from utils import slugify, stable_id

logger = get_logger(__name__)


def _first_text(item: ET.Element, names: list[str]) -> str | None:
    for name in names:
        child = item.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return None


def _pubdate_iso(pub_date: str | None) -> str | None:
    if not pub_date:
        return None
    try:
        return email.utils.parsedate_to_datetime(pub_date).isoformat()
    except Exception:
        return pub_date


def fetch_episodes(feed_url: str, limit: int) -> list[Episode]:
    logger.info("Fetching RSS feed metadata")
    with urllib.request.urlopen(feed_url, timeout=30) as response:  # nosec: B310
        root = ET.fromstring(response.read())

    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS feed missing <channel> node")

    episodes: list[Episode] = []
    for item in channel.findall("item")[:limit]:
        title = _first_text(item, ["title"]) or "Untitled Episode"
        guid = _first_text(item, ["guid"]) or _first_text(item, ["link"]) or title
        link = _first_text(item, ["link"])
        pub_date = _first_text(item, ["pubDate"])
        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url") if enclosure is not None else None

        episodes.append(
            Episode(
                episode_id=stable_id(guid, slugify(title)),
                title=title,
                published_at=_pubdate_iso(pub_date),
                audio_url=audio_url,
                page_url=link,
            ),
        )
    return episodes
