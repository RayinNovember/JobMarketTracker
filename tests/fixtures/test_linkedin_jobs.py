"""Tests for the LinkedIn jobs pipeline.

Transform tests always run. Database tests run when TEST_DB_URL points at a
throwaway Postgres (never your Supabase project):
    TEST_DB_URL=postgresql://... uv run pytest
"""

import json
import os
from datetime import date
from pathlib import Path

import pytest

from core.text import ThemeTagger
from projects.linkedin_jobs.transform import merge_items, parse_salary, to_row

ROOT = Path(__file__).resolve().parent.parent
ITEMS = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text())
TAGGER = ThemeTagger.from_yaml(ROOT / "projects/linkedin_jobs/themes.yaml")


def rows_for(items, term="data scientist"):
    merged = merge_items({term: items})
    return merged, [to_row(i, t, TAGGER) for i, t in merged.values()]


def test_salary_parsing():
    assert parse_salary(["$130,000.00/yr", "$160,000.00/yr"]) == (130000.0, 160000.0, "yr")
    assert parse_salary(["$45.00/hr", "$55.00/hr"]) == (45.0, 55.0, "hr")
    assert parse_salary(["$120K", "$150K"]) == (120000.0, 150000.0, "yr")
    assert parse_salary(None) == (None, None, None)


def test_transform_fields_and_privacy():
    merged, rows = rows_for(ITEMS)
    r = {x["job_id"]: x for x in rows}
    a = r["4100000001"]
    assert a["primary_industry"] == "Hospitals and Health Care"
    assert a["applicants_count"] == 87 and a["company_employees"] == 5400
    assert a["posted_at"] == date(2026, 9, 28)
    assert {"Machine learning modeling", "Experimentation & causal inference", "SQL & data pipelines",
            "Stakeholder communication", "Generative AI & LLMs"} <= set(a["themes"])
    assert r["4100000002"]["workplace_type"] == "Remote"
    assert r["4100000002"]["applicants_count"] == 200
    for item, _ in merged.values():
        assert not any(k.startswith("jobPoster") for k in item)


def test_repost_shares_content_hash():
    _, rows = rows_for(ITEMS)
    r = {x["job_id"]: x for x in rows}
    assert r["4100000002"]["content_hash"] == r["4100000003"]["content_hash"]
    assert r["4100000001"]["content_hash"] != r["4100000002"]["content_hash"]


def test_merge_across_searches():
    merged = merge_items({"data scientist": ITEMS[:1], "machine learning engineer": ITEMS[:2]})
    assert len(merged) == 2
    assert sorted(merged["4100000001"][1]) == ["data scientist", "machine learning engineer"]


DB = os.environ.get("TEST_DB_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_monthly_runs_dedupe():
    import psycopg

    from core import db, runlog
    from projects.linkedin_jobs import load

    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)

        # Month 1: jobs 1 and 2
        run1 = runlog.start_run(conn, "linkedin_jobs", {})
        merged, rows = rows_for(ITEMS[:2])
        load.insert_raw(conn, run1, merged)
        assert load.upsert_postings(conn, run1, rows, date(2026, 10, 1)) == 2
        conn.commit()
        runlog.finish_run(conn, run1, status="succeeded", rows_fetched=2, rows_new=2)

        # Month 2: job 2 again (from two searches) plus job 3 (a repost of job 2)
        run2 = runlog.start_run(conn, "linkedin_jobs", {})
        merged = merge_items({"data analyst": ITEMS[1:3], "data scientist": ITEMS[1:2]})
        rows = [to_row(i, t, TAGGER) for i, t in merged.values()]
        load.insert_raw(conn, run2, merged)
        assert load.upsert_postings(conn, run2, rows, date(2026, 11, 1)) == 1  # only job 3 is new
        conn.commit()

        j2 = conn.execute(
            "select first_seen_at, last_seen_at, times_seen, search_terms from jobs.postings where job_id='4100000002'"
        ).fetchone()
        assert j2 == (date(2026, 10, 1), date(2026, 11, 1), 2, ["data analyst", "data scientist"])

        assert conn.execute("select count(*) from jobs.postings").fetchone()[0] == 3
        dedup = conn.execute(
            "select count(*), max(repost_count) from jobs.postings_dedup"
        ).fetchone()
        assert dedup == (2, 2)  # job 3 collapses into job 2
        assert conn.execute("select count(*) from jobs.raw_postings").fetchone()[0] == 4
        assert conn.execute("select count(*) from jobs.posting_themes").fetchone()[0] > 0

        # Analysis views (Module 9) read the same data
        conn.execute("insert into jobs.my_skills (theme, my_level) values ('Dashboards & BI', 5)")
        gap = dict(conn.execute("select theme, priority from jobs.skill_gap").fetchall())
        assert gap["Dashboards & BI"] == 0  # you're an expert: no gap
        assert conn.execute("select sum(roles) from jobs.industry_mix").fetchone()[0] == 2

        # Re-running the same month's load is harmless
        assert load.upsert_postings(conn, run2, rows, date(2026, 11, 1)) == 0
        conn.commit()
        assert conn.execute("select times_seen from jobs.postings where job_id='4100000002'").fetchone()[0] == 2


class FakeRun:
    """Stands in for the object apify-client returns from .call()."""
    status = "SUCCEEDED"
    default_dataset_id = "fake-dataset"
    usage_total_usd = 0.01


class FakeApify:
    """A pretend Apify client: same methods the pipeline calls, no network."""
    def actor(self, actor_id):
        return self

    def call(self, run_input):
        self.last_input = run_input
        return FakeRun()

    def dataset(self, dataset_id):
        return self

    def iterate_items(self):
        return iter(ITEMS)


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_pipeline_end_to_end(monkeypatch):
    import psycopg

    from core import db
    from projects.linkedin_jobs import run, scrape

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    monkeypatch.setattr(scrape, "client", lambda: FakeApify())
    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)

    assert run.main(["--limit", "5", "--searches", "data scientist,data analyst"]) == 0

    with psycopg.connect(DB) as conn:
        status, fetched, new = conn.execute(
            "select status, rows_fetched, rows_new from core.run_log order by run_id desc limit 1"
        ).fetchone()
    assert (status, fetched, new) == ("succeeded", 3, 3)
