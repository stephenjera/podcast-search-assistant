CREATE TABLE IF NOT EXISTS episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_episode_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    audio_url TEXT,
    page_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audio_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL UNIQUE REFERENCES episodes(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    file_sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL UNIQUE REFERENCES episodes(id) ON DELETE CASCADE,
    transcript_path TEXT NOT NULL,
    transcript_json JSONB NOT NULL,
    transcription_model TEXT,
    language TEXT,
    duration_seconds DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_chunk_id TEXT NOT NULL UNIQUE,
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    transcript_id UUID REFERENCES transcripts(id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    start_time_seconds DOUBLE PRECISION NOT NULL,
    end_time_seconds DOUBLE PRECISION NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_external_id ON episodes (external_episode_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_episode_id ON transcripts (episode_id);
CREATE INDEX IF NOT EXISTS idx_chunks_episode_id ON chunks (episode_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks (chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata_json_gin ON chunks USING GIN (metadata_json);
