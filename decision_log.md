# Decision Log

Append-only journal. Informal notebook, not official docs. Oldest entries at the top.

## 2026-08-27 — v2 direction: fully local, end-to-end

- v2 goal: the whole project (pipeline + backend + frontend) must run end-to-end on a local machine. No OpenAI API keys, no internet required at runtime (except RSS feed fetch).
- Postgres + pgvector in Docker stays — it already runs locally and is a clean boundary between the write path (pipeline) and read path (API).
- v2 branch state at review time: 1 commit + uncommitted local-inference migration (OpenAI → faster-whisper + sentence-transformers, embedding dim 1536 → 384). Direction was right but the model choices were placeholders; standardised below.

## 2026-08-27 — Embedding model: Ollama qwen3-embedding:8b

- **Chosen: `qwen3-embedding:8b` (4096 dims) via Ollama HTTP.** Both the pipeline (ingest) and the API (query) use the same model — mixed models would break search.
- Considered: `embeddinggemma:300m` (768 dims, below text-embedding-3-small), `qwen3-embedding:0.6b` (1024, ≈ text-embedding-3-small level), `all-MiniLM-L6-v2` (384, weakest, 2020-era), OpenAI `text-embedding-3` (v1 baseline — the 8b is at/above `text-embedding-3-large` on most English retrieval evals, free, offline).
- Actual download was 4.7 GB (Q4_K_M GGUF), not the 24 GB pre-quantised figure; already pulled and running on the 3090 Ti.
- Schema follows the model: `VECTOR(4096)`. Existing 1536/384-dim chunks get re-embedded (transcripts stay cached on disk, so switching models never re-transcribes).
- `SEARCH_MIN_SCORE=0.10` is a v1 OpenAI-era guess — recalibrate from measured score distributions (P1 A/B harness) before trusting any threshold.

## 2026-08-27 — Whisper model: faster-whisper large-v3

- **Chosen: `large-v3`** over `medium`/`small`. Reason: transcription sets the quality ceiling of the whole chain — an embedding model can only rank text that exists. Podcast audio (names, two speakers, slang) is exactly where small/medium diverge.
- Ollama has no speech-to-text model, so faster-whisper stays — already wired into the pipeline.
- Download is ~4.3 GB (was partial, completed 2026-08-27). Machine: RTX 3090 Ti 24 GB (busy), 32 cores, 15 GB RAM — large-v3 runs fine on CPU int8 (~20–40 min per 45-min episode) or faster on GPU when VRAM frees up.
- **Bug found in review:** transcript cache path was keyed by episode + mode only (`{id}.120s.json`), not the whisper model. Changing `TRANSCRIPTION_MODEL` silently serves stale transcripts. Fix: include the model in the cache path.

## 2026-08-27 — Priorities for v2 (Option A)

1. **P0 — stabilise the local baseline, commit it.** Standardise on the two models above, shared Ollama embedding client for pipeline + API, `VECTOR(4096)`, drop `openai`/`pydantic-ai` deps and `OPENAI_API_KEY`, delete `backend/whiler_local/` (prototype already integrated), rename `backend/database` (data volume) → `backend/data/postgres` to stop the `data/` vs `database/` vs `db/` (init SQL) confusion, fix stale READMEs, fix the cache-keying bug, commit green baseline.
2. **P1 — real corpus + A/B harness.** Ingest 5–10 full 45-min episodes (feed `the-news-agents` has 1,201 full episodes — corpus size is not a constraint). The old 3 × 2-min clips only exist because `--full-audio` was opt-in for fast dev loops. Build a gold query set (20–30 queries with hand-picked answer chunks), score models with recall@k/MRR + score distributions → data-driven `SEARCH_MIN_SCORE`. Harness stays in-repo as a regression tool for future model/chunk changes.
3. **P2 — structural split.** Decide the pipeline↔API package boundary (two `pyproject.toml`s vs one package with clean module lines) with P1 evidence in hand, so we don't refactor twice.

## 2026-08-27 — P0 implementation notes

- `data/` layout settled: `backend/data/{audio,transcripts,postgres}` + `backend/db/init` (SQL). Old `backend/database` removed (dev data was disposable; wiped via container — no sudo on box).
- HNSW index on `chunks.embedding` does NOT work at 4096 dims (pgvector 0.8.5: "column cannot have more than 2000 dimensions for hnsw index"). Decision: no vector index for now — linear scan is fine at local scale. If search latency becomes a problem, options are: matryoshka truncation via Ollama `dimensions` option to <=2000 dims (+HNSW), or bit-vector quantization + rerank. Flag for P1 corpus.
- Old whisper-1 (OpenAI) 2-min clip transcripts deleted — they were from feed positions no longer in the top-N, and large-v3 regenerates in minutes. Audio mp3s kept on disk (harmless).
- `ingest_runs` table added + pipeline records run start/finish (status, episodes processed, error) — first line of observability.

## 2026-08-27 — P0 verification results (first real data)

- End-to-end green on fresh episode "Is this Labour's first woman leader?": RSS → download → large-v3 (120s, ~60s wall) → 4 chunks → 8b embed → Postgres → API. `ingest_runs` recorded.
- Cache naming works: `9bb705…large-v3.120s.json`.
- **First threshold data point (qwen3-embedding:8b):** related query "who sponsors the podcast" → top score **0.474**; unrelated query ("quantum chromodynamics") → **0.321**. Current `SEARCH_MIN_SCORE=0.10` passes BOTH — confirmed far too permissive. Expect the calibrated threshold to land ~0.35–0.40; will pin it with the P1 score distribution.

## 2026-02-17 — P0 done, committed

All P0 work landed: models switched (qwen3-embedding:8b + large-v3), shared embedding client, model-keyed transcript cache, ingest_runs table, dependency cleanup, folder layout (`data/postgres`, `db/init`), READMEs updated to match reality. Green baseline committed.

One gotcha worth remembering: `uvicorn` running against the old code kept the deleted `pipeline.embeddings` module in memory and still served requests — old processes don't notice dependency removals until they restart. Restarted it cleanly.

Next up (P1): real corpus (a handful of full 45-min episodes), A/B benchmark harness with gold queries, and threshold calibration off the score distribution.
