from __future__ import annotations

from airflow.models import DagBag

DAG_ID = "ai_tracker_phase1_ingest"


def test_dag_loads_without_errors():
    """DAG file parses and registers without import errors."""
    dag_bag = DagBag(dag_folder="dags")
    assert dag_bag.dags.get(DAG_ID) is not None
    assert len(dag_bag.import_errors) == 0, f"DAG import errors: {dag_bag.import_errors}"


def test_dag_has_expected_tasks():
    """DAG contains ingest_source (mapped) and enrich_raw_events tasks."""
    dag_bag = DagBag(dag_folder="dags")
    dag = dag_bag.dags.get(DAG_ID)
    assert dag is not None

    task_ids = {t.task_id for t in dag.tasks}
    assert "ingest_source" in task_ids
    assert "enrich_raw_events" in task_ids


def test_dag_has_outlet_assets():
    """DAG defines outlet assets for raw_events and ai_events."""
    dag_bag = DagBag(dag_folder="dags")
    dag = dag_bag.dags.get(DAG_ID)
    assert dag is not None

    outlet_assets = set()
    for task in dag.tasks:
        for outlet in task.outlets or []:
            outlet_assets.add(outlet.name if hasattr(outlet, "name") else str(outlet))

    assert any("raw_events" in str(a) for a in outlet_assets)
    assert any("ai_events" in str(a) for a in outlet_assets)


def test_dag_schedule_is_daily():
    """DAG schedule defaults to daily 9 AM UTC."""
    dag_bag = DagBag(dag_folder="dags")
    dag = dag_bag.dags.get(DAG_ID)
    assert dag is not None
    assert dag.schedule_interval == "0 9 * * *"
