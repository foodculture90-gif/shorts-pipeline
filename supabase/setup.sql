-- =============================================================================
-- Mission Control — database setup (Supabase free plan).
-- Supabase → SQL Editor → New query → paste this file → fill in YOUR SETTINGS → Run.
-- Safe to run again.
-- =============================================================================

-- ---- YOUR SETTINGS ----------------------------------------------------------
do $$ begin
  perform set_config('mc.owner_email',  'YOUR_EMAIL@gmail.com', false);
  perform set_config('mc.github_repo',  'YOUR_GITHUB_USERNAME/shorts-pipeline', false);
  perform set_config('mc.github_token', 'github_pat_PASTE_HERE', false);
end $$;
-- -----------------------------------------------------------------------------

create extension if not exists pg_net;

create schema if not exists private;
create table if not exists private.config (key text primary key, value text not null);
insert into private.config values
  ('owner_email',  current_setting('mc.owner_email')),
  ('github_repo',  current_setting('mc.github_repo')),
  ('github_token', current_setting('mc.github_token'))
on conflict (key) do update set value = excluded.value;
revoke all on schema private from anon, authenticated;

create or replace function public.is_owner() returns boolean
language sql stable security definer set search_path = public, private as $$
  select coalesce(auth.jwt() ->> 'email', '') =
         (select value from private.config where key = 'owner_email')
$$;

-- ---- Tables -----------------------------------------------------------------
create table if not exists public.projects (
  id text primary key, name text not null, status text not null default 'active',
  description text, sort int default 0);

create table if not exists public.channels (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  niche text not null default 'kids'' stories for ages 3-7',
  voice text not null default 'en-US-AnaNeural',
  per_day int not null default 10,             -- shorts made automatically each day
  auto_daily boolean not null default true,
  made_for_kids boolean not null default true,
  youtube_channel_id text, youtube_title text, connected boolean not null default false,
  created_at timestamptz not null default now());

-- YouTube permissions. RLS on with NO policies = only the cloud worker can read it.
create table if not exists public.channel_tokens (
  channel_id uuid primary key references public.channels(id) on delete cascade,
  refresh_token text not null, updated_at timestamptz default now());

create table if not exists public.episodes (
  id uuid primary key default gen_random_uuid(),
  channel_id uuid references public.channels(id) on delete set null,
  parent_id uuid,
  status text not null default 'queued',
     -- queued | generating | awaiting_approval | publishing | scheduled | published | failed | replaced | deleted
  title text, takeaway text, style text, story jsonb, idea text, feedback text,
  preview_path text, thumb_path text, assets_path text, duration real,
  error text, youtube_id text, youtube_url text, publish_at timestamptz,
  views int, likes int, stats_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now());

create table if not exists public.commands (
  id bigint generated always as identity primary key,
  type text not null,             -- generate | revise | publish | delete | stats | connect_channel
  payload jsonb not null default '{}',
  status text not null default 'queued',   -- queued | running | done | failed
  run_after timestamptz not null default now(),
  note text, error text,
  created_at timestamptz not null default now(), finished_at timestamptz);

create table if not exists public.usage (
  day date primary key, images int not null default 0, shorts int not null default 0);

create table if not exists public.tasks (
  id bigint generated always as identity primary key,
  project_id text not null references public.projects(id),
  title text not null, notes text, status text not null default 'todo', sort int default 0,
  created_at timestamptz not null default now());

create table if not exists public.settings (key text primary key, value jsonb not null);

create table if not exists public.activity (
  id bigint generated always as identity primary key,
  project_id text, kind text not null default 'info', message text not null,
  created_at timestamptz not null default now());

-- ---- Security: owner-only --------------------------------------------------------
do $$ declare t text; begin
  foreach t in array array['projects','channels','episodes','commands','usage','tasks','settings','activity'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists owner_all on public.%I', t);
    execute format('create policy owner_all on public.%I for all to authenticated using (public.is_owner()) with check (public.is_owner())', t);
  end loop;
end $$;
alter table public.channel_tokens enable row level security;  -- deliberately no policies

insert into storage.buckets (id, name, public) values ('media', 'media', false) on conflict (id) do nothing;
drop policy if exists media_owner on storage.objects;
create policy media_owner on storage.objects for all to authenticated
  using (bucket_id = 'media' and public.is_owner()) with check (bucket_id = 'media' and public.is_owner());

-- ---- Any new command wakes the cloud worker instantly -------------------------------
create or replace function private.wake_worker() returns trigger
language plpgsql security definer set search_path = public, private as $$
begin
  perform net.http_post(
    url := 'https://api.github.com/repos/' || (select value from private.config where key = 'github_repo') || '/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || (select value from private.config where key = 'github_token'),
      'Accept', 'application/vnd.github+json', 'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'mission-control', 'Content-Type', 'application/json'),
    body := jsonb_build_object('event_type', 'command'));
  return null;
end $$;
drop trigger if exists wake_worker on public.commands;
create trigger wake_worker after insert on public.commands
  for each statement execute function private.wake_worker();

-- ---- Live updates ---------------------------------------------------------------
do $$ begin
  begin alter publication supabase_realtime add table public.episodes; exception when others then null; end;
  begin alter publication supabase_realtime add table public.activity; exception when others then null; end;
  begin alter publication supabase_realtime add table public.tasks;    exception when others then null; end;
  begin alter publication supabase_realtime add table public.channels; exception when others then null; end;
end $$;

-- ---- Starting data ----------------------------------------------------------------
insert into public.projects (id, name, status, description, sort) values
  ('shorts',  'YouTube Shorts', 'active', 'Free AI story Shorts, new characters every time, up to ~20 a day', 1),
  ('fitness', 'AI Fitness App', 'planning', 'iOS + Apple Watch app: AI calories, physique, workouts', 2)
on conflict (id) do nothing;

insert into public.channels (name, niche, per_day)
select * from (values
  ('Story Time', 'magical illustrated stories for kids aged 3-7: animals, adventures, gentle lessons', 10),
  ('Wonder Facts', 'fun true facts for curious kids aged 5-9, told as tiny stories (animals, space, oceans, nature)', 10)
) v(name, niche, per_day)
where not exists (select 1 from public.channels);

insert into public.settings (key, value) values ('music_volume', '0.12') on conflict (key) do nothing;

insert into public.tasks (project_id, title, status, sort)
select * from (values
  ('shorts', 'Accounts: Google, GitHub, Supabase, Cloudflare, Gemini key', 'doing', 1),
  ('shorts', 'Connect YouTube channels in the app', 'todo', 2),
  ('shorts', 'Phone-verify each YouTube channel (more uploads/day)', 'todo', 3),
  ('shorts', 'Submit YouTube API audit (auto-public uploads)', 'todo', 4),
  ('shorts', 'Add royalty-free music to the repo', 'todo', 5),
  ('shorts', 'Reach YouTube Partner Program (1,000 subs + 10M Shorts views / 90 days)', 'todo', 6),
  ('fitness', 'Get a Mac + Apple Developer account', 'todo', 1),
  ('fitness', 'Design screens: food scan, daily progress, physique, Watch', 'todo', 2),
  ('fitness', 'AI calorie counting from food photos', 'todo', 3),
  ('fitness', 'AI physique evaluation + progress photos', 'todo', 4),
  ('fitness', 'Apple Watch + HealthKit workout tracking', 'todo', 5),
  ('fitness', 'TestFlight beta, then App Store', 'todo', 6)
) v(project_id, title, status, sort)
where not exists (select 1 from public.tasks);

-- ---- Free picture allowance: reserve atomically so parallel workers never overshoot ----
create or replace function public.reserve_images(n int, cap int) returns boolean
language plpgsql security definer set search_path = public as $$
declare ok boolean;
begin
  insert into public.usage (day, images) values (current_date, 0) on conflict (day) do nothing;
  update public.usage set images = images + n where day = current_date and images + n <= cap
  returning true into ok;
  return coalesce(ok, false);
end $$;
revoke execute on function public.reserve_images(int, int) from anon, authenticated;
