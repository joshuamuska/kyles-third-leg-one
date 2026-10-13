# Kyle's 3rd Leg

The league website. `index.html` is the site, and `scripts/update.py` pulls the current season from ESPN every Tuesday and Wednesday through GitHub Actions.

## Files
- `index.html`: the site, including all 2021–2025 history.
- `league.json`: ESPN league ID, the season to pull, and optional team-to-manager fixes.
- `scripts/update.py`: the ESPN update script.
- `requirements.txt`: what the script needs installed.
- `setup/update.yml`: the weekly schedule. Its contents go in `.github/workflows/update.yml` (see setup).

## Secrets (Settings > Secrets and variables > Actions)
- `ESPN_S2` and `ESPN_SWID`: required, because the league is private.
- `ANTHROPIC_API_KEY`: optional. With it, Claude writes the weekly recaps. Without it, the script writes shorter recaps itself.

## Things to know
- **Running it by hand:** Actions tab > Weekly ESPN update > Run workflow.
- **If the update fails** with an ESPN error, the cookies have probably expired. Copy fresh `espn_s2` and `SWID` values into the secrets.
- **If a team shows an ESPN name instead of a manager**, the script couldn't match the owner's name. The workflow log shows the ESPN team number. Add it to `managers` in `league.json`, for example `"managers": {"7": "cody"}`.
- **New season:** change `season` in `league.json` (for example to 2027). Finished seasons are added to the all-time history automatically.
- **Offseason:** GitHub pauses scheduled workflows after 60 days with no repository activity. If that happens, re-enable it from the Actions tab.
