import os
from datetime import timedelta

import pendulum
from airflow.sdk import Asset, dag, task

from tracker.ingest import ALL_PHASE1_SOURCES, run_source_ingestion


postgres_host = os.getenv("POSTGRES_HOST", "postgres")
postgres_db = os.getenv("POSTGRES_DB", "ai_tracker")
asset_schema = os.getenv("TRACKER_ASSET_SCHEMA", "public")
raw_ai_events_table = os.getenv("TRACKER_RAW_AI_EVENTS_TABLE", "raw_events")
dag_schedule = os.getenv("AI_TRACKER_DAG_SCHEDULE", "0 9 * * *")
dag_start_date = os.getenv("AI_TRACKER_DAG_START_DATE", "2026-11-01T00:00:00+00:00")

RAW_AI_EVENTS_ASSET = Asset(
    f"postgres://{postgres_host}/{postgres_db}/{asset_schema}/{raw_ai_events_table}"
)


@dag(
    dag_id="ai_tracker_phase1_ingest",
    schedule=dag_schedule,
    start_date=pendulum.parse(dag_start_date, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["ai-tracker", "phase-1", "ingestion"],
)
def ai_tracker_phase1_ingest():
    @task(pool="web_scraping_pool", outlets=[RAW_AI_EVENTS_ASSET])
    def ingest_source(source: str) -> dict:
        return run_source_ingestion(source=source)

    ingest_source.expand(source=ALL_PHASE1_SOURCES)

ai_tracker_phase1_ingest()
