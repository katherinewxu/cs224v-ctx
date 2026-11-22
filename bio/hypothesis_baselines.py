"""Offline floor/reference for graded hypotheses (evaluator --hypothesis-every), no LLM.

Genes are picked by the info-matched `nbr` policy; at every K-th round (and the last) each strategy
submits 5 modules of 5 tested genes, graded with evaluator.grade_module:

    random     random tested genes, random sign (the floor)
    hits       tested hits of one sign, grouped at random (needs the scores, no neighbour reasoning)
    nbr_hits   tested hits of one sign grouped by shared lookup neighbours, ranked by how many of a
               hit's looked-up neighbours were themselves same-sign hits (perfect bookkeeping of
               scores and lookups; the reference for an agent that keeps both)
    frozen     nbr_hits' modules from the first checkpoint, resubmitted unchanged (what most agents did)
    dup5       nbr_hits' best module submitted 5 times (what plain Codex did in the fresh+found pilot)

With --fresh each module must include a gene tested since the last checkpoint (hits and nbr_hits build
around fresh hits; random and frozen do not adapt), and --denom found grades on held-out genes found.
--dedup counts each same-sign held-out hit once per checkpoint (evaluator --hypothesis-dedup).

    bio/.venv/bin/python -I bio/hypothesis_baselines.py --rounds 30 --batch 16 --every 10 --seeds 0 1 2 3 4
    bio/.venv/bin/python -I bio/hypothesis_baselines.py --rounds 100 --batch 32 --fresh --denom found
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baselines import _nbr_pick  # noqa: E402
from env import BioEnv  # noqa: E402
from evaluator import dedup_score, grade_module  # noqa: E402

N_MOD, N_GENES = 5, 5


def strategies(env, looked, rng, fresh=None):
    sc = {g: v for l in env.log for g, v in l.revealed.items() if g in l.accepted}
    tested = sorted(sc)
    hit = {g for g in tested if env.is_hit(g)}
    out = {"random": [{"genes": list(rng.choice(tested, N_GENES, replace=False)), "sign": rng.choice(["+", "-"])}
                      for _ in range(N_MOD)]}
    by_sign = {s: [g for g in hit if (sc[g] > 0) == (s == "+")] for s in "+-"}
    mods = []
    for s in sorted(by_sign, key=lambda s: -len(by_sign[s])):
        pool = list(by_sign[s]); rng.shuffle(pool)
        if fresh is not None:  # one fresh hit first in each group
            fr = [g for g in pool if g in fresh]; old = [g for g in pool if g not in fresh]
            for f in fr:
                if len(old) < N_GENES - 1:
                    break
                mods.append({"genes": [f] + [old.pop() for _ in range(N_GENES - 1)], "sign": s})
            continue
        mods += [{"genes": pool[i:i + N_GENES], "sign": s} for i in range(0, len(pool) - N_GENES + 1, N_GENES)]
    out["hits"] = sorted(mods, key=lambda m: rng.random())[:N_MOD]
    # nbr_hits: enrichment from looked-up lists only
    mods = []
    for s, pool in by_sign.items():
        same = set(pool)
        enrich = {g: sum(h in same for h in looked.get(g, [])) for g in pool}
        used = set()
        for g in sorted(pool, key=lambda g: (-enrich[g], g)):
            if g in used:
                continue
            Ng = set(looked.get(g, []))
            mates = [x for x in pool if x != g and x not in used and (x in Ng or Ng & set(looked.get(x, [])))]
            mates = sorted(mates, key=lambda x: (-enrich[x], x))[:N_GENES - 1]
            if len(mates) + 1 >= 3:
                mods.append(({"genes": [g] + mates, "sign": s}, enrich[g] + sum(enrich[x] for x in mates)))
                used.update([g] + mates)
    best = [m for m, _ in sorted(mods, key=lambda t: -t[1])[:N_MOD]]
    if fresh is not None:  # keep the best modules, add to each the fresh same-sign hit most linked to it
        taken = {g for m in best for g in m["genes"]}
        for m in best:
            cand = [x for x in by_sign[m["sign"]] if x in fresh and x not in taken]
            if not cand:
                continue
            nb = {h for g in m["genes"] for h in looked.get(g, [])}
            link = lambda x: (x in nb) + len(nb & set(looked.get(x, []))) + sum(x in looked.get(g, []) for g in m["genes"])
            x = max(sorted(cand), key=link)
            m["genes"] = m["genes"] + [x]; taken.add(x)
    out["nbr_hits"] = best
    out["dup5"] = [dict(best[0]) for _ in range(N_MOD)] if best else []
    return out


def run(seed, rounds, batch, every, heldout, reserve, use_fresh=False, denom="fixed", dedup=False):
    env = BioEnv("IFNG", rounds=rounds, batch=batch, anonymize=True, seed=seed, features="depmap")
    if reserve:
        env.set_reserve(reserve, seed + 1)
    rng = np.random.default_rng(2000 + seed)
    srng = np.random.default_rng(3000 + seed)  # module strategies only, so gene picks match across grading rules
    st = {"looked": set(), "cand": {}}
    looked = {}
    scores = {}
    n = len(env.ids)
    prev, first = 0, None
    while not env.done:
        mask = np.zeros(n, bool); mask[[env.index[g] for g in env.tested]] = True
        before = set(st["looked"])
        mask[[env.index[g] for g in env.reserved]] = True  # never proposable
        pick = _nbr_pick(env, mask, np.flatnonzero(~mask), st, batch, 4, rng)
        for g in st["looked"] - before:
            looked[g] = [h for h, _ in env.lookup(g)]
        env.propose([env.ids[i] for i in pick]); env.end_round()
        if env.round % every == 0 or env.done:
            fresh = {g for l in env.log[prev:] for g in l.accepted}
            strat = strategies(env, looked, srng, fresh if use_fresh else None)
            if first is None:
                first = [dict(m) for m in strat["nbr_hits"]]
            strat["frozen"] = first
            for name, mods in strat.items():
                g = [grade_module(env, m["genes"], m["sign"], heldout, denom=denom,
                                  fresh=fresh if use_fresh else None) for m in mods]
                s = dedup_score(g, N_MOD, heldout) if dedup else sum(x["score"] for x in g) / N_MOD
                scores.setdefault(name, []).append(s)
            prev = env.round
    return {k: float(np.mean(v)) for k, v in scores.items()}, env.log[-1].cum_hits


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--every", type=int, default=10)
    ap.add_argument("--heldout", type=int, default=8)
    ap.add_argument("--reserve", type=float, default=0.15)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--denom", choices=["fixed", "found"], default="fixed")
    ap.add_argument("--dedup", action="store_true")
    a = ap.parse_args()
    rows = [run(s, a.rounds, a.batch, a.every, a.heldout, a.reserve, a.fresh, a.denom, a.dedup) for s in a.seeds]
    for name in rows[0][0]:
        v = [r[0][name] for r in rows]
        print(f"{a.rounds}x{a.batch} {name:9s} mean hypothesis score {np.mean(v):.3f} (seeds {', '.join(f'{x:.3f}' for x in v)})")
    print(f"{a.rounds}x{a.batch} hits (nbr picks): {[r[1] for r in rows]}")
