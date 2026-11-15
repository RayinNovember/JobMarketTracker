"""Tests for the dashboard's queries and the app itself (Module 11).

All of them need a throwaway Postgres (never your Supabase project: they drop the
jobs and core schemas): TEST_DB_URL=postgresql://... uv run pytest
"""

import json
import os
from datetime import date
from pathlib import Path

import psycopg
import pytest

from core.text import ThemeTagger
from projects.linkedin_jobs.transform import merge_items, to_row

ROOT = Path(__file__).resolve().parent.parent
ITEMS = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text(encoding="utf-8"))
TAGGER = ThemeTagger.from_yaml(ROOT / "projects/linkedin_jobs/themes.yaml")
DB = os.environ.get("TEST_DB_URL")
OCT, NOV = date(2026, 10, 1), date(2026, 11, 1)

pytestmark = pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")


@pytest.fixture
def conn():
    """A fresh database: job 1 in October; jobs 2 and 3 (a repost of 2) in November."""
    from core import db
    from projects.linkedin_jobs import load

    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.execute("""
            do $$ begin
                if not exists (select from pg_roles where rolname = 'dashboard_reader') then
                    create role dashboard_reader;
                end if;
            end $$;
        """)
        conn.commit()
        db.migrate(conn)
        run_id = conn.execute("insert into core.run_log (project) values ('t') returning run_id").fetchone()[0]
        for items, term, seen in [(ITEMS[:1], "data scientist", OCT), (ITEMS[1:], "data analyst", NOV)]:
            merged = merge_items({term: items})
            load.upsert_postings(conn, run_id, [to_row(i, t, TAGGER) for i, t in merged.values()], seen)
            conn.commit()
        yield conn


def test_filter_options(conn):
    from projects.linkedin_jobs import queries

    assert queries.filter_options(conn) == {"terms": ["data analyst", "data scientist"], "months": [OCT, NOV]}


def test_dashboard_counts_roles_not_reposts(conn):
    from projects.linkedin_jobs import queries

    d = queries.dashboard(conn, ["data scientist", "data analyst"], OCT, NOV)
    assert d["summary"]["roles"] == 2            # jobs 2 and 3 are one role
    assert d["summary"]["median_salary"] == 145000  # job 1: $130K-$160K/yr; job 2 is hourly
    assert len(d["postings"]) == 2
    assert {r["industry"] for r in d["industries"]} == {"Hospitals and Health Care", "Staffing and Recruiting"}
    assert all(0 < t["pct"] <= 100 for t in d["themes"])
    assert "Machine learning modeling" in d["postings"][-1]["themes"]


def test_dashboard_filters(conn):
    from projects.linkedin_jobs import queries

    october = queries.dashboard(conn, ["data scientist", "data analyst"], OCT, OCT)
    assert october["summary"]["roles"] == 1
    analysts = queries.dashboard(conn, ["data analyst"], OCT, NOV)
    assert [p["title"] for p in analysts["postings"]] == [ITEMS[1]["title"]]
    nothing = queries.dashboard(conn, ["nobody searched this"], OCT, NOV)
    assert nothing["summary"]["roles"] == 0 and nothing["themes"] == []


def test_reader_role_can_read_but_not_write(conn):
    conn.execute("set role dashboard_reader")
    assert conn.execute("select count(*) from jobs.postings_dedup").fetchone()[0] == 2
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("delete from jobs.postings")
    conn.rollback()


def test_app_runs(conn, monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    st.cache_data.clear()  # another test may have cached results from a different database state
    at = AppTest.from_file(str(ROOT / "projects/linkedin_jobs/app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.metric[0].value == "2"
    at.sidebar.multiselect[1].set_value(["Machine learning modeling"]).run()
    assert not at.exception
    assert "Your biggest gaps" in at.markdown[-1].value
