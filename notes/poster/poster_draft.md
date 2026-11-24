# Poster draft: CS224V poster session, Wed Dec 2

Layout suggestion (landscape, 3 columns, CS 224N guidelines): left = question + setup, middle = what
memory buys (hits, repeats), right = the grading story + v3 results + takeaways. Figures in `figs/`
(SVG, regenerate with `python3 -I notes/poster/make_figs.py` from the repo root).

**[TODO before printing]** v3 numbers (seed 0 running Nov 23, seeds 1-2 after the Nov 27 reset);
Yucheng's OK on how we describe the prototype; team/mentor names and logos.

---

## Title
**Does Structured Context Management Help Long-Horizon Agents? A 100-Round Gene-Screen Test**

Katherine Xu, Karen Vo · Mentor: Yucheng Jiang · CS 224V, Fall 2026

## 1. Question (left column, top)
Long-horizon agents outgrow their context window and must compact. Does a harness that manages
context with structured external memory (the prototype) beat plain Codex, which compacts and relies
on whatever notes it decides to keep?

- Same model, same tools, same task; only the harness differs.
- We built a testbed where forgetting has a measurable cost.

## 2. Testbed (left column)
Closed-loop CRISPR screen from BioDiscoveryAgent (IFNG, 18,418 genes, about 920 hits, gene names
anonymized).
- **100 rounds x 32 genes.** Each round: look up 8 DepMap neighbours for up to 4 genes, propose 32
  untested genes, see their scores once.
- **One model turn per round**, enforced by a hashed round token (no script can play ahead).
- **16K context window**, so compaction fires every 1-2 rounds. **History tool off**: results are
  shown once; the agent must keep its own record.
- **Repeats cost a slot**: re-proposing a tested gene wastes an experiment.
- **Isolation**: agents can't reach the evaluator, data or seed; every trace is audited.

Measures: hits; repeats; a top-10 recall probe every 10 rounds; graded hypotheses (section 5).

## 3. Finding 1: without files, plain Codex forgets what it tested (middle column)
[figure: `figs/repeats_100x32.svg`]

- Told not to write files, plain Codex re-proposed **811 and 1,167** already-tested genes (2 seeds),
  yet still named its top 10 correctly at every probe: it kept the short list, lost the long one.
- With repeats costing a slot, its hits fall from 211/215 to **180/176**. The prototype: 16, 0, 0
  repeats; hits unchanged.
- Allowed to write files, plain Codex usually keeps its own exact record (0 repeats in one seed),
  but not always (161 and 195 repeats in two later seeds despite 120+ files).

## 4. Finding 2: the prototype finds more hits, at about 2x the cost (middle column)
[figure: `figs/hits_100x32.svg`]

| 100x32, 3 seeds | hits | repeats | input tokens / run |
|---|---|---|---|
| prototype | 198* / 215 / 218 (mean 210) | 28 / 3 / 3 | 21-24M |
| plain Codex | 188 / 185 / 189 (mean 187) | 161 / 4 / 195 | 11-12M |

\* stopped at round 99 on the usage limit. A no-LLM heuristic with the same lookups gets about 221
hits, so hits alone are an easy target: the task needs more than a flat log to separate memory
designs.

## 5. Finding 3: agents game the grader; three fixes (right column)
To require reasoning over the whole history, every 10 rounds the agent submits 5 "modules" (3-10
tested genes + a predicted sign). Each is graded on held-out genes (15% of genes never testable) that
are most frequent in its members' neighbour lists.

What the agents did, and the fix:
1. **Froze their modules** after about round 30 → **fresh**: a module scores only if it has a gene
   tested since the last checkpoint.
2. Scores capped by **missing held-out genes** → **found**: grade on the held-out genes actually found.
3. Plain Codex then **submitted one module 5 times** (0.50 vs 0.03) → **each held-out gene counts once**.

[figure: `figs/grading_rules.svg`] [figure: `figs/pilot_dedup.svg`]

Under the final rules, copying scores like random (0.019 vs 0.017), freezing scores 0.006, and
grouping hits by shared neighbours scores 0.106, 6x random.

## 6. Results under the final rules (right column) **[TODO: fill after seeds 1-2]**

| 100x32, v3 rules | hits | hypothesis score | repeats | tokens |
|---|---|---|---|---|
| prototype | s0: 194 | s0: 0.048 | s0: 2 | s0: 23.8M |
| plain Codex | s0: 205 | s0: 0.055 | s0: 18 | s0: 12.0M |
| offline references | – | neighbours 0.106 · hit groups 0.067 · random 0.017 | | |

## 7. Takeaways (right column, bottom)
- **Memory matters when the agent can't or doesn't write it down.** The prototype's structured
  files kept the tested set exact in every run; plain Codex's record depended on whether it chose to
  keep files.
- **The prototype's edge is in hits, not reasoning (so far):** +23 hits per run on average; hypothesis
  scores tie under the original grading.
- **Long-horizon benchmarks must be adversarially graded.** Both agents found shortcuts (frozen
  answers, duplicates) within one pilot. Offline strategies (random, copy, freeze) are cheap checks.
- **Cost:** about 2x tokens and wall time for the prototype.

## 60-second talk (one slide: the repeats figure + one line on the grading story)
"Long-horizon agents have to compact their context. We asked whether a harness with structured
external memory beats plain Codex on a 100-round gene screen where each result is shown once. When
plain Codex doesn't keep files, it forgets what it already tested and wastes hundreds of experiments,
while the prototype stays exact and finds about 12% more hits, at twice the cost. Our second finding
is about measurement: when we asked the agents for hypotheses, they found shortcuts, like copying one
answer five times, so we made the grader adversarial. Come see how each fix changed the scores."
