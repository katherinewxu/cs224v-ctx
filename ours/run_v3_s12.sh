#!/bin/bash
# 100x32 grading v3 (fresh + found + dedup), seeds 1 and 2: plain Codex then prototype, per seed.
# Same settings as run_v3_s0.sh. Before each run, stops if the weekly Codex usage of the logged-in
# account is above MAX_WEEKLY (default 80); the guard does not stop a run already started.
#   nohup ours/run_v3_s12.sh > ours/v3_s12_list.out 2>&1 &      (from the repo root)
# SEEDS picks which seeds to run (default "1 2"); run_final.sh's call runs seed 1 only (see below).
# Seeds are secret per run (the evaluator draws one and writes it to seed_revealed.txt at the end);
# "s1"/"s2" are just names.
cd "$(dirname "$0")/.." || exit 1
[ -x ~/.ours/bin/ours ] || { echo "missing ~/.ours/bin/ours (install the prototype release)"; exit 1; }
[ -f ours/model_info/gpt-6.1-terra.json ] || { echo "missing ours/model_info/gpt-6.1-terra.json"; exit 1; }
[ -f data/depmap/achilles.csv ] || { echo "missing data/depmap/achilles.csv (README step 4)"; exit 1; }
[ -x bio/.venv/bin/python ] || { echo "missing bio/.venv (README step 1)"; exit 1; }
export FEATURES=depmap HISTORY=none REPORT_EVERY=10 HYPOTHESIS_EVERY=10 REPEAT_COST=1
export HYP_FRESH=1 HYP_DENOM=found HYP_DEDUP=1 MAX_WEEKLY=${MAX_WEEKLY:-80}
# Nov 28: called from run_final.sh (MAX_WEEKLY=95 set there) only seed 1 fits in the remaining quota.
[ -z "$SEEDS" ] && [ "$MAX_WEEKLY" = 95 ] && SEEDS=1
LIST=(); for k in ${SEEDS:-1 2}; do LIST+=("v3_base_s$k:codex-shipped" "v3_ours_s$k:codex"); done
exec ours/run_list.sh 16000 100 32 21600 "${LIST[@]}"
