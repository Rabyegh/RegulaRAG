-- =============================================================================
-- RegulaRAG — PostgreSQL initialisation script
-- =============================================================================
-- This script runs once when the PostgreSQL container is first created.
-- It enables the pgvector extension required for vector similarity search
-- (Phase 3+). The regularag database and user are already created by the
-- POSTGRES_DB / POSTGRES_USER environment variables.
-- =============================================================================

-- Enable pgvector extension for vector similarity search (Phase 3+)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for trigram-based text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

