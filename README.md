# Podcast Search Assistant

Search podcast transcripts with natural language. Fully local: transcription with faster-whisper, embeddings with Ollama, storage in Postgres + pgvector.

## Repository layout

| Package | What it is | Talks to |
|---|---|---|
| `core/` | `podcast-core` — shared library: config, DB, Ollama embedding client, models, shared read SQL, corpus provenance (`schema_meta`) | Postgres, Ollama |
| `pipeline/` | `podcast-pipeline` — ingest: RSS, audio download, whisper transcription, chunking, embedding, write to DB | core, Postgres, Ollama |
| `backend/` | `podcast-backend` — FastAPI query service (`/search`, `/episodes`) | core, Postgres, Ollama |
| `eval/` | `podcast-eval` — benchmark harness (gold queries vs unrelated probes) + `queries.json` | core, Postgres, Ollama |
| `frontend/` | React + TypeScript SPA | backend |

Shared state lives at the repo root: `db/` (SQL migrations), `docker-compose.yml` (Postgres), `.env` (local config), `data/` (gitignored: audio + transcript caches).

Dependency rule: `pipeline`, `backend`, and `eval` all depend on `core`; **nothing depends on the pipeline, and the API never imports pipeline code.** `core` is a library baked into each consumer's artifact (Docker image / venv) — it is not itself a deployed service.

## Prerequisites

- Python 3.10+ with [uv](https://docs.astral.sh/uv/)
- Docker (for Postgres)
- [Ollama](https://ollama.com) running locally
- Node.js 20+ (frontend only)

## Quickstart

```bash
# 1. Database (from repo root)
docker compose up -d
docker exec -i -u postgres postgres psql -U docker -d postgres < db/init/001_extensions.sql
docker exec -i -u postgres postgres psql -U docker -d postgres < db/init/002_schema.sql
docker exec -i -u postgres postgres psql -U docker -d postgres < db/init/003_schema_meta.sql

# 2. Embedding model
ollama pull qwen3-embedding:8b

# 3. Ingest a few episodes (from pipeline/)
cd pipeline && uv sync
uv run python -m podcast_pipeline.ingest --limit 5 --full-audio

# 4. API (from backend/)
cd ../backend && uv sync
uv run uvicorn podcast_backend.main:app --port 8000

# 5. Frontend (from frontend/)
cd ../frontend && npm install
npm run dev   # dev server proxies /api to :8000

# 6. Optional: benchmark search quality (from eval/)
cd ../eval && uv sync
uv run python -m podcast_eval.benchmark
```

## Environment variables

All packages read the same `.env` at the repo root (or env vars). See `.env.example`.

| Variable | Default | Used by | Notes |
|---|---|---|---|
| `DATABASE_URL` | `postgres://docker:docker@localhost:5432/postgres` | all | Postgres connection |
| `EMBEDDING_MODEL` | `qwen3-embedding:8b` | pipeline, backend, eval | **Must match the corpus** — see below |
| `OLLAMA_URL` | `http://localhost:11434` | pipeline, backend, eval | |
| `TRANSCRIPTION_MODEL` | `large-v3` | pipeline | faster-whisper model size |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | `cpu` / `int8` | pipeline | set `cuda`/`float16` on GPU |
| `SEARCH_MIN_SCORE` | `0.44` | backend | calibrated via `eval/` (gold min 0.493 vs probe max 0.379) |
| `PODCAST_DATA_ROOT` | `<repo>/data` | pipeline | audio + transcript caches |

## Corpus provenance (store is source of truth)

The store records which models produced the corpus (`schema_meta`: `embedding_model`, `embedding_dimensions`, `transcription_model`):

- **Pipeline** warns at ingest start if the existing corpus was embedded by a different model than configured (mixed-vector corpus → degraded search), and re-stamps `schema_meta` after a successful run.
- **API** validates at startup and **fails loudly** if the configured `EMBEDDING_MODEL` doesn't match the stamped corpus (when the corpus is non-empty).

So switching embedding models requires a deliberate re-ingest — it can never silently mix incompatible vectors.

## Design notes

- **Vector-only search**: every hit score is semantically meaningful; when nothing clears `SEARCH_MIN_SCORE` the API returns `hits: []` with `no_match_reason`.
- **No vector index**: pgvector HNSW caps at 2000 dims and the model outputs 4096, so `chunks.embedding` uses a linear scan — fine at local corpus size (see `db/init/002_schema.sql`).
- **Ingest defaults to first 120 s** of audio for fast loops; `--full-audio` is explicit opt-in. Transcripts are cached in `data/transcripts/` keyed by `{episode}.{model}.{mode}.json`, so model changes never silently serve stale transcripts.
- **Threshold calibration**: `SEARCH_MIN_SCORE=0.44` comes from the eval harness on the 5-episode corpus (gold top-1 min 0.493, probe top-1 max 0.379). Re-run the harness after corpus or model changes.
- **Whisper naming caveat**: large-v3 can garble proper names in this corpus; benchmark gold queries anchor on phrasing, not names.

## Next steps (parked)

- Local embedding-model A/B: `qwen3-embedding:8b` vs `0.6b` vs `embeddinggemma:300m` (re-embed corpus, rerun harness)
- Hybrid lexical + vector ranking, reranking of top-N
- Scheduling/queueing for ingest; unit + integration tests; containerisation
