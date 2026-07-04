import type { SearchHit } from "../lib/api";

type SearchHitCardProps = {
  hit: SearchHit;
};

export function SearchHitCard({ hit }: SearchHitCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <div className="mb-1 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-800">{hit.episode_title}</p>
        <span className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-slate-600">
          score {hit.score.toFixed(3)}
        </span>
      </div>
      <p className="text-xs text-slate-500">
        {hit.timestamp_label} • {hit.episode_id}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">{hit.snippet}</p>
    </article>
  );
}
