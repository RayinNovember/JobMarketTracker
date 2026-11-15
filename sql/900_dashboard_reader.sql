-- Read-only access for the dashboard (Module 11). Named 900 so it runs after every other file.
-- You create the dashboard_reader role once, by hand, in the Supabase SQL Editor,
-- because its password must never be in git. This file only grants it read access,
-- and runs on every migration because the views are dropped and rebuilt each time
-- (a rebuilt view starts with no grants). Without the role, it does nothing.
do $$
begin
    if exists (select from pg_roles where rolname = 'dashboard_reader') then
        grant usage on schema jobs to dashboard_reader;
        grant select on all tables in schema jobs to dashboard_reader;
    end if;
end
$$;
