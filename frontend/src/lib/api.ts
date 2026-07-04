export type SearchRequest = {
  query: string;
  top_k?: number;
  min_score?: number;
  episode_id?: string;
};

export type SearchHit = {
  score: number;
  chunk_id: string;
  episode_id: string;
  episode_title: string;
  text: string;
  start_time: number;
  end_time: number;
  timestamp_label: string;
  snippet: string;
  page_url: string | null;
  published_at: string | null;
};

export type SearchResponse = {
  query: string;
  search_mode: string;
  min_score_applied: number;
  no_match_reason: string | null;
  hits: SearchHit[];
};

export type EpisodeSummary = {
  episode_id: string;
  title: string;
  published_at: string | null;
  audio_url: string | null;
  page_url: string | null;
};

export type EpisodeListResponse = {
  episodes: EpisodeSummary[];
};

export type EpisodeDetailResponse = {
  episode: EpisodeSummary;
};

export type EpisodeChunk = {
  chunk_id: string;
  chunk_index: number;
  text: string;
  start_time: number;
  end_time: number;
  timestamp_label: string;
};

export type EpisodeChunksResponse = {
  episode_id: string;
  episode_title: string;
  published_at: string | null;
  page_url: string | null;
  chunks: EpisodeChunk[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`API ${response.status}: ${message}`);
  }

  return (await response.json()) as T;
}

export async function getEpisodes(): Promise<EpisodeListResponse> {
  return request<EpisodeListResponse>("/episodes");
}

export async function getEpisode(episodeId: string): Promise<EpisodeDetailResponse> {
  return request<EpisodeDetailResponse>(`/episodes/${episodeId}`);
}

export async function getEpisodeChunks(
  episodeId: string,
  limit = 500,
): Promise<EpisodeChunksResponse> {
  return request<EpisodeChunksResponse>(`/episodes/${episodeId}/chunks?limit=${limit}`);
}

export async function searchPodcasts(payload: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
