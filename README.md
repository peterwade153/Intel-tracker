# Intel-tracker

Automated AI lab and ecosystem release tracker.

Collects releases and announcements from Hacker News (Algolia API) and RSS feeds (OpenAI, Google DeepMind), enriches them, and stores them in Postgres with pgvector for vector search. Orchestrated by Apache Airflow 3.4.0 with a CeleryExecutor.

- **Python:** 3.12+
- **Orchestrator:** Apache Airflow 3.4.0 (CeleryExecutor)
- **Database:** Postgres 17 with pgvector
- **Broker:** Redis 7.2
- **Build:** hatchling (`pyproject.toml`)
- **DAG:** `ai_tracker_phase1_ingest` — daily at 9:00 AM UTC by default
- **Tables:** `raw_events`, `ai_events` (enriched), `schema_migrations`


## Overview

Intel-tracker ingests AI industry releases from public sources, normalizes them into raw events, and persists them for downstream enrichment and semantic search.

Collection flow per DAG run:

1. Hacker News is polled via the Algolia `search_by_date` endpoint for AI-related stories.
2. OpenAI and Google DeepMind RSS feeds are fetched and parsed.
3. Raw events are upserted into `raw_events` keyed by `canonical_url` (idempotent).
4. The `raw_events` table is emitted as an Airflow dataset asset for downstream consumers.
5. The `enrich_raw_events` task reads new raw events, cleans content with trafilatura,
   categorizes/scores them, embeds via Ollama (`nomic-embed-text`), and upserts into
   `ai_events`.

Airflow services:

| Service | Role |
|---------|------|
| `airflow-apiserver` | REST API and web UI (port 8080) |
| `airflow-scheduler` | Schedules and dispatches task instances |
| `airflow-worker` | Executes ingestion + enrichment tasks via Celery |
| `airflow-dag-processor` | Parses DAG files |
| `airflow-triggerer` | Runs deferrable operators |
| `airflow-init` | One-shot: DB migration, SQL migrations, pool creation |
| `ollama` | Local embedding server (port 11434) |
| `postgres` | pgvector-enabled Postgres (port 5433 → 5432) |
| `redis` | Celery message broker (port 6379) |


## Sources

| Source key | Lab | Mechanism | Details |
|------------|-----|-----------|---------|
| `hacker_news` | `community` | Algolia API | `hn.algolia.com/api/v1/search_by_date`, query for AI labs/LLMs, min 25 points |
| `openai_news` | `openai` | RSS feed | `https://openai.com/news/rss.xml` |
| `google_deepmind` | `google_deepmind` | RSS feed | `https://deepmind.google/blog/feed/basic/` |
| `liquid_ai` | `liquid_ai` | RSS feed (Substack) | `https://liquidai.substack.com/feed.xml` (Liquid AI blog has no native RSS) |

Feed collection retries HTTP errors with exponential backoff (3 attempts).

## Enrichment Phase

The DAG includes a second task, `enrich_raw_events`, that runs downstream of all
ingestion tasks. It reads raw events that have no matching `ai_events` row and:

1. **Extracts content** — fetches each `canonical_url` and cleans the main article
   body with trafilatura (`tracker/extractors/content.py`).
2. **Categorizes** — heuristic keyword-based tagging (`models`, `engineering`,
   `research`, `news`, `uncategorized`).
3. **Scores impact** — heuristic 1–10 score based on title keywords and HN points.
4. **Embeds** — passes the summary through Ollama's `nomic-embed-text` model
   into a 768-dim vector stored in `ai_events.embedding` (pgvector).
5. **Upserts** — idempotently inserts/updates `ai_events` keyed by `canonical_url`.

The embedder is pluggable via `tracker/pipeline/enrich.py:run_enrichment(embed=...)`.
The DAG wires in `tracker/embeddings/ollama.py:OllamaEmbedder`, which calls the
Ollama `/api/embed` endpoint over HTTP.

## Prerequisites

- Python 3.12
- Docker and Docker Compose (recommended for the full stack)
- PostgreSQL 17 with the `pgvector` extension (if not using Docker)
- Redis 7.2 (if not using Docker)
- Ollama (bundled as a service in `docker-compose.yml`; the `nomic-embed-text`
  model is pulled automatically by the `ollama-init` service on stack startup)

## Installation

```bash
# Clone the repository
git clone https://github.com/peterwade153/Intel-tracker
cd Intel-tracker

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the tracker package (hatchling build system)
pip install -e .

# Install Airflow and provider dependencies
pip install "apache-airflow==3.4.0"
pip install "apache-airflow-providers-postgres"
pip install "apache-airflow-providers-redis"
pip install "apache-airflow-providers-celery"

# Copy the environment sample and fill in values
cp .env.sample .env
# Edit .env with your settings (never commit real secrets)
```

The project uses `pyproject.toml` with the hatchling build system. The `tracker` package is the installable unit. Add runtime dependencies to `pyproject.toml` under `[project.dependencies]`, then `pip install -e .`.

Dev dependencies (`pytest`, `ruff`) are in the `dev` optional group:

```bash
pip install -e ".[dev]"
```

## Running the Stack

### Docker Compose (recommended)

```bash
cp .env.sample .env   # then fill in JWT secret, Fernet key, etc.
docker compose up --build
```

Initialize the database and apply migrations (one time):

```bash
docker compose run --rm airflow-init
```

This runs `airflow db migrate`, `python -m tracker.storage.migrate`, and creates the `web_scraping_pool`.

The `ollama-init` service starts automatically with `docker compose up` and pulls
the `nomic-embed-text` model into Ollama before enrichment tasks run.

Open the Airflow UI at `http://localhost:8080`.


```bash
docker compose exec postgres psql -U airflow -d ai_tracker \
  -c "SELECT source, count(*) FROM raw_events GROUP BY source;"
```

### Running Airflow Manually

If not using Docker, start Postgres (with pgvector) and Redis, then:

```bash
# Initialize Airflow metadata database
airflow db migrate

# Apply tracker SQL migrations
TRACKER_DATABASE_URL=... python -m tracker.storage.migrate

# Create the scraping pool
airflow pools set web_scraping_pool 3 "Outbound scraping and API requests"

# Optional: create an admin user for the UI
airflow users create \
  --username airflow \
  --firstname Airflow \
  --lastname Admin \
  --role Admin \
  --email airflow@example.com

# Start each service in its own terminal
airflow api-server            # UI at http://localhost:8080
airflow scheduler
airflow celery worker
airflow dag-processor
airflow triggerer
```

## Backend Development

The `tracker` package is the core library. It is installed editable via `pip install -e .` and mounted into Airflow containers at `/opt/airflow/project/tracker`.


### Add a dependency

```bash
pip install <package>
```

Then add it to `[project.dependencies]` in `pyproject.toml`.

### Embedding model

The `ai_events.embedding` column is `vector(768)`. The DAG wires in
`tracker/embeddings/ollama.py:OllamaEmbedder`, which calls Ollama's
`/api/embed` endpoint with the `nomic-embed-text` model (768-dimensional output,
no API key required, runs locally via the `ollama` service in `docker-compose.yml`).

To use a different model, set `OLLAMA_EMBED_MODEL` in `.env` and add a new
migration in `sql/` (e.g. `003_alter_embedding_dimension.sql`) with an
`ALTER TABLE ai_events ALTER COLUMN embedding TYPE vector(<dims>)` statement.
Never modify `001_init.sql` after it has been applied — the migration runner
verifies checksums and will reject changes.

## Testing

Run the test suite with pytest:

```bash
pytest
```

Tests live in `tests/`. There are currently no tests; add them as the project grows.

## Linting

Ruff is configured in `pyproject.toml` (`line-length = 100`, target `py311` — note the project requires Python 3.12).

```bash
ruff check tracker
ruff check dags
```

Run lint before declaring a task done.

## CI

A GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and pull request. It installs dependencies, lints, type-checks, and runs the test suite.


## Contributing

1. Branch from `master` as `feature/<name>`.
2. Use Conventional Commits.
3. Stage changes for review.
4. Do not commit to `master` or push without being asked.
