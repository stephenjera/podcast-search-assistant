"""A/B benchmark harness for semantic search quality.

Loads gold queries (each tied to the episode it SHOULD match) and
unrelated probes (expected to score low), then reports:
- per-query top-k hits with raw scores (threshold NOT applied)
- hit@1 / hit@k against the expected episode
- score distribution of top-1 scores (signal = gold, noise = probes)
- a suggested SEARCH_MIN_SCORE: the midpoint between the worst gold
  top-1 score and the best probe top-1 score, when they are separable.

Queries file (JSON), at `benchmark/queries.json`:
    {
      "gold":     [{"id": "...", "query": "...", "expect_episode": "<external_episode_id>"}],
      "probes":   [{"id": "...", "query": "..."}]
    }

Usage (from eval/):
    uv run python -m podcast_eval.benchmark [--queries queries.json] [--top-k 5]
"""

import argparse
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from podcast_core.repository import vector_search
from podcast_core.config import settings
from podcast_core.db import get_db_connection
from podcast_core.embeddings import embed_texts
from podcast_core.logger import get_logger

logger = get_logger(__name__)

EVAL_ROOT = Path(__file__).resolve().parents[1]  # <repo>/eval
DEFAULT_QUERIES_PATH = EVAL_ROOT / "queries.json"
RESULTS_DIR = EVAL_ROOT / "results"


@dataclass
class QueryResult:
    query_id: str
    query: str
    kind: str  # "gold" | "probe"
    expect_episode: str | None = None
    top1_score: float = 0.0
    top1_episode: str | None = None
    expected_rank: int | None = None  # 1-based rank of expected episode in top-k
    hit_at_1: bool = False
    hits: list[dict] = field(default_factory=list)


def run_benchmark(
    queries_path: Path,
    top_k: int,
    write_results: bool = True,
) -> list[QueryResult]:
    spec = json.loads(queries_path.read_text(encoding="utf-8"))
    gold = spec.get("gold", [])
    probes = spec.get("probes", [])

    results: list[QueryResult] = []
    with get_db_connection() as conn:
        for entry in gold:
            results.append(_run_one(conn, entry, top_k, kind="gold"))
        for entry in probes:
            results.append(_run_one(conn, entry, top_k, kind="probe"))

    if write_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_path = RESULTS_DIR / f"results-{stamp}.json"
        out_path.write_text(
            json.dumps(
                [
                    {
                        "id": r.query_id,
                        "query": r.query,
                        "kind": r.kind,
                        "expect_episode": r.expect_episode,
                        "top1_score": r.top1_score,
                        "top1_episode": r.top1_episode,
                        "expected_rank": r.expected_rank,
                        "hit_at_1": r.hit_at_1,
                        "hits": r.hits,
                    }
                    for r in results
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nFull results written to {out_path}")
    return results


def _run_one(conn, entry: dict, top_k: int, *, kind: str) -> QueryResult:
    query = entry["query"]
    result = QueryResult(
        query_id=entry["id"],
        query=query,
        kind=kind,
        expect_episode=entry.get("expect_episode"),
    )
    print(f"\n=== [{kind}] {entry['id']}: {query!r}")

    vector = embed_texts([query])[0]
    hits = vector_search(conn=conn, query_vector=vector, top_k=top_k)
    for hit in hits:
        snippet = hit.text if len(hit.text) <= 120 else hit.text[:117] + "..."
        print(f"  {hit.score:.3f}  {hit.episode_id[:12]}  {snippet}")
        result.hits.append(
            {
                "score": hit.score,
                "episode_id": hit.episode_id,
                "episode_title": hit.episode_title,
                "text": hit.text,
                "start_time": hit.start_time,
            }
        )

    if hits:
        result.top1_score = hits[0].score
        result.top1_episode = hits[0].episode_id
    if result.expect_episode and hits:
        for rank, hit in enumerate(hits, start=1):
            if hit.episode_id == result.expect_episode:
                result.expected_rank = rank
                break
    result.hit_at_1 = (
        result.expect_episode is not None
        and result.top1_episode == result.expect_episode
    )
    return result


def summarise(results: list[QueryResult]) -> dict:
    gold = [r for r in results if r.kind == "gold"]
    probes = [r for r in results if r.kind == "probe"]

    def dist(scores: list[float]) -> dict:
        if not scores:
            return {}
        scores = sorted(scores)
        def pct(p: float) -> float:
            idx = min(len(scores) - 1, max(0, round(p * (len(scores) - 1))))
            return scores[idx]
        return {
            "n": len(scores),
            "min": round(scores[0], 4),
            "p25": round(pct(0.25), 4),
            "median": round(statistics.median(scores), 4),
            "p90": round(pct(0.9), 4),
            "max": round(scores[-1], 4),
        }

    gold_scores = [r.top1_score for r in gold]
    probe_scores = [r.top1_score for r in probes]
    summary = {
        "gold": {"queries": len(gold), "hit_at_1": sum(r.hit_at_1 for r in gold),
                 "top1_dist": dist(gold_scores)},
        "probes": {"queries": len(probes), "top1_dist": dist(probe_scores)},
        "current_search_min_score": settings.SEARCH_MIN_SCORE,
        "suggested_min_score": None,
    }
    if gold_scores and probe_scores:
        worst_gold = min(gold_scores)
        best_probe = max(probe_scores)
        if worst_gold > best_probe:
            summary["suggested_min_score"] = round((worst_gold + best_probe) / 2, 3)
        else:
            summary["note"] = (
                "no separable threshold: worst gold "
                f"{worst_gold:.3f} <= best probe {best_probe:.3f}"
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-save", action="store_true", help="skip writing results JSON")
    args = parser.parse_args()

    results = run_benchmark(args.queries, args.top_k, write_results=not args.no_save)
    summary = summarise(results)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  gold:   {summary['gold']['queries']} queries, "
          f"hit@1 = {summary['gold']['hit_at_1']}/{summary['gold']['queries']}")
    print(f"  gold top-1 dist:   {summary['gold']['top1_dist']}")
    print(f"  probe top-1 dist:  {summary['probes']['top1_dist']}")
    print(f"  current SEARCH_MIN_SCORE: {summary['current_search_min_score']}")
    if summary.get("suggested_min_score"):
        print(f"  SUGGESTED SEARCH_MIN_SCORE: {summary['suggested_min_score']}")
    if summary.get("note"):
        print(f"  {summary['note']}")


if __name__ == "__main__":
    main()
