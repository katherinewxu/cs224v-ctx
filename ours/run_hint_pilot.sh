#!/bin/bash
# Hint pilot, 30x16, plain Codex only (~3% weekly): does the stated strategy change module composition?
# Compare with ours/diagnose_modules.py against hypf_base_30x16 (no hint). Scores at 30x16 don't separate strategies.
cd "$(dirname "$0")/.." || exit 1
export FEATURES=depmap HISTORY=none REPORT_EVERY=10 HYPOTHESIS_EVERY=10 REPEAT_COST=1
export HYP_FRESH=1 HYP_DENOM=found HYP_DEDUP=1 HYP_HINT=1 MAX_WEEKLY=${MAX_WEEKLY:-96}
exec ours/run_list.sh 16000 30 16 21600 hintp_base_30x16:codex-shipped
