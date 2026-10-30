#!/usr/bin/env bash
# One-time setup on a VESSL GPU workspace. Run from the repo root:
#   bash scripts/vessl/setup.sh
set -euo pipefail

command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
uv sync --frozen --group workshop

nvidia-smi --query-gpu=index,name,memory.total --format=csv
uv run python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.device_count())"

# HF login is needed for reference downloads, publish and the Arena entry.
uv run hf auth whoami || echo ">> run: uv run hf auth login   (paste your HF write token yourself)"

# Pollen's reference policies: the bar for each race.
for ev in sprint-2m hill-climb-1m5 roller-sprint-2m; do
  uv run hf download "pollen-robotics/microduck-${ev}-reference" policy.onnx \
    --local-dir "logs/reference/${ev}" >/dev/null && echo "reference ${ev}: ok" || echo "reference ${ev}: not found"
done

uv run --group workshop pytest -q
