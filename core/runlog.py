"""Run log: one row in core.run_log per pipeline run, across all projects."""

import json

import psycopg

def start_run(conn: psycopg.Connection, project: str, params: dict) -> int:
    run_id = conn.execute(
        "insert into core.run_log (project, params) values (%s, %s) returning run_id",
        (project, json.dumps(params)),
    ).fetchone()[0]
    conn.commit()
    return run_id


def finish_run(
    conn: psycopg.Connection,
    run_id: int,
    *,
    status: str,
    rows_fetched: int | None = None,
    rows_new: int | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
) -> None:
    conn.rollback()  # clear any failed transaction before logging the outcome
    conn.execute(
        """
        update core.run_log
           set finished_at = now(), status = %s, rows_fetched = %s,
               rows_new = %s, cost_usd = %s, error = %s
         where run_id = %s
        """,
        (status, rows_fetched, rows_new, cost_usd, (error or None) and error[:4000], run_id),
    )
    conn.commit()
    



