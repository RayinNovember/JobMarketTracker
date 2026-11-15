"""SQL behind the dashboard's skills section (Module 12). Same filters as queries.py."""

from datetime import date

import psycopg

from projects.linkedin_jobs.queries import ROLES, _rows


def has_skills(conn: psycopg.Connection) -> bool:
    """True once Module 12 is set up and at least one posting has been tagged."""
    if conn.execute("select to_regclass('jobs.role_skills')").fetchone()[0] is None:
        return False
    return conn.execute("select exists (select 1 from jobs.posting_skills)").fetchone()[0]


def skills_dashboard(conn: psycopg.Connection, terms: list[str], start: date, end: date,
                     min_mentions: int = 3) -> dict:
    f = {"terms": terms, "start": start, "end": end, "min": min_mentions}

    # Share of tagged roles asking for each skill, split into required and preferred.
    skills = _rows(conn, f"""
        with roles as ({ROLES} and p.other_skills is not null),
        total as (select count(*) as n from roles)
        select s.category, s.skill,
               count(rs.job_id) as roles,
               round(100.0 * count(rs.job_id) / nullif(total.n, 0), 1)::float as pct,
               round(100.0 * count(rs.job_id) filter (where rs.level = 'required')
                     / nullif(total.n, 0), 1)::float as pct_required
        from jobs.skills s
        cross join total
        left join jobs.role_skills rs
               on rs.skill = s.skill and rs.job_id in (select job_id from roles)
        group by s.category, s.skill, total.n
        order by s.category, roles desc, s.skill
    """, f)

    # Skills found outside the list, most frequent first: candidates for skills.yaml.
    emerging = _rows(conn, f"""
        with roles as ({ROLES})
        select o.phrase, count(*) as roles
        from roles r
        cross join lateral unnest(r.other_skills) as o(phrase)
        group by o.phrase
        having count(*) >= %(min)s
        order by roles desc, o.phrase
        limit 25
    """, f)

    tagged = _rows(conn, f"with roles as ({ROLES}) select count(*) filter (where other_skills is not null) as n "
                         "from roles", f)[0]["n"]
    return {"skills": skills, "emerging": emerging, "tagged_roles": tagged}
