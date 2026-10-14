# Kyle's 3rd Leg

The league website. `index.html` is the site, and `scripts/update.py` pulls the current season from ESPN every morning through GitHub Actions: standings, scores, recaps, rosters and transactions. Recaps already written are reused, so the daily runs only call Claude for games that just finished or had a stat correction.

## Files
- `index.html`: the site, including all 2021–2025 history.
- `managers.json`: each manager's name, full name, nickname, photo, bio and active/former status. Edit this instead of `index.html` to change a profile. Check commas and quotes after editing; a typo here stops the site from loading and says so on the page.
- `images/managers/`: manager photos, named by manager ID (`josh.jpg`). Square, 600 × 600 JPG. Anyone without one gets an initials placeholder.
- `league.json`: ESPN league ID, the season to pull, and optional team-to-manager fixes.
- `data/articles/<season>.json`: each finished week's power rankings and Claude's roundup article, with a one-line roast per team. Written once per week by the update and never redone, so reruns don't spend API credits. To have a week rewritten, delete its entry from this file (deleting its `headline` keeps the rankings and rewrites only the article). Without `ANTHROPIC_API_KEY`, rankings still appear and the article waits for a run that has the key.
- Power rankings: 40% all-play record (each week's score against every other team's), 35% points per week, 25% average over the last three weeks.
- `ledger/`: the editable parts of the Ledger menu (Versus, Rivalries, Trophies, Records). Each file has a `_help` line explaining its fields. Same comma-and-quote rule as `managers.json`; a file with a typo is skipped and the page says so.
  - `trophies.json`: which place earns which trophy, plus each trophy's name and one-liner. `place` is a number, `"last"`, or `"consolation"` (best finisher who missed the playoffs); `historicPlace` overrides it for 2021–2025. `hardware: true` counts toward the Most trophies record.
  - `rivalries.json`: named rivalries (two manager IDs and a description), shown as featured cards.
  - `money.json`: optional buy-ins and payouts per season. Leave `seasons` empty to hide the money records.
- Head-to-head, points and streak stats start with the 2026 ESPN season, since 2021–2025 only kept final standings.
- Manager pages (open from the Managers page, or the arrow next to Managers in the nav): a hero with titles, career numbers, the current season (it moves to the new season by itself), a trophy shelf from `ledger/trophies.json`, weekly accolades, and a season history whose rows open to show how each roster started and ended. The update saves what these need in `data/<season>.json`:
  - `weeks[].awards`: each finished week's awards by ESPN team id: `high`/`low` score, `blowout`/`close` (winner of the biggest and smallest margin), `lucky` (won while scoring below the league median), `unlucky` (lost while scoring above it), `over`/`under` (furthest above and below the starters' projection), `best`/`worst` (highest and lowest share of the best lineup the team could have started from its roster). Ties share an award.
  - `draftRosters`: each team's roster straight out of the draft, with round and pick (starters filled in draft order). Saved once the draft is complete and never redone.
  - `finalRosters`: the current roster with how each player got there (`draft`, `waiver`, `fa`, `trade`). It stops changing when the season ends, so it becomes the final-week roster.
- Player headshots and D/ST team logos load straight from ESPN using each player's ESPN id (nothing is stored here). A neutral silhouette shows when ESPN has no image.
- Brackets (in the Ledger): before the playoffs, the playoff picture from the current seeds; once they start, the playoff and consolation brackets fill in from ESPN's games. 2021–2025 show final places only.
- Draft Recap (in the Ledger): a draft board (one column per team in first-round order, colored with each manager's `color` from `managers.json`; one row per round, with ESPN headshots), then steals and busts (draft spot at his position vs. his points rank there now), and a letter grade per team from its drafted players' total points. Claude writes a one-line roast per team, saved in `data/<season>.json` and rewritten at most once per NFL week. Without `ANTHROPIC_API_KEY` the grades still show, just without roasts. A season picker appears once more than one season has a draft; the 2021–2025 drafts weren't saved.
- `rules.json`: the house rules (buy-in, payouts, last-place punishment, anything else) shown at the top of the Rules page, above the league settings the update pulls from ESPN. Anything still starting with "Fill in" shows as a placeholder. Same comma-and-quote rule as `managers.json`.
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
