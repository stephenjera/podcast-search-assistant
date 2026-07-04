import type { EpisodeSummary } from "../lib/api";

type EpisodeCardProps = {
  episode: EpisodeSummary;
  selected: boolean;
  onSelect: (episodeId: string) => void;
};

function formatPublishedDate(value: string | null): string {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function EpisodeCard({ episode, selected, onSelect }: EpisodeCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(episode.episode_id)}
      className={`w-full rounded-2xl border p-3 text-left transition ${
        selected
          ? "border-amber-400 bg-amber-50"
          : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <p className="text-sm font-semibold text-slate-800">{episode.title}</p>
      <p className="mt-1 text-xs text-slate-500">
        {formatPublishedDate(episode.published_at)}
      </p>
    </button>
  );
}
