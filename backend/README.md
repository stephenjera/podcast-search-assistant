# Backend

This backend is split into:

- `src/pipeline`: RSS ingest, download, transcription, chunking, DB writes
- `src/api`: FastAPI read/query layer for frontend
- `src/embeddings.py`: shared embedding client (Ollama) — used by BOTH the pipeline and the API, so corpus and query vectors always live in the same space

Shared modules live in `src/` root (`config.py`, `db.py`, `embeddings.py`, `logger.py`, `models.py`, `utils.py`).

## Prerequisites

- Python 3.12+
- `uv`
- Docker (for Postgres + pgvector via `docker-compose`)
- Ollama with the embedding model pulled: `ollama pull qwen3-embedding:8b`

> Transcription (faster-whisper `large-v3`) runs locally on CPU/GPU — no Ollama or API key needed for it.

## Install Dependencies

```bash
cd backend
uv sync
```

## Run Database

```bash
cd backend
docker compose up -d
```

## Run Ingestion Pipeline

Run from `backend/`:

```bash
cd backend
uv run python -m pipeline.ingest --limit 3
```

Useful examples:

```bash
uv run python -m pipeline.ingest --limit 1 --download-audio
uv run python -m pipeline.ingest --limit 1 --full-audio
uv run python -m pipeline.ingest --limit 1 --no-download-audio
```

Default behavior transcribes only the first `120` seconds of each episode locally with faster-whisper
(model from `TRANSCRIPTION_MODEL`, default `large-v3`). Transcripts are cached on disk under
`data/transcripts/` keyed by episode, model, and mode, so re-runs skip transcription.
Pass `--full-audio` to opt in to full-episode transcription.

Each run is recorded in the `ingest_runs` table (status, episodes processed, error) for a quick run summary.

## Run API

Run from `backend/`:

```bash
cd backend
uv run uvicorn api.main:app --reload --port 8000
```

## API Endpoints

- `GET /health`
- `GET /episodes`
- `GET /episodes/{episode_id}`
- `GET /episodes/{episode_id}/chunks`
- `POST /search`

`POST /search` request body supports:

- `query`: natural-language query
- `top_k` (optional): max hits
- `min_score` (optional): confidence threshold override
- `episode_id` (optional): scope search to a single episode

Search is vector-only. No lexical fallback path is used.
