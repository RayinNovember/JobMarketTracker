-- LinkedIn job postings project.
-- Safe to re-run: everything is "if not exists" / "create or replace".

create schema if not exists jobs;

-- Raw landing table: exactly what the scraper returned (minus personal fields),
-- one row per job per run. Lets you rebuild the clean table without re-scraping.
create table if not exists jobs.raw_postings (
    run_id      bigint      not null references core.run_log (run_id),
    job_id      text        not null,
    scraped_at  timestamptz not null default now(),
    search_terms text[]     not null,
    payload     jsonb       not null,
    primary key (run_id, job_id)
);

-- Clean table: one row per LinkedIn job ID, ever.
create table if not exists jobs.postings (
    job_id            text primary key,
    title             text,
    company_name      text,
    company_url       text,
    company_employees integer,
    location          text,
    industries        text,
    primary_industry  text,
    seniority_level   text,
    employment_type   text,
    job_function      text,
    workplace_type    text,
    salary_min        numeric,
    salary_max        numeric,
    salary_period     text,          -- yr | hr | mo | wk
    posted_at         date,
    applicants_count  integer,
    link              text,
    description_text  text,
    content_hash      text,          -- same role reposted under a new job ID shares this
    job_hash          text,          -- same as content_hash but ignores location: groups multi-city postings
    themes          text[] not null default '{}',
    search_terms      text[] not null default '{}',
    first_seen_at     date    not null,
    last_seen_at      date    not null,
    times_seen        integer not null default 1,
    first_run_id      bigint references core.run_log (run_id),
    last_run_id       bigint references core.run_log (run_id)
);

-- Added after the table was first created; a no-op on fresh databases.
-- Backfill existing rows with: uv run python -m projects.linkedin_jobs.run --rehash
alter table jobs.postings add column if not exists job_hash text;

create index if not exists postings_first_seen_idx on jobs.postings (first_seen_at);
create index if not exists postings_content_hash_idx on jobs.postings (content_hash);
create index if not exists postings_job_hash_idx on jobs.postings (job_hash);
create index if not exists postings_industry_idx on jobs.postings (primary_industry);

-- Views are rebuilt on every migration: p.* is fixed when a view is created, so adding
-- a column to postings would make "create or replace" fail. cascade also drops the views
-- built on this one (here and in 020_analysis.sql); the statements after recreate them.
drop view if exists jobs.postings_dedup cascade;

-- One row per distinct role: collapses reposts (same role, new job ID) and multi-city
-- postings (same role, one job ID per location) to the earliest-seen posting, and spans
-- the full window the role was visible. Rows not yet backfilled fall back to content_hash.
create view jobs.postings_dedup as
with keyed as (
    select p.*, coalesce(p.job_hash, p.content_hash, p.job_id) as role_key
    from jobs.postings p
),
roles as (
    select role_key,
           min(first_seen_at) as role_first_seen_at,
           max(last_seen_at)  as role_last_seen_at,
           count(*)           as repost_count,     -- every job ID collapsed into this role
           array_agg(distinct location order by location) filter (where location is not null) as locations
    from keyed
    group by role_key
)
select distinct on (k.role_key)
       k.*,
       r.role_first_seen_at,
       r.role_last_seen_at,
       r.repost_count,
       coalesce(r.locations, '{}')                  as locations,
       coalesce(cardinality(r.locations), 0)        as location_count
from keyed k
join roles r using (role_key)
order by k.role_key, k.first_seen_at, k.job_id;

-- Theme coverage: one row per posting x theme, handy for BI tools.
create or replace view jobs.posting_themes as
select p.job_id, p.primary_industry, p.seniority_level, p.first_seen_at, t.theme
from jobs.postings_dedup p
cross join lateral unnest(p.themes) as t(theme);
