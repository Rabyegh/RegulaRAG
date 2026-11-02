# ADR-003: PostgreSQL as Primary Relational Database

**Date:** 2026-11-02  
**Status:** Accepted  
**Phase:** 1 — Project Foundation

---

## Context

The platform requires a primary database for storing regulatory documents, chunk metadata, processed embeddings, user data, and audit logs. The database must support vector similarity search for dense retrieval without requiring a separate dedicated vector database.

---

## Decision

Use **PostgreSQL 16** with the **pgvector extension** as the primary database.

pgvector enables storage and approximate nearest-neighbour search of dense embedding vectors directly within PostgreSQL, eliminating the need for a dedicated vector database (e.g., Pinecone, Weaviate, Qdrant) in the initial phases.

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| MySQL / MariaDB | No native vector search extension; weaker support for JSONB and full-text search. |
| MongoDB | Document store is a good fit for regulatory text but lacks ACID guarantees and native vector search. |
| Pinecone / Weaviate (dedicated vector DB) | Adds operational complexity and cost without a demonstrated need to exceed PostgreSQL+pgvector's capacity. |
| SQLite | Not production-ready for concurrent access; lacks pgvector. |

---

## Consequences

**Positive:**
- Single database for both relational data and vector embeddings reduces operational complexity.
- pgvector supports HNSW and IVFFlat indexes for scalable approximate nearest-neighbour search.
- ACID guarantees ensure data consistency for regulatory documents.
- Mature ecosystem: SQLAlchemy, Alembic, asyncpg.
- The `pgvector/pgvector:pg16` Docker image bundles everything in one container.

**Negative:**
- At very high embedding volumes (tens of millions of vectors), a dedicated vector database may outperform PostgreSQL+pgvector.
- This trade-off is acceptable for the initial regulatory scope (six frameworks, thousands of chunks).

---

## Trade-offs

PostgreSQL+pgvector is the pragmatic choice that minimises infrastructure complexity while providing the necessary vector search capability. The decision is revisited if vector search becomes a bottleneck during Phase 7 performance evaluation.

