# podcast-pipeline

Ingest pipeline: RSS → audio download → faster-whisper transcription → chunking → Ollama embeddings → Postgres/pgvector.

```bash
uv sync
uv run python -m podcast_pipeline.ingest --limit 5 --full-audio
```

Options:
- `--limit N` — first N feed episodes
- `--full-audio` — transcribe the whole episode (default: first 120 s)
- `--download-audio` — force re-download of audio

Behaviour:
- Transcripts are cached in `data/transcripts/{episode}.{model}.{mode}.json` (cache key includes model + mode, so a model change never serves stale transcripts).
- Each run is tracked in `ingest_runs`; a successful run re-stamps `schema_meta` with the embedding/transcription models used. A corpus stamped with a different embedding model produces a loud warning at start.
- Whisper defaults to CPU/int8 for portability; set `WHISPER_DEVICE=cuda WHISPER_COMPUTE_TYPE=float16` for GPU.
