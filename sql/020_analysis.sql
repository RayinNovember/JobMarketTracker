-- Analysis layer: views the dashboard and your own queries read from.
-- "Recent" means the role was still visible within the last 90 days.

-- Your own rating of each theme: 0 = none, 5 = expert. Fill it in yourself.
create table if not exists jobs.my_skills (
    theme    text primary key,
    my_level smallint check (my_level between 0 and 5),
    notes    text
);

-- New roles per month (reposts counted once).
create or replace view jobs.monthly_summary as
select date_trunc('month', role_first_seen_at)::date as month,
       count(*)                                        as new_roles,
       count(distinct company_name)                    as companies,
       round(avg(case when workplace_type ilike '%remote%' then 1.0 else 0 end), 3) as remote_share
from jobs.postings_dedup
group by 1
order by 1;

-- Which industries are hiring, recent roles only.
create or replace view jobs.industry_mix as
select coalesce(primary_industry, '(unknown)') as industry,
       count(*)                                as roles,
       round(count(*)::numeric / sum(count(*)) over (), 3) as share
from jobs.postings_dedup
where role_last_seen_at >= current_date - 90
group by 1
order by roles desc;

-- How often each theme appears in recent job descriptions.
create or replace view jobs.theme_coverage as
with recent as (
    select * from jobs.postings_dedup where role_last_seen_at >= current_date - 90
)
select t.theme,
       count(*)                                                   as roles,
       round(count(*)::numeric / (select count(*) from recent), 3) as share
from recent
cross join lateral unnest(recent.themes) as t(theme)
group by t.theme
order by roles desc;

-- The gap: themes the market asks for most, weighted by how far you are from expert.
create or replace view jobs.skill_gap as
select c.theme,
       c.share                                         as market_share,
       s.my_level,
       round(c.share * (5 - coalesce(s.my_level, 0)), 3) as priority
from jobs.theme_coverage c
left join jobs.my_skills s using (theme)
order by priority desc;
