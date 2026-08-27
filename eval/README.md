# podcast-eval

Benchmark harness for search quality. `queries.json` holds gold queries (tied to the episode they SHOULD match) and unrelated probes (expected to score low).

```bash
uv sync
uv run python -m podcast_eval.benchmark [--queries queries.json] [--top-k 5]
```

Reports per-query top-k scores, hit@1, gold-vs-probe top-1 score distributions, and a suggested `SEARCH_MIN_SCORE` (midpoint when separable). Results are written to `results/` (gitignored).

Current baseline (5-episode corpus, qwen3-embedding:8b): 11/11 hit@1, gold top-1 min 0.493, probe top-1 max 0.379 → threshold 0.44.

### A/B comparing embedding models

```bash
uv run python -m podcast_eval.ab_embedding_models [--model NAME]...
```

For each model: embeds all stored chunk texts **and** the benchmark queries
using that model (each model's vectors are compared in its own cosine space),
then scores hit@1 / top-5 and the gold-vs-probe distributions. In-memory —
nothing is written to the database. The 8b row reproduces the benchmark
baseline and validates the harness. Note: running several models back-to-back
evicts each other from GPU memory (and may evict whatever chat model is
resident — Ollama manages that).
