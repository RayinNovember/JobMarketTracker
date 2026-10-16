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
    themes            text[] not null default '{}',
    search_terms      text[] not null default '{}',
    first_seen_at     date    not null,
    last_seen_at      date    not null,
    times_seen        integer not null default 1,
    first_run_id      bigint references core.run_log (run_id),
    last_run_id       bigint references core.run_log (run_id)
);

create index if not exists postings_first_seen_idx on jobs.postings (first_seen_at);
create index if not exists postings_content_hash_idx on jobs.postings (content_hash);
create index if not exists postings_industry_idx on jobs.postings (primary_industry);

-- One row per distinct role: collapses reposts (same content_hash, new job ID)
-- to the earliest-seen posting, and spans the full window the role was visible.
create or replace view jobs.postings_dedup as
select distinct on (p.content_hash)
       p.*,
       min(p.first_seen_at) over (partition by p.content_hash) as role_first_seen_at,
       max(p.last_seen_at)  over (partition by p.content_hash) as role_last_seen_at,
       count(*)             over (partition by p.content_hash) as repost_count
from jobs.postings p
order by p.content_hash, p.first_seen_at, p.job_id;

-- Theme coverage: one row per posting x theme, handy for BI tools.
create or replace view jobs.posting_themes as
select p.job_id, p.primary_industry, p.seniority_level, p.first_seen_at, t.theme
from jobs.postings_dedup p
cross join lateral unnest(p.themes) as t(theme);
