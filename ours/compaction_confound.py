"""Do repeats cluster in rounds with a compaction, beyond the trend with round number? (no model calls)

compaction_analysis.py found more repeats per round in rounds with a compaction, but later rounds have
both more compactions and more repeats. Here rounds are compared only with rounds from the same block
of 10 (the same stage of the run): within each block, mean repeats in rounds with a compaction minus
rounds without, averaged over blocks that have both, weighted by the smaller group. Significance: a
permutation test that shuffles the compaction labels within each block (keeps the per-block trend).

    bio/.venv/bin/python -I ours/compaction_confound.py nf_base_s0 nf_base_s1 hyp_base_s0 ...
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compaction_analysis import ROOT, events  # noqa: E402

BLOCK = 10


def labels(name):
    rd = sorted((ROOT / "ours/runs").glob(f"{name}-*"))[-1]
    rounds = json.loads((ROOT / "ours/evals" / name / "run.json").read_text())["rounds"]
    done, comp = 0, set()
    for kind, _ in events(rd):
        if kind == "end_round":
            done += 1
        elif kind == "compact":
            comp.add(done + 1)
    reps = np.array([len(r.get("repeats", [])) for r in rounds], float)
    c = np.array([i + 1 in comp for i in range(len(rounds))])
    blocks = np.arange(len(rounds)) // BLOCK
    return reps, c, blocks


def effect(reps, c, blocks):
    num = den = 0.0
    for b in np.unique(blocks):
        m = blocks == b
        w, wo = reps[m & c], reps[m & ~c]
        if len(w) and len(wo):
            k = min(len(w), len(wo))
            num += k * (w.mean() - wo.mean()); den += k
    return num / den if den else float("nan"), den


def perm_p(reps, c, blocks, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    obs, _ = effect(reps, c, blocks)
    idx = [np.where(blocks == b)[0] for b in np.unique(blocks)]
    ge = 0
    for _ in range(n):
        cp = c.copy()
        for ix in idx:
            cp[ix] = rng.permutation(c[ix])
        ge += effect(reps, cp, blocks)[0] >= obs
    return (ge + 1) / (n + 1)


if __name__ == "__main__":
    print(f"| run | rounds with / without compaction | repeats | raw diff | within-block diff | blocks used | p (one-sided) |")
    print("|---|---|---|---|---|---|---|")
    for name in sys.argv[1:]:
        reps, c, blocks = labels(name)
        raw = reps[c].mean() - reps[~c].mean() if c.any() and (~c).any() else float("nan")
        eff, w = effect(reps, c, blocks)
        used = sum(1 for b in np.unique(blocks) if (c & (blocks == b)).any() and (~c & (blocks == b)).any())
        p = perm_p(reps, c, blocks) if reps.sum() else float("nan")
        print(f"| {name} | {int(c.sum())} / {int((~c).sum())} | {int(reps.sum())} | {raw:+.2f} | {eff:+.2f} | "
              f"{used} | {p:.3f} |")
