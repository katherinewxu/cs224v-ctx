# Harder task design (option a: agent-written files allowed)

DRAFT, Nov 15. Nothing built yet; for Karen and Katherine to agree on before any code.

## Why the current task saturates

On DepMap 100x32 with history off, both arms kept an exact record on disk (one line or one file per
round) and scored 100/100 on the top-10 report. The task only ever asks for two things a flat log
answers by lookup: "was this gene tested?" and "which tested genes scored highest?". A memory test
that a `grep` or `sort` passes measures whether the agent thinks to keep a log, not how the harness
manages context.

Also, an information-matched heuristic (`nbr` in `bio/baselines.py`: look up neighbours of the best
genes, test them) gets 221 hits (5 seeds), the same as the two LLM arms (229, 212). So the hit count
doesn't reward anything a log-keeping script couldn't do either.

## What would make files insufficient

The record must be needed in a form that has to be *built and kept up to date*, not just stored, and
the cheap way to rebuild it from the raw log must cost more than the window allows.

1. **Evolving hypotheses, scored.** Every K rounds the agent submits a short model of the screen:
   e.g. 5 "modules" (groups of tested genes it believes act together, with a predicted sign). Scoring:
   held-out genes from those modules are tested by the evaluator and the prediction is graded. A flat
   log has the data, but the hypothesis is reasoning over hundreds of results; a harness that keeps
   structured state (clusters, neighbour graph) should carry it between compactions, and a raw-log
   agent has to re-derive it each time.
2. **Delayed, conditional rewards.** Some genes are "assays": testing one reveals nothing at first,
   but a hit is credited only if a *specific related gene* (named in the reveal) is tested within the
   next N rounds. The agent has to carry a set of open obligations across compactions; files can hold
   it, but only if the agent keeps them current (stale or missing entries cost hits).
3. **Batch constraints that depend on many past scores.** Each round's batch must include, say, at
   least 8 neighbours of the agent's current top-20 hits (by |score|) and no gene within distance d of
   a tested null. The evaluator checks it. The top-20 and the null set change every round, so the
   agent has to keep a derived structure (neighbour lists of a moving top set), not just the log.
4. **Budgeted recall instead of free lookup.** Keep files, but charge the read: each exec read of a
   workspace file costs model tokens anyway; at 16K the window can't hold a 3,200-row log, so the agent
   must summarise. Measure what each arm reads per round and whether its decisions use it (from the
   trace). This turns "has a log" into "uses a compact, current summary".

## Recommendation

Start with 3 (batch constraints): it reuses the evaluator, needs one new check in `propose`, is
scored automatically (violations + hits), and directly exercises the prototype's structured state
(neighbour lists of a moving top set) versus re-deriving it from a flat log each round. 1 is the most
interesting scientifically but needs a grading design. Pilot at 30x16, then 100x32, with the
`nbr` baseline extended to satisfy the constraint as the reference.

## Open questions

- Does Yucheng want option (a) at all, or (b) (plain Codex without files)? See the email.
- Do constraint violations reject the gene (lost slot) or the whole batch?
