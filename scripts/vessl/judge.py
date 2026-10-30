"""Judge every checkpoint of every run with the Arena's own evaluator, in parallel on the CPUs.

    uv run --frozen --group workshop python scripts/vessl/judge.py sprint-2m            # all runs
    uv run --frozen --group workshop python scripts/vessl/judge.py sprint-2m --runs base-s1 base-s2
    uv run --frozen --group workshop python scripts/vessl/judge.py tug-of-war --watch    # keep judging as checkpoints land

Each checkpoint: `publish --dry-run` (the real export, the normalizer baked in), then `arena score`.
Results go to logs/judge/<event>.jsonl (one line per checkpoint, never re-judged) and a ranked
table is printed: races by 5/5 first then lowest time, the tug by highest rating.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = {
    "sprint-2m": "sprint_2m",
    "hill-climb-1m5": "hill_climb_1m5",
    "roller-sprint-2m": "roller_sprint_2m",
    "tug-of-war": "tug_of_war",
}
TUG = "tug-of-war"


def checkpoints(run: Path) -> list[int]:
    return sorted(int(m.group(1)) for p in run.glob("model_*.pt") if (m := re.fullmatch(r"model_(\d+)\.pt", p.name)))


def parse(event: str, out: str) -> dict:
    if event == TUG:
        m = re.search(r"rating: ([-+\d.]+) cm", out)
        faults = out.count(" fault")
        pits = len(re.findall(r"seed \d+: \S+\s+\S*pit", out))
        return {"score": float(m.group(1)) if m else None, "faults": faults, "pits_hint": pits}
    s = re.search(r"score ([\d.]+)s · (\d+)/(\d+) finished", out)
    v = re.search(r"scored at ([\d.]+) m/s", out)
    return {
        "score": float(s.group(1)) if s else None,
        "finished": int(s.group(2)) if s else 0,
        "of": int(s.group(3)) if s else 0,
        "vx": float(v.group(1)) if v else None,
    }


def judge_one(event: str, run: str, n: int) -> dict:
    tag = f"j{os.getpid()}-{Path(run).name[-40:]}-{n}".replace("_", "-").lower()
    repo = f"local/microduck-{tag}"
    out_dir = ROOT / f"publish-{tag}"
    row = {"event": event, "run": Path(run).name, "ckpt": n}
    try:
        exp = subprocess.run(
            ["uv", "run", "--frozen", "publish", "--run", run, "--checkpoint", str(n), "--repo", repo,
             "--dry-run", "--allow-dirty", "--device", "cpu"],
            cwd=ROOT, capture_output=True, text=True, timeout=900,
        )
        onnx = out_dir / "policy.onnx"
        if not onnx.exists():
            return row | {"error": "export failed: " + (exp.stderr or exp.stdout)[-400:]}
        keep = ROOT / "logs" / "judge" / "onnx" / row["run"]
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(onnx, keep / f"model_{n}.onnx")
        sc = subprocess.run(
            ["uv", "run", "--frozen", "--group", "workshop", "arena", "score", str(onnx), "--event", event],
            cwd=ROOT, capture_output=True, text=True, timeout=3600,
        )
        return row | parse(event, sc.stdout) | {"raw": sc.stdout[-1500:]}
    except subprocess.TimeoutExpired as e:
        return row | {"error": f"timeout: {e.cmd[:3]}"}
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def load(path: Path) -> dict[tuple[str, int], dict]:
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            done[(r["run"], r["ckpt"])] = r
    return done


def table(event: str, rows: list[dict], top: int) -> str:
    ok = [r for r in rows if r.get("score") is not None]
    if event == TUG:
        ok.sort(key=lambda r: (r.get("faults", 0) > 0, -r["score"]))
        lines = [f"{r['run']:<45} {r['ckpt']:>6}  {r['score']:+8.1f} cm  faults {r.get('faults', 0)}" for r in ok[:top]]
    else:
        ok.sort(key=lambda r: (-r["finished"], r["score"]))
        lines = [f"{r['run']:<45} {r['ckpt']:>6}  {r['score']:7.3f} s  {r['finished']}/{r['of']}  at {r['vx']:.2f} m/s" for r in ok[:top]]
    bad = [r for r in rows if r.get("error")]
    if bad:
        lines.append(f"({len(bad)} failed: e.g. {bad[0]['run']} {bad[0]['ckpt']}: {bad[0]['error'][:120]})")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("event", choices=sorted(EXPERIMENT))
    ap.add_argument("--runs", nargs="*", help="substrings of run folder names (default: all)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--watch", action="store_true", help="loop, judging new checkpoints every 2 min")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()

    base = ROOT / "logs" / "rsl_rl" / EXPERIMENT[a.event]
    store = ROOT / "logs" / "judge" / f"{a.event}.jsonl"
    store.parent.mkdir(parents=True, exist_ok=True)
    while True:
        done = load(store)
        runs = [r for r in sorted(base.glob("*")) if r.is_dir() and (not a.runs or any(s in r.name for s in a.runs))]
        todo = [(str(r), n) for r in runs for n in checkpoints(r) if (r.name, n) not in done]
        if todo:
            print(f"[judge] {len(todo)} checkpoints on {a.workers} workers", flush=True)
            with ProcessPoolExecutor(a.workers) as pool, store.open("a") as f:
                futs = [pool.submit(judge_one, a.event, r, n) for r, n in todo]
                for fu in as_completed(futs):
                    row = fu.result()
                    f.write(json.dumps(row) + "\n"); f.flush()
                    s = row.get("score")
                    print(f"  {row['run']} {row['ckpt']}: {s if s is not None else row.get('error', '?')[:80]}"
                          + (f" {row.get('finished')}/{row.get('of')} @{row.get('vx')}" if a.event != TUG and s else ""), flush=True)
        rows = [r for r in load(store).values() if not a.runs or any(s in r["run"] for s in a.runs)]
        print("\n" + table(a.event, rows, a.top) + "\n", flush=True)
        if not a.watch:
            return 0
        time.sleep(120)


if __name__ == "__main__":
    sys.exit(main())
