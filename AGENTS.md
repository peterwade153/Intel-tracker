# AGENTS.md — Intel-tracker

## Project Domain

AI lab and ecosystem release tracker. Collects releases and announcements from Hacker News (Algolia API) and RSS feeds (OpenAI, Google DeepMind, Liquid AI), enriches them, and stores them in Postgres with pgvector for vector search. Orchestrated by Apache Airflow 3.4.0 with CeleryExecutor.

## Project Setup and Management

- Python version: 3.12+
- Dependency management: `pip` and `pyproject.toml` (hatchling build system)
- Add a dependency: `pip install <package>`, then add to `pyproject.toml`
- Run tests: `pytest` (from repo root)
- Run unit tests: `pytest tests/unit/`
- Run integration tests: `pytest tests/integration/` (requires Postgres + pgvector)
- Run lint: `ruff check tracker dags tests`
- Run type check: `mypy tracker dags`
- Branch from `master` as `feature/<name>`, use Conventional Commits
- Stage changes for review. Don't commit to `master` or push without being asked.

## Testing

Tests live in `tests/` and are split into `unit/` (mocked, fast) and `integration/` (requires Postgres + pgvector).

### Prerequisites

```bash
pip install -e ".[dev]"
```

### Unit tests (no external services)

```bash
pytest tests/unit/
```

### Integration tests (requires Postgres + pgvector on port 5432)

```bash
# Create test database
createdb -U airflow ai_tracker_test

# Run
pytest tests/integration/
```

Or with a custom database URL:

```bash
TEST_DATABASE_URL=postgresql+psycopg://airflow:airflow@localhost:5432/ai_tracker_test pytest tests/integration/
```

### All tests

```bash
pytest
```

### Markers

- `integration` — tests requiring external services; run with `pytest -m "not integration"` to skip them

### Test structure

```
tests/
├── conftest.py              # Shared fixtures
├── pytest.ini               # Pytest config
├── unit/                    # Mocked, fast tests
│   ├── test_config.py
│   ├── test_collectors_feeds.py
│   ├── test_collectors_hacker_news.py
│   ├── test_extractors_content.py
│   ├── test_embeddings_ollama.py
│   ├── test_storage_db.py
│   └── test_pipeline_enrich.py
└── integration/             # Requires Postgres + pgvector
    ├── test_migrations.py
    ├── test_pipeline_enrich.py
    └── test_dag_run.py
```

## Architecture Overview

- **tracker/** — Python package (core library)
  - `collectors/` — Hacker News (Algolia), RSS feeds (OpenAI, DeepMind, Liquid AI)
  - `embeddings/` — Ollama embedder client (`/api/embed`)
  - `extractors/` — HTML content extraction (trafilatura)
  - `pipeline/` — Enrichment: categorize, score, embed, upsert to `ai_events`
  - `storage/` — `raw_events` and `ai_events` DB models, upsert, SQL migration runner
- **dags/** — Airflow DAG: `ai_tracker_phase1_ingest` (daily 9 AM UTC, CeleryExecutor)
- **sql/** — `001_init.sql` (tables), `002_alter_embedding_dimension.sql` (migration)
- **docker-compose.yml** — Postgres (pgvector), Redis, Airflow services, Ollama, Ollama-init

## API / Endpoints

No external HTTP API. Data is consumed via Airflow DAG runs and direct Postgres queries.

Tables: `raw_events`, `ai_events` (enriched, `embedding vector(768)`), `schema_migrations`

## Coding Conventions

- Type-hint public functions and methods, including return types (`from __future__ import annotations`)
- Use `pathlib` for path management; do not use `os.path`
- Prefer f-strings over `str.format()` or `%` formatting
- Follow EAFP: handle exceptions rather than checking conditions up front
- Write Google-style docstrings for every public function and method
- Validate data with Pydantic models
- Lint before declaring a task done: `ruff check tracker dags tests`
- Type-check: `mypy tracker dags`

## Constraints

- Ask before adding any external dependency
- Preserve the signature and response shape of existing functions
- Don't use blocking I/O inside `async` functions
- Keep existing tests intact; fix code to make them pass
- Declare a task done only after gates pass and docstrings are updated
- Never modify `sql/001_init.sql` after it's been applied — use new migration files instead (checksum verification)

## Ignore

- `.env` — secrets, never committed
- `logs/` — Airflow runtime logs
- `.venv/`, `build/`, `dist/`, `*.egg-info/` — build artifacts

## CI

`.github/workflows/ci.yml` runs lint, test, and type-check on push/PR to `master`.
