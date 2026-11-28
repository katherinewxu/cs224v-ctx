#!/bin/bash
# Final runs on one account, back to back (~16 h, ~87% of a weekly limit):
#   hint pair (seed 0, HYP_HINT=1), then v3 seeds 1-2 (both arms).
# MAX_WEEKLY=95 because the first usage reading comes from the last pre-reset log (93%); later runs read
# fresh values. Usage: nohup ours/run_final.sh > ours/final_list.out 2>&1 &
cd "$(dirname "$0")/.." || exit 1
export MAX_WEEKLY=${MAX_WEEKLY:-95}
ours/run_hint_s0.sh
ours/run_v3_s12.sh
