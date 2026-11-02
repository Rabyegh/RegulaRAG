# ADR-001: Modular Monolith Architecture

**Date:** 2026-11-02  
**Status:** Accepted  
**Phase:** 1 — Project Foundation

---

## Context

RegulaRAG requires an architecture that can handle a complex, multi-stage AI pipeline (document ingestion → processing → retrieval → generation → evaluation) while remaining maintainable and testable during early development.

The two primary architectural options considered were a **microservices architecture** and a **modular monolith**.

---

## Decision

Adopt a **modular monolith** architecture for the initial platform implementation.

The backend is a single Python package (`regularag`) with clearly separated internal modules (`core`, `api`, `ingestion`, `processing`, `retrieval`, `rag`, `graph`, `intelligence`, `evaluation`), each with its own namespace and responsibilities.

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| Microservices from Day 1 | Premature operational complexity (service discovery, inter-service networking, distributed tracing) without demonstrated need. Adds significant development overhead in early phases. |
| Single flat module | Poor maintainability as the codebase grows. Makes testing individual components difficult. |
| Serverless functions | Not suited to the stateful, in-process AI pipeline (embedding models, connection pools). High cold-start latency incompatible with interactive query requirements. |

---

## Consequences

**Positive:**
- Single deployable unit simplifies CI/CD, debugging, and local development.
- Module boundaries are enforced by code conventions and imports, not network calls.
- Easier to refactor and restructure before patterns stabilise.
- Any module can be extracted into a microservice later if scale demands it.

**Negative:**
- All modules share the same Python process (cannot scale individual components independently).
- A bug in one module can affect the entire process.

---

## Trade-offs

This decision prioritises **developer velocity and maintainability** over **independent scalability**. The decision is revisited if any single module demonstrates a need for independent scaling (e.g., the embedding pipeline processing large document batches).

