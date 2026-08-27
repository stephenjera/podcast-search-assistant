"""A/B compare embedding models in-memory, against the existing benchmark set.

For each candidate model we embed ALL stored chunk texts and the benchmark
queries using THAT model (each model is self-consistent: its own vectors,
its own cosine space), then compute:
  * hit@1:  does the top-1 chunk belong to the gold episode?
  * top-5:  is the gold episode among the 5 distinct best episodes?
  * score distributions for gold vs probe top-1, and a suggested
    SEARCH_MIN_SCORE (midpoint) when the two are separable.

The current 8b model row must reproduce the 11/11 benchmark baseline —
that validates the harness itself.

No data is written anywhere. Requires Postgres + Ollama running.

Usage:
    cd eval
    uv run python -m podcast_eval.ab_embedding_models
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import psycopg
from psycopg.rows import dict_row

from podcast_core.config import settings
from podcast_core.embeddings import embed_texts
from podcast_core.utils import cosine_similarity

EVAL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES_PATH = EVAL_ROOT / "queries.json"
RESULTS_DIR = EVAL_ROOT / "results"

MODELS = [
    "qwen3-embedding:8b",     # current, 4096 dims
    "qwen3-embedding:0.6b",   # candidate, 1024 dims (HNSW-indexable)
    "embeddinggemma:300m",    # candidate, 768 dims (HNSW-indexable)
]


def _fetch_chunks(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.external_episode_id AS episode_id, c.chunk_index, c.text_content
          FROM chunks c
          JOIN episodes e ON e.id = c.episode_id
         ORDER BY e.external_episode_id, c.chunk_index
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _cosine_top1(query_vec: list[float], corpus_vecs: list[list[float]],
                 chunks: list[dict]) -> tuple[float, str]:
    best_score, best_idx = -1.0, 0
    for i, vec in enumerate(corpus_vecs):
        s = cosine_similarity(query_vec, vec)
        if s > best_score:
            best_score, best_idx = s, i
    return best_score, chunks[best_idx]["episode_id"]


def _top5_episodes(query_vec: list[float], corpus_vecs: list[list[float]],
                   chunks: list[dict]) -> list[str]:
    scores = [cosine_similarity(query_vec, v) for v in corpus_vecs]
    ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
    episodes: list[str] = []
    for i in ranked:
        ep = chunks[i]["episode_id"]
        if ep not in episodes:
            episodes.append(ep)
        if len(episodes) == 5:
            break
    return episodes


def evaluate_model(model: str, chunks: list[dict], gold: list[dict],
                   probes: list[dict]) -> dict:
    print(f"\n=== {model} ===")

    texts = [c["text_content"] for c in chunks]
    t0 = time.monotonic()
    corpus_vecs = embed_texts(texts, model=model)
    corpus_secs = time.monotonic() - t0
    dims = len(corpus_vecs[0])
    print(f"  corpus: {len(texts)} chunks -> {dims} dims in {corpus_secs:.1f}s")

    query_texts = [q["query"] for q in gold] + [q["query"] for q in probes]
    t0 = time.monotonic()
    query_vecs = embed_texts(query_texts, model=model)
    query_secs = time.monotonic() - t0
    print(f"  queries: {len(query_texts)} in {query_secs:.1f}s")

    gold_results = []
    for q, vec in zip(gold, query_vecs[: len(gold)]):
        score, top1 = _cosine_top1(vec, corpus_vecs, chunks)
        eps = _top5_episodes(vec, corpus_vecs, chunks)
        hit1 = top1 == q["expect_episode"]
        top5 = q["expect_episode"] in eps
        gold_results.append({
            "id": q["id"], "query": q["query"],
            "top1_score": round(score, 4),
            "top1_episode": top1,
            "hit_at_1": hit1, "hit_in_top5": top5,
        })

    probe_results = []
    for q, vec in zip(probes, query_vecs[len(gold):]):
        score, top1 = _cosine_top1(vec, corpus_vecs, chunks)
        probe_results.append({
            "id": q["id"], "query": q["query"],
            "top1_score": round(score, 4),
            "top1_episode": top1,
        })

    gold_scores = [r["top1_score"] for r in gold_results]
    probe_scores = [r["top1_score"] for r in probe_results]
    hits = sum(r["hit_at_1"] for r in gold_results)
    top5s = sum(r["hit_in_top5"] for r in gold_results)
    suggested = None
    if max(probe_scores) < min(gold_scores):
        suggested = round((min(gold_scores) + max(probe_scores)) / 2, 4)

    print(f"  hit@1: {hits}/{len(gold)}   top-5: {top5s}/{len(gold)}")
    print(f"  gold  top-1: min={min(gold_scores):.4f} mean={mean(gold_scores):.4f} max={max(gold_scores):.4f}")
    print(f"  probe top-1: min={min(probe_scores):.4f} mean={mean(probe_scores):.4f} max={max(probe_scores):.4f}")
    if suggested:
        print(f"  suggested SEARCH_MIN_SCORE: {suggested}")
    for r in gold_results:
        mark = "ok " if r["hit_at_1"] else "MISS"
        print(f"    [{mark}] {r['top1_score']:.4f} {r['id']}")
    for r in probe_results:
        print(f"    [probe] {r['top1_score']:.4f} {r['id']}")

    return {
        "model": model,
        "dimensions": dims,
        "corpus_embed_secs": round(corpus_secs, 1),
        "query_embed_secs": round(query_secs, 1),
        "hit_at_1": f"{hits}/{len(gold)}",
        "hit_in_top5": f"{top5s}/{len(gold)}",
        "gold_top1": {"min": min(gold_scores), "mean": round(mean(gold_scores), 4), "max": max(gold_scores)},
        "probe_top1": {"min": min(probe_scores), "mean": round(mean(probe_scores), 4), "max": max(probe_scores)},
        "suggested_min_score": suggested,
        "gold": gold_results,
        "probes": probe_results,
    }


def run_ab(queries_path: Path = DEFAULT_QUERIES_PATH,
           models: list[str] | None = None,
           write_results: bool = True) -> dict:
    data = json.loads(queries_path.read_text())
    gold = data["gold"]
    probes = data.get("probes", [])
    models = models or MODELS

    print("Loading chunks ...")
    with psycopg.connect(settings.DATABASE_URL, row_factory=dict_row) as conn:
        chunks = _fetch_chunks(conn)
    if not chunks:
        raise SystemExit("No chunks in database — run the pipeline first.")
    print(f"  {len(chunks)} chunks across "
          f"{len({c['episode_id'] for c in chunks})} episodes")

    results = [evaluate_model(m, chunks, gold, probes) for m in models]

    if write_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / f"ab-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "corpus_chunks": len(chunks),
            "models": results,
        }
        out.write_text(json.dumps(payload, indent=2))
        print(f"\nResults written to {out}")
    return {"corpus_chunks": len(chunks), "models": results}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="A/B embedding models")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES_PATH)
    parser.add_argument("--model", action="append",
                        help="Restrict to specific model(s); repeatable")
    parser.add_argument("--no-write", action="store_true",
                        help="Do not write results to eval/results/")
    args = parser.parse_args()
    run_ab(args.queries, args.model, write_results=not args.no_write)
