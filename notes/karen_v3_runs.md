# Karen: running the v3 seeds 1-2 on your account

Hi Karen! Katherine's weekly Codex limit is used up until Nov 27, and we need seeds 1-2 of the final
runs before the Dec 2 poster session. Could you run them on your account? Same model and settings
as seed 0, so the results compare directly. They take about 11 hours back to back and use roughly
55-60% of a weekly limit; one seed per arm (`v3_base_s1` + `v3_ours_s1`) is about 30% if that's
all you have.

## What these runs are
100 rounds x 32 genes, 16K window, one turn per round, history off, DepMap lookups, repeats cost a
slot, and graded hypotheses every 10 rounds with the three new rules (all explained to the agent in
its task text):
- **fresh**: a module scores only if it has a gene tested since the last checkpoint;
- **found**: graded on the held-out genes actually in its members' neighbour lists;
- **dedup**: each held-out gene counts once per checkpoint, so copies of one module add nothing.
Background and offline references: `bio/RESULTS.md`, last three sections.

## Setup (once)
1. `git pull` on `main` of kkarenvoo05/cs224v-ctx (needs commit 2705a56 or later).
2. Prototype installed at `~/.ours/bin/ours`, logged in with your ChatGPT account (as for your
   Nov 10-13 runs).
3. `ours/model_info/gpt-6.1-terra.json`: Katherine will send you this file (model settings only, no
   credentials; not in git because it comes from the release). Put it at that path.
4. `bio/.venv` and `data/depmap/achilles.csv` (README steps 1 and 4). Check:
   `bio/.venv/bin/python -m pytest -q bio/test_evaluator.py` should print 18 passed.

## Run
From the repo root:
```
nohup ours/run_v3_s12.sh > ours/v3_s12_list.out 2>&1 &
```
It checks the setup first and prints what's missing. Order: plain Codex s1, prototype s1, plain
Codex s2, prototype s2. Progress is in `ours/v3_s12_list.out` (one line per run) and
`ours/<name>.log`.

**Usage guard:** before each run it reads your weekly usage from the newest run log and stops if it
is above 80%. If you have old runs in `ours/runs/`, the first reading can be stale (it once read
100% right after a reset). If it stops immediately and your real usage is low, start it with
`MAX_WEEKLY=95 nohup ours/run_v3_s12.sh ...` instead. A run that's already started is not stopped,
so a prototype run (about 15%) started near the limit can run out before round 100.

Keep the laptop awake and plugged in (e.g. `caffeinate -i` in another terminal).

## Send back
Zip these and send them to Katherine directly (not to GitHub or a public link; the release isn't
for redistribution):
- `ours/evals/v3_*_s1`, `ours/evals/v3_*_s2` (evaluator logs, small)
- `ours/runs/v3_*_s1-*`, `ours/runs/v3_*_s2-*` (traces), without any `codex_home` folders
- `ours/v3_s12_list.out` and `ours/runs.log`

Katherine will audit them, run `ours/compare.py`, and fill in the poster and paper tables.

Thank you!
