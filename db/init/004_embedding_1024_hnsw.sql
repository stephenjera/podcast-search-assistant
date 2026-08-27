-- 004: standard embedding model switched to qwen3-embedding:0.6b (1024 dims).
-- The column is dimension-bounded, so existing vectors must be dropped and
-- re-embedded via the pipeline (see decision log 2026-08-27 A/B entry).
-- HNSW works because 1024 <= the 2000-dim pgvector HNSW cap (8b at 4096 never could).
UPDATE chunks SET embedding = NULL;
ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1024);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
