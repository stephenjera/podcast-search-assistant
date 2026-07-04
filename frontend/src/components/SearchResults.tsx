import type { SearchHit } from "../lib/api";
import { SearchHitCard } from "./SearchHitCard";

type SearchResultsProps = {
  hits: SearchHit[];
  loading: boolean;
  error: string | null;
  noMatchReason: string | null;
};

export function SearchResults({
  hits,
  loading,
  error,
  noMatchReason,
}: SearchResultsProps) {
  return (
    <div className="mt-5">
      {error && <p className="mb-3 text-sm text-red-700">{error}</p>}
      {noMatchReason && <p className="mb-3 text-xs text-slate-500">{noMatchReason}</p>}

      <div className="space-y-3">
        {hits.map((hit) => (
          <SearchHitCard key={hit.chunk_id} hit={hit} />
        ))}
      </div>

      {!loading && !error && hits.length === 0 && noMatchReason && (
        <p className="mt-3 text-sm text-slate-500">No results to show for this query.</p>
      )}
    </div>
  );
}
