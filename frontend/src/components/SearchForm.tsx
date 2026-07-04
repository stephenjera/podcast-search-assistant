import type { SyntheticEvent } from "react";

type SearchFormProps = {
  query: string;
  topK: number;
  minScore: number;
  searchLoading: boolean;
  selectedEpisodeTitle: string | null;
  onQueryChange: (value: string) => void;
  onTopKChange: (value: number) => void;
  onMinScoreChange: (value: number) => void;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onClearScope: () => void;
};

export function SearchForm({
  query,
  topK,
  minScore,
  searchLoading,
  selectedEpisodeTitle,
  onQueryChange,
  onTopKChange,
  onMinScoreChange,
  onSubmit,
  onClearScope,
}: SearchFormProps) {
  return (
    <form onSubmit={onSubmit} className="grid gap-3">
      <label className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
        Natural-language query
      </label>
      <textarea
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="Where was Trump mentioned?"
        rows={3}
        className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-200"
      />

      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Top K
          </span>
          <input
            value={topK}
            onChange={(event) => onTopKChange(Number(event.target.value))}
            min={1}
            max={25}
            type="number"
            className="w-full rounded-xl border border-slate-300 p-2 text-sm outline-none focus:border-amber-400"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Min Score
          </span>
          <input
            value={minScore}
            onChange={(event) => onMinScoreChange(Number(event.target.value))}
            min={0}
            max={1}
            step={0.01}
            type="number"
            className="w-full rounded-xl border border-slate-300 p-2 text-sm outline-none focus:border-amber-400"
          />
        </label>
      </div>

      <p className="text-xs text-slate-500">
        Scope:{" "}
        {selectedEpisodeTitle ? (
          <span className="font-semibold text-amber-700">{selectedEpisodeTitle}</span>
        ) : (
          "All episodes"
        )}
      </p>

      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={searchLoading}
          className="inline-flex items-center justify-center rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-600 disabled:opacity-50"
        >
          {searchLoading ? "Searching..." : "Run Search"}
        </button>
        {selectedEpisodeTitle && (
          <button
            type="button"
            onClick={onClearScope}
            className="inline-flex items-center justify-center rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Clear Scope
          </button>
        )}
      </div>
    </form>
  );
}
