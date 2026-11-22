"""Re-score saved hypothesis checkpoints (ours/evals/<run>/run.json) under old, fresh+found and fresh+found+dedup.

    bio/.venv/bin/python -I bio/rescore_hypotheses.py hyp_ours_s1 hyp_base_s1 ...  (run from the repo root)
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "bio")
from env import BioEnv
from evaluator import dedup_score
for r in sys.argv[1:]:
    d = json.load(open(f"ours/evals/{r}/run.json")); c = json.load(open(f"ours/evals/{r}/config.json"))
    sf = Path(f"ours/evals/{r}/seed_revealed.txt")
    if sf.exists():
        seed = int(sf.read_text().strip())
        env = BioEnv(c["screen"], rounds=c["rounds"], batch=c["batch"], anonymize=True, seed=seed, features=c["features"])
        ok = lambda h, s: bool(env._is_hit[env.index[h]]) and (env._score[env.index[h]] > 0) == (s == "+")
    else:
        ok = None  # seed never revealed (run cut short): good count from the stored fixed-rule score, no dedup
    rows = {"old": [], "ff": [], "ffd": []}; prev = 0
    for h in d["hypotheses"]:
        a = h["after_round"]
        fresh = {g for l in d["rounds"][prev:a] for g in l["accepted"]}
        g = []
        for m in h["modules"]:
            if ok:
                good = [x for x in m["heldout"] if ok(x, m["sign"])]
            else:
                k = round(m["score"] * 8) if not c.get("hypothesis_denom") == "found" else round(m["score"] * len(m["heldout"]))
                good = [f"?{i}" for i in range(k)]
            s = len(good) / len(m["heldout"]) if len(m["heldout"]) >= 3 else 0.0
            if not any(x in fresh for x in m["members"]): s = 0.0
            g.append({"good": good, "score": s})
        n = 5
        rows["old"].append(h["score"]); rows["ff"].append(sum(x["score"] for x in g) / n)
        rows["ffd"].append(dedup_score(g, n, 8)); prev = a
    mean = lambda v: sum(v) / len(v)
    dd = f"{mean(rows['ffd']):.3f}" if ok else "n/a (seed not revealed)"
    print(f"{r:18s} old {mean(rows['old']):.3f}  fresh+found {mean(rows['ff']):.3f}  +dedup {dd}  (checkpoints {len(rows['old'])})")
