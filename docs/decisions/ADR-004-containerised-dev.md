# ADR-004: Containerised Development Environment

**Date:** 2026-11-02  
**Status:** Accepted  
**Phase:** 1 — Project Foundation

---

## Context

The platform depends on multiple infrastructure services (PostgreSQL, Elasticsearch, Neo4j) that are difficult to install and configure reproducibly across different developer machines and operating systems. A consistent development environment is essential for team collaboration and CI/CD.

---

## Decision

Use **Docker** and **Docker Compose** to provide a fully containerised development environment for all infrastructure services.

The backend application itself is developed locally (using uv and the virtual environment) for fast iteration, while databases and search services run in Docker containers.

A multi-stage **Dockerfile** is also provided so the backend can be packaged and deployed as a container image in staging and production.

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| Native installation of all services | Non-reproducible across OS/versions; difficult to clean up; conflicts with existing system installations. |
| Vagrant | Heavier and slower than Docker; less widely used in the Python AI ecosystem. |
| Dev containers (full Docker development) | Slower inner loop for Python development; hot-reload in containers adds complexity. |
| Cloud-hosted services only | Creates a network dependency for local development; increases cost during early development. |

---

## Consequences

**Positive:**
- All developers use identical service versions regardless of their host OS.
- Services can be started, stopped, and reset with a single `docker compose` command.
- Persistent volumes ensure data survives container restarts.
- Health checks ensure services are ready before dependent containers start.
- The production Dockerfile provides a deployable artifact from the same codebase.

**Negative:**
- Requires Docker Desktop (or equivalent) on developer machines.
- Elasticsearch's memory requirements (≥2 GB heap) may be constraining on low-RAM laptops.

---

## Trade-offs

Docker Compose is the industry standard for multi-service local development environments. The memory overhead of Elasticsearch is mitigated by making it opt-in via the `profiles` mechanism (Phase 1) and documenting the lightweight alternative. The Dockerfile's multi-stage build keeps the production image minimal.

