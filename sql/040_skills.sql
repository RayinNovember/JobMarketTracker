-- Module 12: skills by category. (The other_skills column on jobs.postings is added in
-- 010_linkedin_jobs.sql, before the views that select p.*, so the views include it.)

-- The skill list, copied from skills.yaml on every tagging run. Each skill's category lives here, once.
create table if not exists jobs.skills (
    skill      text primary key,
    category   text not null check (category in ('technical', 'communication', 'business', 'leadership')),
    definition text
);

-- One row per posting per skill it asks for.
create table if not exists jobs.posting_skills (
    job_id text not null references jobs.postings (job_id),
    skill  text not null references jobs.skills (skill),
    level  text not null check (level in ('required', 'preferred')),
    primary key (job_id, skill)
);

create index if not exists posting_skills_skill_idx on jobs.posting_skills (skill);

-- Skills per role (reposts collapsed), with the category attached. 010 drops this view
-- (cascade) whenever it rebuilds postings_dedup, so it is recreated here every time.
create or replace view jobs.role_skills as
select p.job_id, p.primary_industry, p.seniority_level, s.category, ps.skill, ps.level
from jobs.postings_dedup p
join jobs.posting_skills ps on ps.job_id = p.job_id
join jobs.skills s on s.skill = ps.skill;
