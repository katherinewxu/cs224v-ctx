#!/bin/bash
# 100x32 grading v3 (fresh + found + dedup), seed 0: plain Codex first, then the prototype; stops above 80% weekly.
cd "$(dirname "$0")/.." || exit 1
export FEATURES=depmap HISTORY=none REPORT_EVERY=10 HYPOTHESIS_EVERY=10 REPEAT_COST=1
export HYP_FRESH=1 HYP_DENOM=found HYP_DEDUP=1 MAX_WEEKLY=80
exec ours/run_list.sh 16000 100 32 21600 v3_base_s0:codex-shipped v3_ours_s0:codex
