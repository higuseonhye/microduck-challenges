#!/usr/bin/env bash
# The live Arena leaderboards: what first place takes right now.
#   bash scripts/vessl/board.sh            # all five
#   bash scripts/vessl/board.sh sprint-2m
set -uo pipefail
events=${1:-"sprint-2m hill-climb-1m5 roller-sprint-2m tug-of-war got-a-talent"}
for ev in $events; do
  echo "== $ev"
  curl -s "https://pollen-robotics-microduck-arena.hf.space/api/events/${ev}/leaderboard" | python3 -c '
import json, sys
d = json.load(sys.stdin)
rows = d if isinstance(d, list) else d.get("rows") or d.get("leaderboard") or d.get("entries") or []
for i, r in enumerate(rows[:10], 1):
    keys = ("score", "seeds_finished", "command_vx", "votes", "shown")
    print(f"{i:>2}. {r.get(\"user\",\"?\"):<20} {r.get(\"policy_name\",\"\"):<36}", "  ".join(f"{k}={r[k]}" for k in keys if k in r))
if not rows: print(json.dumps(d)[:600])
' || echo "(no response)"
done
