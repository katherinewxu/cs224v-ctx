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

## 4. Finding 2: the prototype finds somewhat more hits, at about 2x the cost (middle column)
[figure: `figs/hits_100x32.svg`]

| 100x32, 4 runs | hits | repeats | input tokens / run | wall time |
|---|---|---|---|---|
| prototype | 198* / 215 / 218 / 194 (mean 206) | 28 / 3 / 3 / 2 | 21-24M | about 3.5 h |
| plain Codex | 188 / 185 / 189 / 205 (mean 192) | 161 / 4 / 195 / 18 | 11-12M | about 1.6 h |

+14.5 hits (+8%) for 2x tokens; the ranges overlap (permutation p = 0.07, one-sided). The 4th run of
each arm is v3 seed 0 (same settings, final grading rules).
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

## 6b. Why are hypothesis scores low? Not memory: reasoning (right column)
[figure: `figs/diagnosis_modules.svg`]

- Checked every module member against the truth and against the agent's own files at that moment: in
  7 of 8 runs, **every** bad member's correct score was already in the agent's files.
- Most bad members under v3 are **newly tested genes the agent knew were not hits** (55 of 83 for the
  prototype, 90 of 132 for plain Codex): the rule needs one new gene per module; both agents filled
  modules with new genes.
- Given **exactly the agents' own data**, simple neighbour grouping scores 0.095 / 0.100, about 2x
  the agents (0.048 / 0.055).
- After compaction, the prototype re-read its memory files every time (666 of 668, within 2 tool
  calls; its summary lists its files). Plain Codex did so after 68-98% of compactions. Its repeats
  build up over the run rather than spiking at compactions: forgetting is cumulative.

## 7. Takeaways (right column, bottom)
- **Memory matters when the agent can't or doesn't write it down.** The prototype's structured
  files kept the tested set exact in every run; plain Codex's record depended on whether it chose to
  keep files.
- **The prototype's edge in hits is small and uncertain:** +14 hits per run on average over 4 runs,
  and the ranges overlap; hypothesis scores tie.
- **The bottleneck has moved from memory to reasoning.** Both agents had the facts; neither used
  them as well as a two-line grouping rule.
- **Long-horizon benchmarks must be adversarially graded.** Both agents found shortcuts (frozen
  answers, duplicates) within one pilot. Offline strategies (random, copy, freeze) are cheap checks.
- **Cost:** about 2x tokens and wall time for the prototype.

## 60-second talk (one slide: the repeats figure + one line on the grading story)
"Long-horizon agents have to compact their context. We asked whether a harness with structured
external memory beats plain Codex on a 100-round gene screen where each result is shown once. When
plain Codex doesn't keep files, it forgets what it already tested and wastes hundreds of experiments,
while the prototype stays exact, at twice the cost. Our second finding
is about measurement: when we asked the agents for hypotheses, they found shortcuts, like copying one
answer five times, so we made the grader adversarial. Come see how each fix changed the scores."
