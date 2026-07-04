# Podcast Search Assistant

Small full-stack application that ingests podcast episodes and enables natural-language transcript search.

This repository is structured as:

- `backend/`: ingestion pipeline + FastAPI query API + Postgres/pgvector persistence
- `frontend/`: React + TypeScript + Tailwind CSS v4 SPA

Detailed runbooks:

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

## Shared Setup

### 1. Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+
- npm
- Docker (for Postgres + pgvector)

### 2. Start Database

```bash
cd backend
docker compose up -d
```

### 3. Install Backend Dependencies

```bash
cd backend
uv sync
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 5. Run Ingestion (example)

```bash
cd backend
uv run python -m pipeline.ingest --limit 1 --download-audio
```

### 6. Run Backend API

```bash
cd backend
uv run uvicorn api.main:app --reload --port 8000
```

### 7. Run Frontend

```bash
cd frontend
npm run dev
```

Frontend defaults to backend at `http://localhost:8000` (override with `VITE_API_BASE_URL`).

## Environment Variables

| Variable | Location | Required | Default | Purpose |
| --- | --- | --- | --- | --- |
| `OPENAI_API_KEY` | `backend/.env` | Yes (for transcription + embeddings) | none | OpenAI API access |
| `DATABASE_URL` | `backend/.env` | No | `postgresql://docker:docker@localhost:5432/postgres` | Backend DB connection |
| `PODCAST_FEED_URL` | `backend/.env` | No | `https://feeds.captivate.fm/the-news-agents/` | RSS source for ingestion |
| `TRANSCRIPTION_MODEL` | `backend/.env` | No | `whisper-1` | Model for audio transcription |
| `EMBEDDING_MODEL` | `backend/.env` | No | `text-embedding-3-small` | Model for semantic search vectors |
| `SEARCH_MIN_SCORE` | `backend/.env` | No | `0.10` | Minimum confidence threshold for results |
| `VITE_API_BASE_URL` | `frontend/.env.local` | No | `http://localhost:8000` | Frontend API base URL |

## Design Notes

This section summarises the key tradeoffs and decisions used to arrive at the current app.

### Architecture Choices

- **Pipeline and API split**:
  - `src/pipeline` handles expensive ingest workloads (RSS, audio download, transcription, chunking, embeddings).
  - `src/api` handles low-latency query/read contracts for frontend.
- **Postgres + pgvector**:
  - Single operational store for metadata, chunk text, and embeddings.
  - Supports both structured browsing (`episodes`) and semantic retrieval (`/search`).
- **API contract-first frontend**:
  - Frontend uses typed endpoint contracts and display-ready fields (`snippet`, `timestamp_label`).

### Tradeoffs

- **Vector-only search**:
  - No fallback so every hit score is semantically meaningful.
  - If no confident matches exist, the API returns `hits: []` with `no_match_reason`
- **Simple error model for MVP**:
  - Unhandled backend failures are logged server-side and returned as generic `500` errors.
  - We deferred typed error categories and retry policies.
- **Cost/speed-biased ingestion default**:
  - Ingestion transcribes the first 120 seconds by default; `--full-audio` is explicit opt-in.
  - This keeps development loops fast while still running real end-to-end ingestion.
- **Frontend structural pass over visual redesign**:
  - We split `App.tsx` into focused components and added episode-card browsing.
  - We intentionally deferred visual redesign, custom hooks extraction, debounce, and request cancellation.

### Why These Choices

- Keeps ingestion concerns away from request/response latency path.
- Simplifies local MVP deployment (one DB stack, one API, one SPA).
- Makes “search-first” and “episode-first” product flows possible from the same stored data.

### What Is Currently Covered

- RSS ingest from feed source
- Transcript generation (truncated to first 120 seconds by default, `--full-audio` opt-in)
- Chunking + embeddings + pgvector search
- Episode-scoped or global search
- Frontend UI for natural-language querying with optional episode-card scope

## Production Readiness (Next Steps)

These are the next improvements we would prioritize beyond V1.

### Data Pipeline

- Move ingestion to scheduled/queued workers with retry policies.
  - Depends on available data-platform tooling and deployment constraints.
- Consider extracting pipeline to a separate service/repo if team ownership or scaling needs require independent lifecycles.
- Storage strategy for audio at larger scale (object storage + lifecycle rules)

### LLM optimisation

- Improve threshold calibration for matches (how many matches to return)
- Add hybrid lexical + vector ranking strategy (improve match quality)
- Consider reranking model for top-N

### Observability

- API metrics (latency/error rate)
- Ingestion run summaries and alerts
- Add more logging

### Security

- Authentication and authorisation for API and Frontend
- Secret management outside local `.env`

### Testing

- Unit tests where relevant
- Integration tests for ingest and search contracts
- Deterministic smoke tests for demo workflows

### Deployment

- Containerisation strategy
- Target platform configuration
