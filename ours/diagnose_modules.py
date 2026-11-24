"""Why are hypothesis scores low: memory or reasoning? (no model calls)

For every module member at every checkpoint of a hypothesis run, compare with the ground truth from the
evaluator (ours/evals/<run>/run.json, requests.jsonl) and with what the agent's own files held at that
moment (the run's workspace.git snapshot just before its hypothesis call):

  good          a hit with the predicted sign
  bad, known    not a good member, and the agent's files held its correct score (it had the facts)
  bad, wrong    the files held a different score for it (memory error)
  bad, absent   no score for it in the files (memory gap; it may have been held in the JS REPL store)

Also: whether members were looked up by the agent before the checkpoint (it only sees neighbour lists of
genes it looked up, and grading uses members' neighbour lists), and an "own-data" reference: the
neighbour-grouping strategy run on exactly the agent's tested genes and lookups at that checkpoint,
graded with the v3 rules, next to the agent's own v3 score. A gap between the two is a reasoning gap
(same information, worse grouping); a low own-data score means the agent's exploration limited it.

    bio/.venv/bin/python -I ours/diagnose_modules.py v3_ours_s0 v3_base_s0 hyp_ours_s1 ...
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bio"))
from env import BioEnv  # noqa: E402
from evaluator import dedup_score, grade_module  # noqa: E402
from hypothesis_baselines import strategies  # noqa: E402

GENE_NUM = re.compile(r"(G\d{5})\b[^G]{0,60}?(-?\d*\.\d+)")


def run_dir(name):
    d = sorted((ROOT / "ours/runs").glob(f"{name}-*"))
    return d[-1]


def session_events(rd):
    for f in sorted(rd.glob("harness/codex_home/sessions/**/*.jsonl")):
        for line in f.read_text().splitlines():
            x = json.loads(line)
            yield x, (x.get("payload") if isinstance(x.get("payload"), dict) else {})


def hypothesis_times(rd):
    """Timestamps of hypothesis calls the evaluator accepted ("recorded"), from the Codex session log."""
    calls, out = {}, []
    for x, p in session_events(rd):
        if x.get("type") != "response_item":
            continue
        if p.get("type") in ("custom_tool_call", "function_call") and "mcp__bda__hypothesis" in json.dumps(p):
            calls[p.get("call_id")] = x["timestamp"]
        elif p.get("type") in ("custom_tool_call_output", "function_call_output") and p.get("call_id") in calls:
            if '\\"recorded\\": true' in json.dumps(p) or '"recorded": true' in json.dumps(p) or "recorded" in json.dumps(p):
                out.append(calls[p["call_id"]])
    return out


def first_mentions(rd):
    """file name -> time of the first tool call whose input mentions it (when the agent started that file)."""
    out = {}
    for x, p in session_events(rd):
        if x.get("type") == "response_item" and p.get("type") in ("custom_tool_call", "function_call"):
            for name in re.findall(r"[\w./-]+\.(?:json|jsonl|txt|csv|tsv|md)", json.dumps(p)):
                out.setdefault(Path(name).name, x["timestamp"])
    return out


def iso(ts):
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def snapshot_scores(rd, ts, tested_by=None, mentions=None):
    """gene -> set of scores in the agent's workspace files as of time ts. With per-step commits (prototype),
    the latest commit at or before ts. Otherwise (plain Codex: start and end commits only) the final files:
    a file last written before ts counts whole; a file rewritten later counts only if the agent had started
    it before ts, and then only for genes tested by that checkpoint (an upper bound)."""
    git = ["git", f"--git-dir={rd / 'workspace.git'}"]
    n = int(subprocess.run(git + ["rev-list", "--count", "--all"], capture_output=True, text=True).stdout.strip() or 0)
    texts = []
    if n > 2:
        c = subprocess.run(git + ["rev-list", "-1", f"--before={ts}", "--all"], capture_output=True, text=True).stdout.strip()
        if c:
            for f in subprocess.run(git + ["ls-tree", "-r", "--name-only", c], capture_output=True, text=True).stdout.split():
                if re.search(r"\.(json|jsonl|txt|csv|tsv|md)$", f):
                    texts.append((subprocess.run(git + ["show", f"{c}:{f}"], capture_output=True, text=True,
                                                 errors="replace").stdout, None))
    else:
        t = iso(ts)
        for f in (rd / "workspace").rglob("*"):
            if not f.is_file() or not re.search(r"\.(json|jsonl|txt|csv|tsv|md)$", f.name):
                continue
            if f.stat().st_mtime <= t:
                texts.append((f.read_text(errors="replace"), None))
            elif mentions and f.name in mentions and iso(mentions[f.name]) <= t:
                texts.append((f.read_text(errors="replace"), tested_by))
    rec = {}
    for text, only in texts:
        for g, v in GENE_NUM.findall(text):
            if only is not None and g not in only:
                continue
            try:
                rec.setdefault(g, set()).add(round(float(v), 4))
            except ValueError:
                pass
    return rec, n


def diagnose(name):
    ev = ROOT / "ours/evals" / name
    d = json.loads((ev / "run.json").read_text()); cfg = json.loads((ev / "config.json").read_text())
    rd = run_dir(name)
    truth = {g: (l["revealed"][g], g in l["hits"]) for l in d["rounds"] for g in l["accepted"]}
    reqs = [json.loads(l) for l in open(ev / "requests.jsonl")]
    looks = [(r["round"], r["response"].get("neighbors", {})) for r in reqs
             if r["path"] == "/lookup" and isinstance(r.get("response"), dict)]
    times = hypothesis_times(rd)
    mentions = first_mentions(rd)
    if len(times) != len(d["hypotheses"]):
        print(f"warning: {name}: {len(times)} accepted hypothesis calls in the log, {len(d['hypotheses'])} checkpoints",
              file=sys.stderr)
    seedf = ev / "seed_revealed.txt"
    env = None
    if seedf.exists():
        seed = int(seedf.read_text().strip())
        env = BioEnv(cfg["screen"], rounds=cfg["rounds"], batch=cfg["batch"], anonymize=True, seed=seed,
                     features=cfg["features"])
        env.set_reserve(cfg["reserve"], seed + 1)
    tot = {k: 0 for k in ("members", "good", "bad_known", "bad_wrong", "bad_absent", "nonhit", "wrongsign",
                          "looked_up", "good_looked_up", "fresh", "fresh_good", "fresh_nonhit_known")}
    agent_v3, own_v3, rows = [], [], []
    played, prev, prev_cp = 0, 0, 0
    for i, h in enumerate(d["hypotheses"]):
        a = h["after_round"]
        tested_by = {g for l in d["rounds"][:a] for g in l["accepted"]}
        rec, _ = snapshot_scores(rd, times[i], tested_by, mentions) if i < len(times) else ({}, None)
        looked = {g: nb for r, L in looks if r <= a for g, nb in L.items()}
        fresh_set = {g for l in d["rounds"][prev_cp:a] for g in l["accepted"]}
        prev_cp = a
        for m in h["modules"]:
            for g in m["members"]:
                s, hit = truth[g]
                good = hit and (s > 0) == (m["sign"] == "+")
                tot["members"] += 1; tot["looked_up"] += g in looked; tot["fresh"] += g in fresh_set
                tot["fresh_good"] += good and g in fresh_set
                if good:
                    tot["good"] += 1; tot["good_looked_up"] += g in looked
                    continue
                tot["nonhit" if not hit else "wrongsign"] += 1
                have = rec.get(g, set())
                if any(abs(v - round(s, 4)) < 0.0015 for v in have):
                    tot["bad_known"] += 1; tot["fresh_nonhit_known"] += (not hit) and g in fresh_set
                elif have:
                    tot["bad_wrong"] += 1
                else:
                    tot["bad_absent"] += 1
        if env is not None:  # replay to this checkpoint, then grade agent (v3) and own-data reference (v3)
            while played < a:
                env.propose(d["rounds"][played]["accepted"]); env.end_round(); played += 1
            fresh = {g for l in env.log[prev:] for g in l.accepted}
            g_agent = [grade_module(env, m["members"], m["sign"], 8, denom="found", fresh=fresh) for m in h["modules"]]
            agent_v3.append(dedup_score(g_agent, 5, 8))
            ref = strategies(env, looked, np.random.default_rng(i), fresh)["nbr_hits"]
            g_ref = [grade_module(env, m["genes"], m["sign"], 8, denom="found", fresh=fresh) for m in ref]
            own_v3.append(dedup_score(g_ref, 5, 8))
            prev = a
        rows.append((a, len(rec)))
    n = tot["members"]; bad = n - tot["good"]
    out = {"run": name, "checkpoints": len(d["hypotheses"]), "members": n,
           "good": tot["good"], "bad": bad,
           "bad: non-hit": tot["nonhit"], "bad: hit, wrong sign": tot["wrongsign"],
           "bad: files had the correct score": tot["bad_known"], "bad: files had a wrong score": tot["bad_wrong"],
           "bad: no score in files": tot["bad_absent"],
           "fresh members": tot["fresh"], "fresh members good": tot["fresh_good"],
           "bad: fresh non-hit, score known": tot["fresh_nonhit_known"],
           "members looked up": tot["looked_up"], "good members looked up": tot["good_looked_up"],
           "genes with a score in files (last checkpoint)": rows[-1][1] if rows else 0,
           "tested genes (last checkpoint)": len({g for l in d["rounds"][:d["hypotheses"][-1]["after_round"]] for g in l["accepted"]})}
    if agent_v3:
        out["agent v3 score"] = round(float(np.mean(agent_v3)), 3)
        out["own-data nbr_hits v3 score"] = round(float(np.mean(own_v3)), 3)
    return out


if __name__ == "__main__":
    res = [diagnose(n) for n in sys.argv[1:]]
    print(json.dumps(res, indent=1))
