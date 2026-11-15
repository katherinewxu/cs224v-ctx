"""Evaluator-owned BDA service for code-capable agents (e.g. the prototype harness).

The agent never gets the screen files, hit labels or the ID-to-symbol mapping: those stay
in this process. It talks to the service over HTTP on 127.0.0.1 (or with eval_client.py)
and can only:

    POST /propose   {"ids": [...]}  submit genes for the current round (limited calls/round)
    POST /end_round {}              close the round; returns scores + hit flags of accepted genes
    POST /lookup    {"ids": [...]}  similar genes (up to --lookups IDs per round)
    GET  /history                   results already observed (--history full: all; last: the last
                                    closed round only; none: disabled, so results are seen once)
    POST /report    {"ids": [...]}  (--report-every K) after every K-th and the last round: name the
                                    tested genes with the largest |score| so far; scored, not revealed
    GET  /status                    round, batch, remaining budget
    GET  /help                      the text above, for the agent's instructions

Scores are revealed only at /end_round, as in llm_agent.py (the agent learns them next round).
Every request and response is appended to OUT/requests.jsonl; OUT/run.json is rewritten
atomically after each round with the same totals/curve fields as llm_agent.py, plus an
independent analyze.py-style recount.

Isolation: this only keeps hidden state out of the API. Run the agent in a folder that does
not contain this repo or the data (and check it can't read them) before trusting results.

Usage:
    bio/.venv/bin/python -I bio/evaluator.py --screen IFNG --rounds 30 --batch 16 --anonymize \
        --features depmap --seed 0 --port 8765 --out bio/runs/eval_NAME
"""
import argparse
import hashlib
import json
import os
import sys
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env import BioEnv  # noqa: E402

HISTORY_MODES = ("full", "last", "none")
HELP = __doc__.split("Scores are revealed")[0].strip()


class RoundGate:
    """One model turn per round: round k opens only with the token sent in that round's user message.
    Only sha256 hashes are held, so a script written in an earlier turn cannot open later rounds."""

    def __init__(self, hashes: list[str]):
        self.hashes, self.opened = hashes, set()

    def check(self, round_1based: int, token) -> str | None:
        if round_1based in self.opened:
            return None
        h = self.hashes[round_1based - 1] if round_1based <= len(self.hashes) else None
        if token is None or h is None or hashlib.sha256(str(token).encode()).hexdigest() != h:
            return (f"round {round_1based} is not open: pass the round_token given in the user message for "
                    f"round {round_1based}. If you have not received it yet, stop and wait for the next message.")
        self.opened.add(round_1based)
        return None


class Evaluator:
    def __init__(self, env: BioEnv, out: Path, proposals_per_round: int = 3, lookups_per_round: int = 4,
                 gate: RoundGate | None = None, history_mode: str = "full", report_every: int = 0,
                 report_n: int = 10):
        if history_mode not in HISTORY_MODES:
            raise ValueError(f"history_mode must be one of {HISTORY_MODES}")
        self.gate, self.history_mode = gate, history_mode
        # Score-memory probe: after every report_every-th round (and the last), the agent must name the
        # report_n tested genes with the largest |score| before it may propose again. Needs exact scores
        # from early rounds, so a memory that keeps only the tested set loses points here.
        self.report_every, self.report_n = report_every, report_n
        self.report_due: int | None = None
        self.reports: list[dict] = []
        self.on_done = None
        self.env, self.out = env, Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        if (self.out / "requests.jsonl").exists() or (self.out / "run.json").exists():
            raise FileExistsError(f"Evaluator output already exists: {self.out}; choose a new --out")
        self.max_props, self.max_lookups = proposals_per_round, lookups_per_round
        self.props_used = self.lookups_used = 0
        self.lock = threading.Lock()
        self.n_requests = 0
        self.t0 = time.time()
        self._save()

    # ---- API ----------------------------------------------------------------
    def status(self) -> dict:
        e = self.env
        return {"round": e.round + 1 if not e.done else None, "rounds_total": e.rounds, "done": e.done,
                "batch": e.batch, "remaining_in_batch": None if e.done else e.remaining_in_batch(),
                "proposals_left": self.max_props - self.props_used,
                "lookups_left": self.max_lookups - self.lookups_used, "n_genes": len(e.ids),
                "tested": len(e.tested), "cum_hits": e.log[-1].cum_hits if e.log else 0,
                "history": self.history_mode, "report_due": self.report_due}

    def propose(self, ids, token=None) -> dict:
        e = self.env
        if e.done:
            return {"error": "episode finished"}
        if self.gate and (err := self.gate.check(e.round + 1, token)):
            return {"error": err}
        if self.report_due is not None:
            return {"error": f"report due for round {self.report_due}: call report first"}
        if self.props_used >= self.max_props:
            return {"error": f"proposal limit ({self.max_props}) reached for this round; call /end_round"}
        if not isinstance(ids, list) or len(ids) > 4 * e.batch:
            return {"error": f"ids must be a list of at most {4 * e.batch} IDs"}
        self.props_used += 1
        cur = e._cur
        before = {k: len(getattr(cur, k)) for k in ("accepted", "invalid", "repeats", "dup_in_batch", "overflow")}
        e.propose([str(g) for g in ids])
        new = {k: getattr(cur, k)[before[k]:] for k in before}
        return {"round": e.round + 1, "accepted": new["accepted"],
                "rejected": {"invalid": new["invalid"], "already_tested": new["repeats"],
                             "duplicate": new["dup_in_batch"], "over_batch": new["overflow"]},
                "remaining_in_batch": e.remaining_in_batch(), "proposals_left": self.max_props - self.props_used}

    def end_round(self) -> dict:
        e = self.env
        if e.done:
            return {"error": "episode finished"}
        log = e.end_round()
        self.props_used = self.lookups_used = 0
        self._save()
        if e.done and self.on_done:
            self.on_done()
        out = {"round": log.round + 1, "results": [{"id": g, "score": round(log.revealed[g], 4),
                                                    "hit": g in log.hits} for g in log.accepted],
               "short_by": e.batch - len(log.accepted), "cum_hits": log.cum_hits, "rounds_left": e.rounds - e.round}
        if self.report_every and ((log.round + 1) % self.report_every == 0 or e.done):
            self.report_due = log.round + 1
            out["report_due"] = (f"Before anything else, call report with the {self.report_n} genes you have "
                                 f"tested whose |score| is largest so far (from your own records).")
        if self.gate and not e.done:
            out["next"] = "Round closed. Stop here and end your turn; the next user message gives the next round's token."
        return out

    def lookup(self, ids) -> dict:
        if not isinstance(ids, list):
            return {"error": "ids must be a list"}
        left = self.max_lookups - self.lookups_used
        ids = [str(g) for g in ids][:left]
        self.lookups_used += len(ids)
        return {"neighbors": {g: [h for h, _ in self.env.lookup(g)] for g in ids},
                "lookups_left": self.max_lookups - self.lookups_used}

    def report(self, ids) -> dict:
        if self.report_due is None:
            return {"error": "no report is due now"}
        if not isinstance(ids, list):
            return {"error": "ids must be a list"}
        e, n = self.env, self.report_n
        scores = {g: abs(v) for l in e.log for g, v in l.revealed.items() if g in l.accepted}
        cut = sorted(scores.values(), reverse=True)[min(n, len(scores)) - 1] if scores else 0.0
        named = list(dict.fromkeys(str(g) for g in ids))[:n]
        correct = sum(1 for g in named if g in scores and scores[g] >= cut)  # ties at the cut count
        rec = {"after_round": self.report_due, "n": n, "correct": correct,
               "untested": sum(1 for g in named if g not in scores), "named": named}
        self.reports.append(rec)
        self.report_due = None
        self._save()
        return {"recorded": True, "after_round": rec["after_round"], "named": len(named)}

    def history(self) -> dict:
        e = self.env
        if self.history_mode == "none":
            return {"error": "history is disabled in this run: each result is shown once, in end_round's reply"}
        logs = e.log[-1:] if self.history_mode == "last" else e.log
        return {"results": [{"round": l.round + 1, "id": g, "score": round(l.revealed[g], 4), "hit": g in l.hits}
                            for l in logs for g in l.accepted]}

    # ---- bookkeeping --------------------------------------------------------
    def record(self, method: str, path: str, body, resp: dict) -> None:
        self.n_requests += 1
        with open(self.out / "requests.jsonl", "a") as f:
            f.write(json.dumps({"i": self.n_requests, "t": round(time.time() - self.t0, 2), "round": self.env.round,
                                "method": method, "path": path, "body": body, "response": resp}) + "\n")

    def _save(self) -> None:
        e = self.env
        res = {"status": "complete" if e.done else "partial", "n_requests": self.n_requests,
               "wall_s": round(time.time() - self.t0, 1), "totals": e.totals(),
               "hit_ratio_recount": e.hit_ratio_by_analyze() if e.log else 0.0,
               "curve": [l.hit_ratio for l in e.log], "reports": self.reports,
               "report_score": (sum(r["correct"] for r in self.reports) / (self.report_n * len(self.reports))
                                if self.reports else None), "rounds": [asdict(l) for l in e.log], "tested": e.tested}
        tmp = self.out / "run.json.tmp"
        tmp.write_text(json.dumps(res))
        tmp.replace(self.out / "run.json")

    def handle(self, method: str, path: str, body) -> tuple[int, dict]:
        with self.lock:
            routes = {("GET", "/status"): lambda: self.status(), ("GET", "/history"): lambda: self.history(),
                      ("GET", "/help"): lambda: {"help": HELP},
                      ("POST", "/propose"): lambda: self.propose((body or {}).get("ids"), (body or {}).get("round_token")),
                      ("POST", "/end_round"): lambda: self.end_round(),
                      ("POST", "/lookup"): lambda: self.lookup((body or {}).get("ids")),
                      ("POST", "/report"): lambda: self.report((body or {}).get("ids"))}
            fn = routes.get((method, path))
            resp = fn() if fn else {"error": f"unknown endpoint {method} {path}"}
            code = 404 if not fn else 400 if "error" in resp else 200
            self.record(method, path, body, resp)
            return code, resp


def make_server(ev: Evaluator, port: int = 0) -> HTTPServer:
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(*ev.handle("GET", self.path, None))

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 1_000_000:
                return self._send(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "body must be JSON"})
            self._send(*ev.handle("POST", self.path, body))

        def log_message(self, *a):
            pass

    return HTTPServer(("127.0.0.1", port), H)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--screen", default="IFNG")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--anonymize", action="store_true")
    ap.add_argument("--features", choices=["screens", "depmap"], default="screens")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--proposals-per-round", type=int, default=3, help="first proposal + retries")
    ap.add_argument("--lookups", type=int, default=4, help="lookup IDs per round")
    ap.add_argument("--port", type=int, default=8765, help="0 = any free port (written to OUT/port)")
    ap.add_argument("--secret-seed", action="store_true",
                    help="random ID-anonymization seed kept in memory; only its sha256 is written until the end")
    ap.add_argument("--round-token-hashes", default="", help="comma-separated sha256 per round: gate rounds on tokens")
    ap.add_argument("--history", choices=HISTORY_MODES, default="full",
                    help="full: /history returns every result; last: only the last closed round; none: disabled "
                         "(the agent must keep its own record, so memory survives compaction or it doesn't)")
    ap.add_argument("--report-every", type=int, default=0, help="score-memory probe every K rounds (0 = off)")
    ap.add_argument("--report-n", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    seed = int.from_bytes(os.urandom(4), "big") if a.secret_seed else a.seed
    env = BioEnv(a.screen, rounds=a.rounds, batch=a.batch, anonymize=a.anonymize, seed=seed, features=a.features)
    gate = RoundGate([h for h in a.round_token_hashes.split(",") if h]) if a.round_token_hashes else None
    ev = Evaluator(env, a.out, a.proposals_per_round, a.lookups, gate, a.history, a.report_every, a.report_n)
    out = Path(a.out)
    (out / "config.json").write_text(json.dumps(vars(a)))
    if a.secret_seed:
        (out / "seed_sha256.txt").write_text(hashlib.sha256(str(seed).encode()).hexdigest() + "\n")
    srv = make_server(ev, a.port)
    (out / "port").write_text(str(srv.server_address[1]))
    print(f"evaluator on http://127.0.0.1:{srv.server_address[1]}  ({len(env.ids)} genes, {a.rounds}x{a.batch})",
          flush=True)
    if a.secret_seed:
        ev.on_done = lambda: (out / "seed_revealed.txt").write_text(f"{seed}\n")
    try:
        srv.serve_forever()  # the launcher stops it
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
