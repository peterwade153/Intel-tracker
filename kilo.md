# Kilo Setup Reference — Intel-tracker

## Environment

- Project: `/Users/walugembepeter/Documents/projects/ai-intel-tracker-env/Intel-tracker`
- Pre-existing venv: `/Users/walugembepeter/Documents/projects/ai-intel-tracker-env/`
  - Activate: `source /Users/walugembepeter/Documents/projects/ai-intel-tracker-env/bin/activate`
  - Python: 3.11.1
  - Includes: ruff, pytest, mypy, httpx, trafilatura, tenacity, pydantic, sqlalchemy, psycopg

## Common Commands

```bash
# Activate venv
source /Users/walugembepeter/Documents/projects/ai-intel-tracker-env/bin/activate

# Run unit tests (no external services)
pytest tests/unit/

# Run ruff lint
ruff check tracker dags tests

# Run mypy type check (tracker/ only; dags/ needs airflow installed)
mypy tracker

# Run all checks
ruff check tracker dags tests && pytest tests/unit/
```

## Git (not available in this environment)

Git is NOT installed in this sandbox. You must handle branch/commit/push locally:

```bash
# On your local machine, inside Intel-tracker/
git checkout master
git pull origin master
git checkout -b feature/<issue-name>
# make changes
git add -A
git commit -m "feat: <description>"
git push origin feature/<issue-name>
```

## Changes Made (this session)

Four issues addressed across 4 files:

1. **Issue 9 — vector_dim config** (`tracker/config.py`)
   - Added `get_vector_dim()` reading `AI_TRACKER_VECTOR_DIM` env var (default 768)
   - Added `get_enrich_max_iterations()` reading `AI_TRACKER_ENRICH_MAX_ITERATIONS` (default 50)

2. **Issue 7 — max_iterations env var** (`tracker/pipeline/enrich.py`)
   - `run_enrichment()` reads `AI_TRACKER_ENRICH_MAX_ITERATIONS` to override the `max_iterations` parameter
   - Invalid values log a warning and fall back to the default

3. **Issue 4 — parallelize content extraction** (`tracker/pipeline/enrich.py`)
   - `run_enrichment()` now uses `ThreadPoolExecutor` to enrich events concurrently
   - I/O-bound `extract_and_clean` (HTTP fetch) and `embed` (Ollama HTTP) calls run in parallel
   - Results are placed back in original order via index mapping

4. **Issue 8 — logging for web scraping and enrichment** (`tracker/extractors/content.py`, `tracker/pipeline/enrich.py`)
   - `content.py`: logs fetch start/end, extraction success/failure, byte counts
   - `enrich.py`: logs batch progress, iteration counts, upsert stats, zero-vector warnings

5. **Bonus** (`tracker/storage/enriched_db.py`)
   - `EnrichedEvent.embedding` default factory now uses `get_vector_dim()` instead of hardcoded 768

## Verification

- `ruff check tracker dags tests` — passes
- `pytest tests/unit/` — 39 passed, 1 error (DB connection refused; pre-existing, no postgres running)
- `mypy tracker` — clean (dags/ has pre-existing airflow/pendulum stub errors)
