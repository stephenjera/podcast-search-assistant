# podcast-eval

Benchmark harness for search quality. `queries.json` holds gold queries (tied to the episode they SHOULD match) and unrelated probes (expected to score low).

```bash
uv sync
uv run python -m podcast_eval.benchmark [--queries queries.json] [--top-k 5]
```

Reports per-query top-k scores, hit@1, gold-vs-probe top-1 score distributions, and a suggested `SEARCH_MIN_SCORE` (midpoint when separable). Results are written to `results/` (gitignored).

Current baseline (5-episode corpus, qwen3-embedding:8b): 11/11 hit@1, gold top-1 min 0.493, probe top-1 max 0.379 → threshold 0.44.
