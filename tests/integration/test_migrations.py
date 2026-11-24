from __future__ import annotations

import os
import tempfile

import pytest

from tracker.storage.migrate import apply_sql_migrations


def test_migrate_apply_new_sql(db_engine, clean_tables):
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY);")

        applied = apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))
        assert "001_test.sql" in applied


def test_migrate_skip_already_applied(db_engine, clean_tables):
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("CREATE TABLE IF NOT EXISTS test_table2 (id SERIAL PRIMARY KEY);")

        applied1 = apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))
        assert "001_test.sql" in applied1

        applied2 = apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))
        assert applied2 == []


def test_migrate_checksum_mismatch(db_engine, clean_tables):
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("CREATE TABLE IF NOT EXISTS test_table3 (id SERIAL PRIMARY KEY);")

        apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))

        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("CREATE TABLE IF NOT EXISTS test_table3 (id SERIAL PRIMARY KEY, name TEXT);")

        with pytest.raises(RuntimeError, match="Checksum mismatch"):
            apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))


def test_migrate_empty_dir(db_engine, clean_tables):
    with tempfile.TemporaryDirectory() as tmpdir:
        applied = apply_sql_migrations(tmpdir, db_engine.url.replace("+psycopg", ""))
        assert applied == []
