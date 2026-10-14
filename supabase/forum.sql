-- Forum for Kyle's 3rd Leg.
-- Run this whole file once in Supabase: SQL Editor > New query > paste > Run.
-- It's safe to run again later (for example after changing the manager list).
-- There are no secrets in this file. The passcode is set separately (see README).

create extension if not exists pgcrypto with schema extensions;

-- Posts. A thread is a post with no parent_id; replies point at their thread.
create table if not exists public.forum_posts (
  id bigint generated always as identity primary key,
  parent_id bigint references public.forum_posts (id) on delete cascade,
  author text not null,
  body text not null check (char_length(body) between 1 and 1000 and body ~ '\S'),
  created_at timestamptz not null default now(),
  last_activity timestamptz not null default now()
);
create index if not exists forum_posts_parent_idx on public.forum_posts (parent_id);
create index if not exists forum_posts_threads_idx on public.forum_posts (last_activity desc) where parent_id is null;

-- Anyone can read. Nobody can write directly; posting only goes through forum_post() below.
alter table public.forum_posts enable row level security;
drop policy if exists "Anyone can read posts" on public.forum_posts;
create policy "Anyone can read posts" on public.forum_posts for select to anon, authenticated using (true);
revoke all on public.forum_posts from anon, authenticated;
grant select on public.forum_posts to anon, authenticated;

-- The passcode hash lives in a schema the website API can't see at all.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create table if not exists private.forum_secret (
  id boolean primary key default true check (id),
  passcode_hash text not null
);
alter table private.forum_secret enable row level security;
revoke all on private.forum_secret from public, anon, authenticated;

-- Posting: checks the name, the length and the passcode, then saves the post.
create or replace function public.forum_post(p_author text, p_body text, p_passcode text, p_parent_id bigint default null)
returns public.forum_posts
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_body text := btrim(coalesce(p_body, ''), E' \t\r\n');
  v_hash text;
  v_parent public.forum_posts;
  v_row public.forum_posts;
begin
  if p_author is null or p_author not in ('josh','brett','kyle','brandon','keith','brad','reis','noah','tyler','cody') then
    raise exception 'Pick your name from the list.';
  end if;
  if v_body = '' then
    raise exception 'Posts can''t be empty.';
  end if;
  if char_length(v_body) > 1000 then
    raise exception 'Posts are limited to 1000 characters.';
  end if;

  select passcode_hash into v_hash from private.forum_secret limit 1;
  if v_hash is null then
    raise exception 'The forum passcode hasn''t been set up yet.';
  end if;
  if p_passcode is null or extensions.crypt(p_passcode, v_hash) <> v_hash then
    raise exception 'Wrong passcode.';
  end if;

  if p_parent_id is not null then
    select * into v_parent from public.forum_posts where id = p_parent_id;
    if not found then
      raise exception 'That thread was deleted.';
    end if;
    if v_parent.parent_id is not null then
      raise exception 'Replies go on the thread, not on another reply.';
    end if;
    update public.forum_posts set last_activity = now() where id = p_parent_id;
  end if;

  insert into public.forum_posts (parent_id, author, body)
  values (p_parent_id, p_author, v_body)
  returning * into v_row;
  return v_row;
end;
$$;

revoke all on function public.forum_post(text, text, text, bigint) from public;
grant execute on function public.forum_post(text, text, text, bigint) to anon, authenticated;
