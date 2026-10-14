# Kyle's 3rd Leg

The league website. `index.html` is the site, and `scripts/update.py` pulls the current season from ESPN every morning through GitHub Actions: standings, scores, recaps, rosters and transactions. Recaps already written are reused, so the daily runs only call Claude for games that just finished or had a stat correction.

## Files
- `index.html`: the site, including all 2021–2025 history.
- `managers.json`: each manager's name, full name, nickname, photo, bio and active/former status. Edit this instead of `index.html` to change a profile. Check commas and quotes after editing; a typo here stops the site from loading and says so on the page.
- `images/managers/`: manager photos, named by manager ID (`josh.jpg`). Square, 600 × 600 JPG. Anyone without one gets an initials placeholder.
- `league.json`: ESPN league ID, the season to pull, and optional team-to-manager fixes.
- `scripts/update.py`: the ESPN update script.
- `requirements.txt`: what the script needs installed.
- `setup/update.yml`: the daily schedule. Its contents go in `.github/workflows/update.yml` (see setup).
- `supabase/forum.sql`: the forum's database setup, run once in the Supabase SQL Editor.

## Forum
Posts are stored in Supabase (project `uppbazlahrfbjjxpfuzl`). The publishable key in `FORUM` near the bottom of `index.html` is safe to be public. Never put the service role key or the passcode in this repo.
- **Change the passcode:** in the Supabase SQL Editor, run the query below with the new passcode, then delete that query from the editor's snippet list.
  ```sql
  insert into private.forum_secret (id, passcode_hash)
  values (true, extensions.crypt('NEW PASSCODE HERE', extensions.gen_salt('bf', 10)))
  on conflict (id) do update set passcode_hash = excluded.passcode_hash;
  ```
- **Delete a post:** Table Editor > `forum_posts` > tick the row > Delete. Deleting a thread also deletes its replies.
- **Manager changes:** edit the name list in `forum_post` in `supabase/forum.sql` and run the whole file again. The list uses the lowercase IDs from `index.html`.
- **Free plan pause:** Supabase pauses free projects after a week with no activity. If the forum says it can't load, open the project in the dashboard and choose Restore.

## Secrets (Settings > Secrets and variables > Actions)
- `ESPN_S2` and `ESPN_SWID`: required, because the league is private.
- `ANTHROPIC_API_KEY`: optional. With it, Claude writes the weekly recaps. Without it, the script writes shorter recaps itself.

## Things to know
- **Running it by hand:** Actions tab > Daily ESPN update > Run workflow.
- **If the update fails** with an ESPN error, the cookies have probably expired. Copy fresh `espn_s2` and `SWID` values into the secrets.
- **If a team shows an ESPN name instead of a manager**, the script couldn't match the owner's name. The workflow log shows the ESPN team number. Add it to `managers` in `league.json`, for example `"managers": {"7": "cody"}`.
- **New season:** change `season` in `league.json` (for example to 2027). Finished seasons are added to the all-time history automatically.
- **Offseason:** GitHub pauses scheduled workflows after 60 days with no repository activity. If that happens, re-enable it from the Actions tab.
