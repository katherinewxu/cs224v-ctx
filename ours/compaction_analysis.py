"""What happens after a compaction? (no model calls)

From each run's Codex session log (harness/codex_home/sessions), in order: compaction events, tool calls
and round boundaries (end_round calls). For every compaction:
  - how many tool calls until the agent reads its memory (a workspace data file, or the JS store via load())
  - whether it proposed genes before reading its memory ("proposed blind")
And per round (run.json): repeats in rounds with a compaction vs rounds without.

The prototype's compaction summary is plain text and lists its data_structures catalog; plain Codex's
is an encrypted server-side summary plus retained messages, so only behaviour can be compared.

    bio/.venv/bin/python -I ours/compaction_analysis.py v3_ours_s0 v3_base_s0 nf_base_s0 ...
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = re.compile(r"data_structures|\.jsonl?\b|screen_state|all_scores|round_?\d+|records?/|\.csv\b|\.txt\b")
READ = re.compile(r"\bcat\b|\bhead\b|\btail\b|\bjq\b|\bgrep\b|\bsed\b|\bawk\b|\bwc\b|open\(|readFile|json\.load|"
                  r"JSON\.parse|\bload\(|read_text|readlines|\bless\b|python")


def events(rd):
    for f in sorted(rd.glob("harness/codex_home/sessions/**/*.jsonl")):
        for line in f.read_text().splitlines():
            x = json.loads(line)
            p = x.get("payload") if isinstance(x.get("payload"), dict) else {}
            if x.get("type") == "compacted":
                yield "compact", ""
            elif x.get("type") == "response_item" and p.get("type") in ("custom_tool_call", "function_call"):
                text = json.dumps(p.get("input") or p.get("arguments") or "")
                name = p.get("name", "")
                if "end_round" in name or "mcp__bda__end_round" in text:
                    yield "end_round", text
                elif "propose" in name or "mcp__bda__propose" in text:
                    yield "propose", text
                elif DATA.search(text) and READ.search(text) or re.search(r"\bload\(", text):
                    yield "read", text
                else:
                    yield "other", text


def analyse(name):
    rd = sorted((ROOT / "ours/runs").glob(f"{name}-*"))[-1]
    rounds = json.loads((ROOT / "ours/evals" / name / "run.json").read_text())["rounds"]
    ev = list(events(rd))
    done, comp_rounds, after = 0, [], []
    for i, (kind, _) in enumerate(ev):
        if kind == "end_round":
            done += 1
        elif kind == "compact":
            comp_rounds.append(done + 1)
            n, blind, read = 0, False, None
            for k2, _ in ev[i + 1:]:
                if k2 == "compact":
                    break
                n += 1
                if k2 == "read":
                    read = n; break
                if k2 == "propose":
                    blind = True
            after.append((read, blind))
    reads = [r for r, _ in after if r is not None]
    reps = [len(r.get("repeats", [])) for r in rounds]
    with_c = {r for r in comp_rounds if r <= len(rounds)}
    rc = [reps[r - 1] for r in sorted(with_c)]; rn = [reps[i] for i in range(len(reps)) if i + 1 not in with_c]
    mean = lambda v: round(sum(v) / len(v), 2) if v else None
    return {"run": name, "rounds": len(rounds), "compactions": len(comp_rounds),
            "rounds with a compaction": len(with_c),
            "memory read before next compaction": f"{len(reads)}/{len(after)}",
            "median calls to first memory read": sorted(reads)[len(reads) // 2] if reads else None,
            "proposed before reading memory": sum(b for _, b in after),
            "repeats": sum(reps),
            "repeats per round, rounds with compaction": mean(rc),
            "repeats per round, rounds without": mean(rn)}


if __name__ == "__main__":
    res = [analyse(n) for n in sys.argv[1:]]
    keys = list(res[0])
    print("| " + " | ".join(keys) + " |"); print("|" + "---|" * len(keys))
    for r in res:
        print("| " + " | ".join(str(r[k]) for k in keys) + " |")
