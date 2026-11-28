#!/bin/bash
# Hint ablation: v3 grading plus a stated grouping strategy (HYP_HINT=1), seed 0, both arms; stops above 80% weekly.
cd "$(dirname "$0")/.." || exit 1
export FEATURES=depmap HISTORY=none REPORT_EVERY=10 HYPOTHESIS_EVERY=10 REPEAT_COST=1
export HYP_FRESH=1 HYP_DENOM=found HYP_DEDUP=1 HYP_HINT=1 MAX_WEEKLY=${MAX_WEEKLY:-80}
exec ours/run_list.sh 16000 100 32 21600 hint_base_s0:codex-shipped hint_ours_s0:codex
