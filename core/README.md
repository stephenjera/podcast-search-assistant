# podcast-core

Shared library for the local podcast stack. Not a service — it's installed into the `pipeline/`, `backend/`, and `eval/` environments.

Contents (`podcast_core/`):
- `config.py` — settings + `.env` discovery + shared data-dir paths
- `db.py` — Postgres connection helper
- `embeddings.py` — Ollama embedding client (`embed_texts`)
- `models.py` — Pydantic domain models (Episode, Chunk)
- `repository.py` — shared **read-path** SQL (plain dataclass rows, no service schemas)
- `meta.py` — corpus provenance: `schema_meta` stamping + startup validation
- `logger.py`, `utils.py` — shared plumbing

```bash
uv sync   # in core/
```

Note: consumers install this as a local path dependency (`[tool.uv.sources]`). After changing core, run `uv sync --reinstall-package podcast-core` in each consumer.
