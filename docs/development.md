# Development Guide

> RegulaRAG — AI-Powered Regulatory Intelligence & Compliance Analysis Platform

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| uv | 0.5+ | `pip install uv` or [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Docker Desktop | 4.x+ | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git | 2.x+ | [git-scm.com](https://git-scm.com/) |

---

## Environment Setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/Rabyegh/RegulaRAG.git
cd RegulaRAG
```

### 2. Create a virtual environment

```bash
uv venv .venv
```

### 3. Install all dependencies (runtime + dev + test)

```bash
uv pip install -e ".[dev,test]"
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and SECRET_KEY at minimum.
```

> [!CAUTION]
> Never commit `.env` to version control. It is pre-excluded by `.gitignore`.

---

## Local Development

### Start the backend application

```bash
uvicorn regularag.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the registered CLI entry point:

```bash
regularag
```

The API is available at:
- **Base URL**: `http://localhost:8000`
- **Interactive docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health check**: `http://localhost:8000/api/v1/health`

### Verify the health endpoint

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 1.234
}
```

---

## Docker Services

### Start only PostgreSQL (recommended for Phase 1–3)

```bash
docker compose up -d postgres
```

### Start all services

```bash
docker compose up -d
```

> [!NOTE]
> Elasticsearch requires at least 2 GB of heap memory. On machines with limited RAM, start only PostgreSQL and add Elasticsearch when working on Phase 4 search features.

### View service logs

```bash
docker compose logs -f postgres
docker compose logs -f backend
```

### Stop all services

```bash
docker compose down
```

### Destroy all services and volumes (removes all data)

```bash
docker compose down -v
```

### Rebuild and restart the backend container

```bash
docker compose build backend
docker compose up -d backend
```

---

## Testing

### Run all tests

```bash
uv run pytest
```

### Run with coverage

```bash
uv run pytest --cov=src/regularag --cov-report=term-missing
```

### Run only unit tests (no external services needed)

```bash
uv run pytest -m unit
```

### Run only integration tests

```bash
uv run pytest -m integration
```

### Run a specific test file

```bash
uv run pytest tests/unit/test_config.py -v
```

---

## Formatting and Linting

### Check for lint issues

```bash
uv run ruff check src/ tests/
```

### Auto-fix lint issues

```bash
uv run ruff check src/ tests/ --fix
```

### Check formatting

```bash
uv run ruff format src/ tests/ --check
```

### Auto-format code

```bash
uv run ruff format src/ tests/
```

### Type checking

```bash
uv run mypy src/
```

---

## Configuration Management

All configuration is managed through `src/regularag/core/config.py` using Pydantic Settings. Settings are loaded in this order (later values override earlier):

1. Default values defined in `AppSettings`.
2. Values from the `.env` file.
3. Values from environment variables.

The settings singleton is available via:

```python
from regularag.core.config import get_settings

settings = get_settings()
print(settings.app_name)
```

To reset the singleton during testing:

```python
from regularag.core.config import get_settings

get_settings.cache_clear()
```

---

## Git Workflow

### Branch naming

```
feat/phase-2-document-ingestion
fix/health-endpoint-uptime
docs/update-architecture-diagram
chore/update-dependencies
```

### Commit message convention

```
feat(module): short description of the change

Longer explanation if needed. Reference issues or ADRs.

Fixes #123
```

### Before committing

```bash
# Run all quality checks
uv run ruff check src/ tests/
uv run ruff format src/ tests/ --check
uv run pytest
```

### Ensure no secrets are staged

```bash
git diff --cached | grep -i "password\|secret\|api_key\|token"
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'regularag'`

The package is not installed in the active environment. Run:
```bash
uv pip install -e "."
```

### `POSTGRES_PASSWORD must be set in .env`

Docker Compose requires `POSTGRES_PASSWORD` to be set. Copy `.env.example` to `.env` and set a password.

### Elasticsearch container fails to start

Elasticsearch requires the system `vm.max_map_count` to be increased on Linux:
```bash
sudo sysctl -w vm.max_map_count=262144
```
On Windows with Docker Desktop (WSL2 backend), this is typically handled automatically.

### `uv: command not found`

Install uv:
```bash
pip install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Port already in use

Change the port via environment variable:
```bash
API_PORT=8001 uvicorn regularag.main:app --port 8001
```

### Settings not loading from `.env`

Ensure the `.env` file is in the working directory from which you launch the application (the project root).

