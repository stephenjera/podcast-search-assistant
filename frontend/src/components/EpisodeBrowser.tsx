import { useMemo } from "react";

import type { EpisodeSummary } from "../lib/api";
import { EpisodeCard } from "./EpisodeCard";

type EpisodeBrowserProps = {
  episodes: EpisodeSummary[];
  episodesLoading: boolean;
  episodesError: string | null;
  titleFilter: string;
  selectedEpisodeId: string | null;
  onTitleFilterChange: (value: string) => void;
  onEpisodeSelect: (episodeId: string) => void;
};

export function EpisodeBrowser({
  episodes,
  episodesLoading,
  episodesError,
  titleFilter,
  selectedEpisodeId,
  onTitleFilterChange,
  onEpisodeSelect,
}: EpisodeBrowserProps) {
  const filteredEpisodes = useMemo(() => {
    const term = titleFilter.trim().toLowerCase();
    if (!term) return episodes;
    return episodes.filter((episode) => episode.title.toLowerCase().includes(term));
  }, [episodes, titleFilter]);

  return (
    <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold tracking-wide text-slate-700 uppercase">
        Browse Episodes
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Select a card to scope search. Click again to clear.
      </p>
      <label className="mt-3 block text-sm">
        <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600 uppercase">
          Filter by title
        </span>
        <input
          value={titleFilter}
          onChange={(event) => onTitleFilterChange(event.target.value)}
          placeholder="Search episode titles..."
          className="w-full rounded-xl border border-slate-300 p-2 text-sm outline-none focus:border-amber-400"
        />
      </label>

      <div className="mt-3 h-[28rem] overflow-y-auto rounded-2xl border border-slate-200 p-2">
        {episodesLoading && <p className="text-sm text-slate-500">Loading episodes...</p>}
        {episodesError && <p className="text-sm text-red-700">{episodesError}</p>}
        {!episodesLoading && !episodesError && filteredEpisodes.length === 0 && (
          <p className="text-sm text-slate-500">No episodes match this title filter.</p>
        )}
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
          {filteredEpisodes.map((episode) => (
            <EpisodeCard
              key={episode.episode_id}
              episode={episode}
              selected={selectedEpisodeId === episode.episode_id}
              onSelect={onEpisodeSelect}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
