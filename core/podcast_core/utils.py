import hashlib
import json
import re
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "untitled-episode"


def stable_id(*values: str) -> str:
    digest = hashlib.sha256("::".join(values).encode("utf-8")).hexdigest()
    return digest[:20]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    mins = total // 60
    secs = total % 60
    return f"{mins:02d}:{secs:02d}"
