DRAFT, for Karen and Katherine to edit before sending.

Subject: CS224V context management: why compaction hasn't triggered yet, and a few questions

Hi Yucheng,

A short update before Monday's progress report, plus a few questions about the prototype.

**Why we haven't seen compaction yet.** Our BioDiscoveryAgent testbed never reaches the 48K threshold.
With the full results table in the prompt, the prompt grows about 300 tokens per round (batch 32):
4.5K at round 10, 16.7K at round 50, 31.5K at round 100. At that rate it reaches 48K only around
round 150. So far Opus with the full table shows no forgetting at all up to 31.5K (0 repeats, every
recall probe correct), which tells us about the model, not the harness.

**What we plan to do.**
1. Lower the compaction threshold to about 16-20K for a matched pilot (prototype vs. baseline, same
   model, features, task seed and budget, 30 rounds x 16 genes first). Compaction should start around
   round 50 at batch 32.
2. One run where compaction fires at the real 48K: either batch 64 (crosses around round 78) or about
   200 rounds, so the result doesn't depend only on a small window.
3. Trace every compaction event (round, size before and after) in every run.
4. We built an evaluator service so a code-capable agent only reaches the screen through an API
   (propose, lookup, history), with scores and gene names kept in a separate process.

From our own summary policy we already see a large effect: BDA-style summaries lose 26% of hits by
round 98 vs. the full table, mostly because the summaries drop which genes were tested and their
scores (the model answers 4 of 381 recall probes correctly). We're adding a control that keeps the
summary plus the exact tested-ID list to separate the two.

**Prototype status.** We have the release (pinned to 2026.11.09-166c433f). The BDA task runs through an
MCP server, so scores and gene names stay outside the agent, and every compaction is traced. Findings so far:

- *Agents script the episode.* Given one message, both the prototype and `codex-shipped` wrote a loop
  that played all rounds itself, so context never grew (10-21 model requests per 100-round run, no
  compactions). We now gate rounds: each round opens only with a random token sent in that round's
  user message, so the agent takes one turn per round.
- *Gated pilot (30 rounds x 16, `--context-window 16000`, one seed):* the prototype compacted 28 times
  and got 28 hits; the baseline compacted 23 times and got 54 hits; neither repeated a gene. But the
  baseline kept track by re-reading our history tool 41 times, which made forgetting free, so we
  removed that tool: each result is now shown once and has to survive compaction.
- *Without the history tool, the baseline forgot at first.* At 30x16 it repeated 6 genes (all in round
  29 of 30, first tested 3-28 rounds earlier); the prototype repeated none.
- *DepMap, 100 rounds x 32, 16K, history off, one seed:* we also ask every 10 rounds for the 10 tested
  genes with the largest |score|. Prototype 229 hits, baseline 212 (random about 160); the prototype repeated 16 genes in round 2 only, the baseline none; both
  100/100 report answers correct; 99 vs. 44 compactions, 12.4M vs. 5.2M input tokens. This time
  plain Codex wrote each round's results to a file in its workspace and read them back, so both arms
  had an exact memory on disk. Earlier baselines wrote no files and did forget, so this varies by run.

**Questions.**
1. **The main one: what should the comparison isolate?** The prototype's memory is files the agent
   writes itself (it appends each round's results to `data_structures/scores.jsonl` with shell
   commands), and plain Codex sometimes improvises the same thing (one file per round). When it does,
   both arms have an exact record and the memory test is saturated. When it doesn't (our earlier runs),
   it forgets. Blocking workspace writes for both arms would also switch off the prototype's own
   mechanism, so we don't think that's fair. Options we see: (a) count improvised files as fair and
   compare on tasks where a flat log isn't enough (e.g. each round needs reasoning over many past
   results, or the record outgrows what can be re-read cheaply), plus cost per hit; (b) block writes
   only for the baseline, i.e. compare against a no-file-memory Codex. Which do you want?
2. Is `--harness codex-shipped` the right baseline, i.e. the same runtime with the structured memory off?
3. Is `--context-window 16000` a reasonable setting for the pilot, or would you set it differently
   (or use `--catalog-share`)?
4. On macOS the default Codex sandbox can read the whole disk. Karen wrote a restricted seatbelt profile
   that blocks reads of the repo and task data, and we also scramble gene IDs with a secret seed and
   audit the trace. Is there a supported way to restrict reads (or a Linux build with bubblewrap)?
5. Is gating one round per user message (with `--follow-up`) a fair way to use the prototype, or is
   there a mode you'd rather we use for long multi-turn tasks?
6. Monica and you mentioned the benchmark needs to be harder for long horizons. Is ~150-200 rounds on
   this screen what you had in mind, or would you rather we add a second screen or tasks with more
   cross-round dependencies?

Thanks,
Karen and Katherine
