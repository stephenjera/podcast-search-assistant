# podcast-backend

FastAPI query service over the podcast corpus (`podcast_core.repository` read SQL + Ollama embeddings for the query vector).

```bash
uv sync
uv run uvicorn podcast_backend.main:app --port 8000
```

Endpoints:
- `GET /health`
- `GET /episodes` — episode list
- `GET /episodes/{episode_id}` — episode detail
- `GET /episodes/{episode_id}/chunks` — chunk list
- `POST /search` — body: `{"query": "...", "top_k": 5, "min_score": null, "episode_id": null}`; returns display-ready hits (`snippet`, `timestamp_label`) or `hits: []` with `no_match_reason` when nothing clears the threshold.

Startup contract: the app validates the configured `EMBEDDING_MODEL` against the corpus stamp in `schema_meta` and refuses to boot on mismatch (non-empty corpus) — re-ingest first if you changed models.

Note: this environment deliberately does **not** install faster-whisper/torch — transcription belongs to `pipeline/`.
