import { useEffect, useMemo, useState } from "react";
import type { SyntheticEvent } from "react";

import { EpisodeBrowser } from "./components/EpisodeBrowser";
import { SearchForm } from "./components/SearchForm";
import { SearchResults } from "./components/SearchResults";
import { getEpisodes, searchPodcasts } from "./lib/api";
import type { EpisodeSummary, SearchHit } from "./lib/api";

function App() {
  const [episodes, setEpisodes] = useState<EpisodeSummary[]>([]);
  const [episodesLoading, setEpisodesLoading] = useState(true);
  const [episodesError, setEpisodesError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [minScore, setMinScore] = useState(0.1);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string | null>(
    null,
  );
  const [episodeTitleFilter, setEpisodeTitleFilter] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [searchNoMatchReason, setSearchNoMatchReason] = useState<
    string | null
  >(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await getEpisodes();
        if (cancelled) return;
        setEpisodes(response.episodes);
      } catch (error) {
        if (cancelled) return;
        setEpisodesError(
          error instanceof Error ? error.message : "Failed to load episodes",
        );
      } finally {
        if (!cancelled) setEpisodesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedEpisode = useMemo(
    () => episodes.find((episode) => episode.episode_id === selectedEpisodeId) ?? null,
    [episodes, selectedEpisodeId],
  );

  async function onSearchSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;

    setSearchLoading(true);
    setSearchError(null);
    setSearchHits([]);
    setSearchNoMatchReason(null);

    try {
      const response = await searchPodcasts({
        query,
        top_k: topK,
        min_score: minScore,
        episode_id: selectedEpisodeId ?? undefined,
      });
      setSearchHits(response.hits);
      setSearchNoMatchReason(response.no_match_reason);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Search failed");
    } finally {
      setSearchLoading(false);
    }
  }

  function onToggleEpisodeScope(episodeId: string) {
    setSelectedEpisodeId((current) =>
      current === episodeId ? null : episodeId,
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#fef3c7_0%,#fff7ed_35%,#f8fafc_75%)] text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-3xl border border-amber-200/70 bg-white/75 p-6 shadow-sm backdrop-blur-sm">
          <p className="text-xs font-semibold tracking-[0.18em] text-amber-600 uppercase">
            Podcast Search Assistant
          </p>
          <h1 className="mt-2 text-3xl leading-tight font-bold md:text-4xl">
            Find Transcript References Fast
          </h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-700 md:text-base">
            Search globally across episodes or narrow scope to one episode from
            the browser below.
          </p>
        </header>

        <main className="mt-6">
          <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <SearchForm
                query={query}
                topK={topK}
                minScore={minScore}
                searchLoading={searchLoading}
                selectedEpisodeTitle={selectedEpisode?.title ?? null}
                onQueryChange={setQuery}
                onTopKChange={setTopK}
                onMinScoreChange={setMinScore}
                onSubmit={onSearchSubmit}
                onClearScope={() => setSelectedEpisodeId(null)}
              />
              <SearchResults
                hits={searchHits}
                loading={searchLoading}
                error={searchError}
                noMatchReason={searchNoMatchReason}
              />
            </div>
            <EpisodeBrowser
              episodes={episodes}
              episodesLoading={episodesLoading}
              episodesError={episodesError}
              titleFilter={episodeTitleFilter}
              selectedEpisodeId={selectedEpisodeId}
              onTitleFilterChange={setEpisodeTitleFilter}
              onEpisodeSelect={onToggleEpisodeScope}
            />
          </section>
          <section className="mt-4">
            {selectedEpisode && (
              <p className="text-xs text-amber-700">
                Searching within episode: <strong>{selectedEpisode.title}</strong>
              </p>
            )}
            {!selectedEpisode && (
              <p className="text-xs text-slate-500">
                Searching across all episodes.
              </p>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
