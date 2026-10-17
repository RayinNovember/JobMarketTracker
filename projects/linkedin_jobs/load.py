"""Write raw items and clean rows to Supabase, deduplicating on LinkedIn job ID."""

from datetime import date

import psycopg
from psycopg.types.json import Jsonb

COLUMNS = [
    "job_id", "title", "company_name", "company_url", "company_employees", "location",
    "industries", "primary_industry", "seniority_level", "employment_type", "job_function",
    "workplace_type", "salary_min", "salary_max", "salary_period", "posted_at",
    "applicants_count", "link", "description_text", "content_hash", "themes", "search_terms",
]

# Fields refreshed from the latest scrape when a job is seen again.
REFRESH = [c for c in COLUMNS if c not in ("job_id", "search_terms")]

def insert_raw(conn: psycopg.Connection, run_id:int, merged: dict[str, tuple[dict, list[str]]]) -> None:
    """Insert raw items into the database, one row per job ID."""
    with conn.cursor() as cur:
        cur.executemany(
            "insert into jobs.raw_postings (run_id, job_id, search_terms, payload) values (%s, %s, %s, %s)"
            " on conflict (run_id, job_id) do nothing",
            [(run_id, jid, sorted(set(terms)), Jsonb(item)) for jid, (item, terms) in merged.items()],
        )


def upsert_postings(conn: psycopg.Connection, run_id: int, rows: list[dict], seen_on: date) -> int:
    """Insert new jobs; for known jobs update last_seen_at/times_seen. Returns # of new jobs."""
    if not rows:
        return 0
    cols = ", ".join(COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in COLUMNS)
    refresh = ",\n        ".join(f"{c} = coalesce(excluded.{c}, p.{c})" for c in REFRESH)
    with conn.cursor() as cur:
        # create a temporary table to stage the new rows, then upsert into the main table
        cur.execute(
            "create temp table stage (like jobs.postings including defaults) on commit drop"
        )
        cur.executemany(f"insert into stage ({cols}, first_seen_at, last_seen_at) values ({placeholders}, current_date, current_date)", rows)
        # upsert into the main table, updating last_seen_at and times_seen for known jobs
        cur.execute(
            f"""
            insert into jobs.postings as p
                ({cols}, first_seen_at, last_seen_at, times_seen, first_run_id, last_run_id)
            select {cols}, %(seen)s, %(seen)s, 1, %(run)s, %(run)s from stage
            on conflict (job_id) do update set
                {refresh},
                search_terms = (select array_agg(distinct t order by t)
                                  from unnest(p.search_terms || excluded.search_terms) as t),
                last_seen_at = greatest(p.last_seen_at, excluded.last_seen_at),
                times_seen   = p.times_seen + case when p.last_run_id = excluded.last_run_id then 0 else 1 end,
                last_run_id  = excluded.last_run_id
            returning (xmax = 0) as inserted
            """,
            {"seen": seen_on, "run": run_id},
        )
        new = sum(1 for (inserted,) in cur.fetchall() if inserted)
    return new


def retag_all(conn: psycopg.Connection, tagger) -> int:
    """Re-apply themes.yaml to every stored description (after editing themes)."""
    rows = conn.execute("select job_id, title, description_text from jobs.postings").fetchall()
    with conn.cursor() as cur:
        cur.executemany(
            "update jobs.postings set themes = %s where job_id = %s",
            [(tagger.tag(f"{t or ''}\n{d or ''}"), jid) for jid, t, d in rows],
        )
    conn.commit()
    return len(rows)


