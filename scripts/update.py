#!/usr/bin/env python3
"""Pulls the current season from ESPN and saves it to data/<season>.json for the site.

Runs on GitHub Actions every week. Needs two secrets for a private league:
ESPN_S2 and ESPN_SWID. ANTHROPIC_API_KEY is optional: with it, recaps are
written by Claude; without it, the script writes its own short recaps.
"""
import datetime
import hashlib
import json
import os
import pathlib
import sys

import requests
from espn_api.football import League

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "league.json").read_text())

# Manager id -> (first name, last name if known). Used to match ESPN owners.
MANAGERS = {
    "josh": ("Josh", None),
    "brett": ("Brett", None),
    "kyle": ("Kyle", None),
    "brandon": ("Brandon", "Chojnacki"),
    "keith": ("Keith", "Sheridan"),
    "brad": ("Brad", "Trott"),
    "reis": ("Reis", "Bailey"),
    "noah": ("Noah", "Florias"),
    "tyler": ("Tyler", "Call"),
    "cody": ("Cody", "Jackson"),
}
BENCH_SLOTS = {"BE", "IR"}


def match_manager(team):
    override = CFG.get("managers", {}).get(str(team.team_id))
    if override:
        return override
    for owner in team.owners or []:
        first = (owner.get("firstName") or "").strip().lower()
        last = (owner.get("lastName") or "").strip().lower()
        for mid, (f, l) in MANAGERS.items():
            if first == f.lower() or (l and last == l.lower()):
                return mid
    return None


def owner_name(team):
    for owner in team.owners or []:
        name = " ".join(x for x in (owner.get("firstName"), owner.get("lastName")) if x)
        return name or owner.get("displayName") or ""
    return ""


def pick(key, options):
    """Stable choice so a recap doesn't change wording every run."""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return options[h % len(options)]


def who(side):
    mid = side.get("manager")
    return MANAGERS[mid][0] if mid in MANAGERS else (side.get("name") or "Someone")


def pts(x):
    return f"{x:.2f}"


def best_bench_swap(side):
    """Biggest gain from swapping a bench player in for a starter at the same position."""
    best = None
    for b in side["bench"]:
        for s in side["starters"]:
            if b["pos"] == s["pos"] and b["pts"] > s["pts"]:
                gain = b["pts"] - s["pts"]
                if not best or gain > best[0]:
                    best = (gain, b, s)
    return best


def auto_recap(m, week_hi, week_lo):
    h, a = m["home"], m["away"]
    if h["score"] == a["score"]:
        return f"{who(h)} and {who(a)} tied at {pts(h['score'])}. Nobody's happy."
    W, L = (h, a) if h["score"] > a["score"] else (a, h)
    margin = W["score"] - L["score"]
    ws, ls, k = pts(W["score"]), pts(L["score"]), m["key"]
    w, l = who(W), who(L)

    if margin < 2:
        lead = pick(k, [f"{w} survived {l} by {pts(margin)}, {ws}-{ls}.",
                        f"{w} got past {l} by a hair, {ws}-{ls}. A {pts(margin)}-point game."])
    elif margin < 8:
        lead = pick(k, [f"{w} edged {l}, {ws}-{ls}.", f"{w} held off {l}, {ws}-{ls}."])
    elif margin < 25:
        lead = pick(k, [f"{w} beat {l}, {ws}-{ls}.", f"{w} took care of {l}, {ws}-{ls}."])
    elif margin < 45:
        lead = pick(k, [f"{w} handled {l} with room to spare, {ws}-{ls}.",
                        f"{w} never let {l} get close, winning {ws}-{ls}."])
    else:
        lead = pick(k, [f"{w} ran {l} out of the building, {ws}-{ls}. That's a {pts(margin)}-point beating.",
                        f"{w} buried {l}, {ws}-{ls}, winning by {pts(margin)}."])

    parts = [lead]
    if W["starters"]:
        top = max(W["starters"], key=lambda p: p["pts"])
        parts.append(f"{top['name']} led the way with {pts(top['pts'])}.")
    if W["score"] == week_hi:
        parts.append("It was the highest score of the week.")
    if L["score"] == week_lo:
        parts.append(f"{l} also posted the lowest score of the week.")

    swap = best_bench_swap(L)
    if swap and swap[0] > margin:
        gain, b, s = swap
        parts.append(f"The painful part: {b['name']} scored {pts(b['pts'])} on {l}'s bench while "
                     f"{s['name']} put up {pts(s['pts'])} in the lineup. That swap alone wins it.")
    elif swap and swap[0] >= 8:
        gain, b, s = swap
        parts.append(f"{l} also left {b['name']} ({pts(b['pts'])}) on the bench.")
    return " ".join(parts)


def ai_recap(m, week, fallback):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    facts = {
        "week": week,
        "playoff_game": m["playoff"],
        "teams": [
            {"manager": who(s), "team_name": s["name"], "score": s["score"],
             "starters": s["starters"], "bench": s["bench"]}
            for s in (m["home"], m["away"])
        ],
        "notes": fallback,
    }
    prompt = (
        "Write a recap of this fantasy football matchup for a friends' league website. "
        "3 to 5 sentences, plain text, no headline. Sound like the league's group chat: "
        "playful trash talk, keep it PG-13. Use only facts in the data; don't invent injuries, "
        "trades or history. Refer to people by manager name.\n\n" + json.dumps(facts)
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": CFG.get("recapModel", "claude-sonnet-5-5"), "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []))
        return text.strip() or None
    except Exception as e:  # never let a recap break the update
        print(f"::warning::Claude recap failed for {m['key']}: {e}")
        return None


def main():
    s2, swid = os.environ.get("ESPN_S2"), os.environ.get("ESPN_SWID")
    if not s2 or not swid:
        sys.exit("Missing the ESPN_S2 or ESPN_SWID secret. Add both under Settings > Secrets and variables > Actions.")

    season = int(CFG["season"])
    try:
        league = League(league_id=int(CFG["leagueId"]), year=season, espn_s2=s2, swid=swid)
    except Exception as e:
        sys.exit(f"ESPN refused the request ({e}). If this used to work, the ESPN cookies have "
                 "probably expired: copy fresh espn_s2 and SWID values into the repository secrets.")

    teams, by_id = [], {}
    for t in league.teams:
        rec = {"espnId": t.team_id, "manager": match_manager(t), "owner": owner_name(t),
               "name": t.team_name, "w": t.wins, "l": t.losses, "t": t.ties,
               "pf": round(t.points_for, 2), "pa": round(t.points_against, 2),
               "seed": t.standing, "final": t.final_standing or 0}
        teams.append(rec)
        by_id[t.team_id] = rec
    missing = [f"{t['name']} (ESPN team {t['espnId']}, owner {t['owner'] or 'unknown'})"
               for t in teams if not t["manager"]]
    if missing:
        print("::warning::Couldn't match these teams to a manager. Add them to \"managers\" in "
              "league.json: " + "; ".join(missing))

    season_over = bool(teams) and all(t["final"] for t in teams)
    current = league.current_week
    last = min(current, league.finalScoringPeriod)

    # Reuse Claude-written recaps for games whose scores haven't changed.
    out_path = ROOT / "data" / f"{season}.json"
    old = {}
    if out_path.exists():
        try:
            for wk in json.loads(out_path.read_text()).get("weeks", []):
                for m in wk["matchups"]:
                    old[m["key"]] = m
        except Exception:
            pass

    def side(team, score, lineup):
        tid = getattr(team, "team_id", team)
        info = by_id.get(tid, {})
        starters, bench = [], []
        for p in lineup:
            row = {"name": p.name, "pos": p.position, "slot": p.slot_position,
                   "pts": round(p.points or 0, 2), "proj": round(p.projected_points or 0, 2)}
            (bench if p.slot_position in BENCH_SLOTS else starters).append(row)
        return {"espnId": tid, "manager": info.get("manager"), "name": info.get("name"),
                "score": round(score or 0, 2), "starters": starters, "bench": bench}

    weeks, cache = [], {}
    for wk in range(1, last + 1):
        done = season_over or wk < current
        matchups = []
        for b in league.box_scores(wk, player_team_cache=cache):
            if not b.home_team or not b.away_team:
                continue  # bye week
            h = side(b.home_team, b.home_score, b.home_lineup)
            a = side(b.away_team, b.away_score, b.away_lineup)
            ids = sorted([h["espnId"], a["espnId"]])
            matchups.append({"key": f"{season}-{wk}-{ids[0]}-{ids[1]}", "home": h, "away": a,
                             "playoff": b.is_playoff, "type": b.matchup_type, "final": done})
        if not matchups:
            continue
        scores = [s["score"] for m in matchups for s in (m["home"], m["away"])]
        hi, lo = max(scores), min(scores)
        for m in matchups:
            if not done:
                m["recap"] = None
                continue
            base = auto_recap(m, hi, lo)
            prev = old.get(m["key"])
            if (prev and prev.get("recapBy") == "claude"
                    and prev["home"]["score"] == m["home"]["score"]
                    and prev["away"]["score"] == m["away"]["score"]):
                m["recap"], m["recapBy"] = prev["recap"], "claude"
                continue
            text = ai_recap(m, wk, base)
            m["recap"], m["recapBy"] = (text, "claude") if text else (base, "auto")
        weeks.append({"week": wk, "final": done, "playoff": any(m["playoff"] for m in matchups),
                      "matchups": matchups})

    data = {
        "season": season,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
        "regularSeasonWeeks": league.settings.reg_season_count,
        "playoffTeams": league.settings.playoff_team_count,
        "currentWeek": current,
        "seasonOver": season_over,
        "teams": teams,
        "weeks": weeks,
    }
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(data, indent=1))
    seasons = sorted(int(f.stem) for f in out_path.parent.glob("*.json") if f.stem.isdigit())
    (out_path.parent / "index.json").write_text(json.dumps({"seasons": seasons}))
    print(f"Saved {out_path.name}: {len(teams)} teams, {len(weeks)} weeks, season over: {season_over}")


if __name__ == "__main__":
    main()
