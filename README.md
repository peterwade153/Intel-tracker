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


## Sources

| Source key | Lab | Mechanism | Details |
|------------|-----|-----------|---------|
| `hacker_news` | `community` | Algolia API | `hn.algolia.com/api/v1/search_by_date`, query for AI labs/LLMs, min 25 points |
| `openai_news` | `openai` | RSS feed | `https://openai.com/news/rss.xml` |
| `google_deepmind` | `google_deepmind` | RSS feed | `https://deepmind.google/blog/feed/basic/` |

Feed collection retries HTTP errors with exponential backoff (3 attempts).

## Prerequisites

- Python 3.12
- Docker and Docker Compose (recommended for the full stack)
- PostgreSQL 17 with the `pgvector` extension (if not using Docker)
- Redis 7.2 (if not using Docker)

## Installation

```bash
# Clone the repository
git clone <repository-url>
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
