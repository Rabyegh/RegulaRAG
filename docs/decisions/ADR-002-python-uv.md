# ADR-002: Python and uv for Backend Development

**Date:** 2026-11-02  
**Status:** Accepted  
**Phase:** 1 — Project Foundation

---

## Context

The backend language and package management toolchain need to be selected. The platform is deeply integrated with the AI/ML ecosystem and requires fast iteration, strong typing support, and an extensive package ecosystem for NLP, vector databases, and LLM integration.

---

## Decision

Use **Python 3.12+** as the backend programming language and **uv** as the package and virtual environment manager.

Use **pyproject.toml** as the single source of truth for project metadata, dependencies, and tool configuration (Ruff, mypy, pytest, coverage).

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| Node.js / TypeScript | Limited AI/ML ecosystem compared to Python; fewer LLM and vector DB client libraries. |
| Go | Excellent performance but almost no native AI/ML ecosystem; no viable RAG or embedding libraries. |
| pip + requirements.txt | No dependency resolution guarantees, no lock file, poor support for optional dependency groups. |
| Poetry | Slower than uv; uv is now the industry-leading standard for Python project management with significantly better performance. |
| Conda | Heavier environment, not well-suited to production Docker images. |

---

## Consequences

**Positive:**
- Python has the richest AI/ML ecosystem: Sentence Transformers, LangGraph, RAGAS, OpenAI SDK, Hugging Face.
- uv provides near-instant dependency resolution and virtual environment creation.
- `pyproject.toml` consolidates all project tooling in one file.
- Python 3.12+ provides improved performance and type annotation features.

**Negative:**
- Python's GIL limits true CPU parallelism (mitigated by async I/O and worker processes).
- Python is slower than compiled languages; acceptable given that AI model inference dominates latency.

---

## Trade-offs

Python's position as the primary language of AI/ML makes it the natural choice despite performance trade-offs. The uv toolchain provides excellent developer experience that offsets any friction from Python's historic dependency management complexity.

