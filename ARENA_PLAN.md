# Arena campaign — all five events, trained on VESSL

Read the challenge's own `src/microduck_challenges/<folder>/AGENTS.md` before changing anything in it.
These are the additions on this branch, and the order to run them in.

## Setup (once per VESSL workspace)

```bash
git clone https://github.com/higuseonhye/microduck-challenges && cd microduck-challenges && git checkout arena
bash scripts/vessl/setup.sh          # uv sync, GPU check, references, pytest
uv run hf auth login                 # your HF write token, typed by you
bash scripts/vessl/board.sh          # what first place takes today
```

Keep `logs/` on the workspace's persistent volume (symlink it there) so a pause keeps the runs.

## The tools

| Script | What it does |
|---|---|
| `scripts/vessl/launch.sh <event> <name> "<seeds>" [iters] [-- train args]` | seeds in parallel, a checkpoint every 50 iterations (`SAVE=`), refuses an uncommitted `src/` |
| `scripts/vessl/judge.py <event> [--watch]` | every checkpoint through `publish --dry-run` + `arena score`, in parallel on the CPUs; results in `logs/judge/<event>.jsonl`, ONNX kept in `logs/judge/onnx/`, ranked table |
| `scripts/vessl/board.sh [event]` | live leaderboards |
| `scripts/talent_choir.py` | writes `got_a_talent/choir.json`, the 8-duck troupe |

Then publish the winner (on your yes):
`uv run publish --run logs/rsl_rl/<exp>/<run> --checkpoint <N> --repo higuseonhye/microduck-<name> --no-private --enter`

## Order of battle

1. **Tug of War — today.** Weekly cup entries close Friday 16:00 Paris (24:00 KST).
   - `bash scripts/vessl/launch.sh tug-of-war base "1 2 3" 1000` (recipe as shipped; +138 cm at 250 in the docs).
   - `judge.py tug-of-war --watch`. Runs peak at 250–500: publish the best rated checkpoint with no fault.
   - Next week: the **league** (`TUG_OPPONENTS`, below) against the top public entries, for the cup.
2. **Sprint, Hill, Roller — seed and checkpoint harvest first.** Same recipe, 3 seeds, judged every 50
   iterations. The docs show checkpoint-to-checkpoint swings of 4.9 s → 14.7 s (sprint) and
   5.9 s → 10 s (hill): the recipe's best checkpoint is rarely the one at 250-multiples.
   - `launch.sh sprint-2m base "1 2 3" 3000`, `launch.sh hill-climb-1m5 base "1 2 3" 3000`,
     `launch.sh roller-sprint-2m base "1 2 3" 3000`
3. **Sprint, Hill — lane-frame tracking** (branch `exp/lane-tracking`, `LANE_TRACKING = True`): the speed
   is tracked along the spawn heading, so crab-walking and sideways drift stop paying; the
   refuted `lane_hold` was a position reward that standing still kept earning, this one is not.
   Compare against step 2's seeds, not against one run.
4. **Got a Talent — the Duck Choir.** Train the recipe once (`launch.sh got-a-talent base "1"`), pick the
   checkpoint that passes `python -m microduck_challenges.got_a_talent.check <onnx>` on Pollen's
   timeline, then stage the troupe with `--timeline src/microduck_challenges/got_a_talent/choir.json`
   in the workshop, watch it, and publish with that timeline. Votes decide: no guarantee.

## Tug league

`TUG_OPPONENTS="reference,/abs/a.onnx,/abs/b.onnx"` splits the envs evenly between those frozen
ducks (env i plays opponent i % k). Every file must be the recipe's actor (Sub, Div, 4 Gemm, 3 Elu;
`load_actor` refuses anything else). Unset, training is the recipe's. The variable is not in the
commit that publish records: write it in the commit message of a league run.

## Rules kept

One change per run, commit before launch, every checkpoint judged with the Arena's evaluator,
never conclude on one seed, nothing published or entered without the user's yes.
