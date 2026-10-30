#!/usr/bin/env bash
# Launch one or more seeds of a challenge's training in the background, a checkpoint every
# SAVE iterations (default 50: the recipes swing a lot between checkpoints, so judge densely).
#
#   bash scripts/vessl/launch.sh <event> <name> "<seeds>" [iters] [-- extra train args]
#   bash scripts/vessl/launch.sh sprint-2m base "1 2 3" 3000
#   bash scripts/vessl/launch.sh tug-of-war base "1 2" 1000
#
# Several seeds share the GPUs round-robin (CUDA_VISIBLE_DEVICES). On one 80 GB GPU, 2-3 runs of
# 4096 envs fit; set ENVS=2048 to pack more. Commit before launching: publish refuses dirty runs.
set -euo pipefail
event=$1; name=$2; seeds=$3; iters=${4:-}
shift $(( $# >= 4 ? 4 : $# )); [[ ${1:-} == "--" ]] && shift
extra=("$@")

case $event in
  sprint-2m)        task=Mjlab-Sprint2m-MicroDuck;       def=3000 ;;
  hill-climb-1m5)   task=Mjlab-HillClimb1m5-MicroDuck;   def=3000 ;;
  roller-sprint-2m) task=Mjlab-RollerSprint2m-MicroDuck; def=3000 ;;
  tug-of-war)       task=Mjlab-TugOfWar-MicroDuck;       def=1000 ;;
  got-a-talent)     task=Mjlab-GotATalent-MicroDuck;     def=3000 ;;
  *) echo "unknown event $event"; exit 2 ;;
esac
iters=${iters:-$def}
save=${SAVE:-50}
envs=${ENVS:-4096}

git diff --quiet HEAD -- src || { echo "uncommitted changes in src/: commit first"; exit 2; }
ngpu=$(nvidia-smi -L | wc -l)
mkdir -p logs
i=0
for s in $seeds; do
  gpu=$(( i % ngpu )); run="${name}-s${s}"
  CUDA_VISIBLE_DEVICES=$gpu nohup uv run --frozen train "$task" \
    --env.scene.num-envs "$envs" --agent.max-iterations "$iters" --agent.save-interval "$save" \
    --agent.seed "$s" --agent.logger tensorboard --agent.run-name "$run" "${extra[@]}" \
    > "logs/${run}.log" 2>&1 &
  echo "$run  gpu$gpu  pid $!  commit $(git rev-parse --short HEAD)  log logs/${run}.log"
  i=$((i+1))
done
