"""SQL behind the dashboard. Every function returns plain rows: a list of dicts."""

from datetime import date

import psycopg
from psycopg.rows import dict_row

# Distinct roles (reposts and multi-city postings collapsed) from any of the chosen
# searches that were visible at some point between the start and end months. Each
# query below starts from this, so the filters behave the same in every chart.
ROLES = """
    select p.*
    from jobs.postings_dedup p
    where p.search_terms && %(terms)s::text[]
      and date_trunc('month', p.role_first_seen_at) <= %(end)s
      and date_trunc('month', p.role_last_seen_at) >= %(start)s
"""


def _rows(conn: psycopg.Connection, sql: str, params: dict | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(sql, params).fetchall()


def filter_options(conn: psycopg.Connection) -> dict:
    """The search terms and months that exist, to fill the sidebar."""
    terms = _rows(conn, "select distinct unnest(search_terms) as term from jobs.postings order by term")
    months = _rows(conn, """
        select month from (
            select date_trunc('month', first_seen_at)::date as month from jobs.postings
            union
            select date_trunc('month', last_seen_at)::date from jobs.postings
        ) m
        order by month
    """)
    return {"terms": [r["term"] for r in terms], "months": [r["month"] for r in months]}


def dashboard(conn: psycopg.Connection, terms: list[str], start: date, end: date) -> dict:
    """Everything the dashboard shows, for one set of filters."""
    f = {"terms": terms, "start": start, "end": end}

    summary = _rows(conn, f"""
        with roles as ({ROLES})
        select count(*) as roles,
               count(distinct company_name) as companies,
               round(100.0 * count(salary_min) / nullif(count(*), 0))::float as pct_with_salary,
               percentile_cont(0.5) within group (order by (salary_min + coalesce(salary_max, salary_min)) / 2)
                   filter (where salary_period = 'yr') as median_salary
        from roles
    """, f)[0]

    themes = _rows(conn, f"""
        with roles as ({ROLES})
        select t.theme,
               count(*) as roles,
               round(100.0 * count(*) / (select count(*) from roles), 1)::float as pct
        from roles r
        join jobs.posting_themes t on t.job_id = r.job_id
        group by t.theme
        order by roles desc, t.theme
    """, f)

    industries = _rows(conn, f"""
        with roles as ({ROLES})
        select coalesce(primary_industry, 'Unknown') as industry, count(*) as roles
        from roles
        group by 1
        order by roles desc, industry
        limit 15
    """, f)

    seniority = _rows(conn, f"""
        with roles as ({ROLES})
        select coalesce(seniority_level, 'Unknown') as seniority, count(*) as roles
        from roles
        group by 1
        order by roles desc
    """, f)

    theme_by_industry = _rows(conn, f"""
        with roles as ({ROLES}),
        top as (
            select primary_industry, count(*) as n
            from roles
            where primary_industry is not null
            group by primary_industry
            order by n desc
            limit 8
        )
        select top.primary_industry as industry,
               t.theme,
               round(100.0 * count(*) / top.n, 1)::float as pct
        from roles r
        join top on top.primary_industry = r.primary_industry
        join jobs.posting_themes t on t.job_id = r.job_id
        group by top.primary_industry, top.n, t.theme
        order by industry, t.theme
    """, f)

    postings = _rows(conn, f"""
        with roles as ({ROLES})
        select r.title, r.company_name, r.primary_industry, r.seniority_level, r.location,
               r.location_count, r.workplace_type, r.salary_min, r.salary_max, r.salary_period,
               r.role_first_seen_at as first_seen, r.link,
               array(select t.theme from jobs.posting_themes t
                     where t.job_id = r.job_id order by t.theme) as themes
        from roles r
        order by r.role_first_seen_at desc, r.title
    """, f)

    return {
        "summary": summary,
        "themes": themes,
        "industries": industries,
        "seniority": seniority,
        "theme_by_industry": theme_by_industry,
        "postings": postings,
    }
