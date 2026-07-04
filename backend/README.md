# Backend

This backend is split into:

- `src/pipeline`: RSS ingest, download, transcription, chunking, embeddings, DB writes
- `src/api`: FastAPI read/query layer for frontend

Shared modules live in `src/` root (`config.py`, `db.py`, `logger.py`, `models.py`, `utils.py`).

## Prerequisites

- Python 3.12+
- `uv`
- Docker (for Postgres + pgvector via `docker-compose`)

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

Default behavior transcribes only the first `120` seconds of each episode in-memory before calling OpenAI.
Pass `--full-audio` to opt in to full-episode transcription.

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
