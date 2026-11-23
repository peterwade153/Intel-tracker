CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    lab TEXT NOT NULL,
    external_id TEXT,
    canonical_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    raw_summary TEXT,
    raw_content TEXT,
    content_hash TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_raw_events_source_published ON raw_events (source, published_at DESC);

CREATE TABLE IF NOT EXISTS ai_events (
    id BIGSERIAL PRIMARY KEY,
    raw_event_id BIGINT UNIQUE REFERENCES raw_events(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    lab TEXT NOT NULL,
    canonical_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'uncategorized',
    summary TEXT,
    impact_score SMALLINT,
    published_at TIMESTAMPTZ,
    enriched_at TIMESTAMPTZ,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_events_enriched_at ON ai_events (enriched_at NULLS FIRST, published_at DESC);
