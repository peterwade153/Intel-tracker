from __future__ import annotations

import hashlib
import os
from pathlib import Path
import psycopg


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_sql_migrations(sql_dir: str | Path, dsn: str) -> list[str]:
    directory = Path(sql_dir)
    if not directory.exists():
        return []

    sql_files = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix == ".sql"
    )

    applied_now: list[str] = []

    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("SELECT filename, checksum FROM schema_migrations")
            existing = {row[0]: row[1] for row in cur.fetchall()}

            for path in sql_files:
                digest = _sha256(path)
                if path.name in existing:
                    if existing[path.name] != digest:
                        raise RuntimeError(
                            f"Checksum mismatch for already-applied migration {path.name}"
                        )
                    continue

                sql_text = path.read_text(encoding="utf-8")
                cur.execute(sql_text)
                cur.execute(
                    """
                    INSERT INTO schema_migrations (filename, checksum)
                    VALUES (%s, %s)
                    """,
                    (path.name, digest),
                )
                applied_now.append(path.name)

        conn.commit()

    return applied_now


if __name__ == "__main__":
    migrations_dir = os.environ.get("TRACKER_SQL_DIR", "/opt/airflow/sql")
    target_dsn = os.environ.get("TRACKER_DATABASE_URL")
    if not target_dsn:
        raise RuntimeError(
            "TRACKER_DATABASE_URL environment variable is required"
        )
    target_dsn = target_dsn.replace("postgresql+psycopg://", "postgresql://")
    applied = apply_sql_migrations(migrations_dir, target_dsn)
    print(f"Applied migrations: {applied}")
