-- Shared tables used by every scraping project.
-- Safe to re-run: everything is "if not exists".

CREATE schema if not exists core;

-- One row per pipeline run, across all projects.
create table if not exists core.run_log (
    run_id       bigserial primary key,
    project      text        not null,
    started_at   timestamptz not null default now(),
    finished_at  timestamptz,
    status       text        not null default 'running',  -- running | succeeded | failed
    params       jsonb,
    rows_fetched integer,
    rows_new     integer,
    cost_usd     numeric(10, 4),
    error        text
);

create index if not exists run_log_project_started_idx
    on core.run_log (project, started_at desc);
