"""Poster figures as plain SVG (no plotting library). Run from the repo root:
    python3 -I notes/poster/make_figs.py
Reads ours/evals/<run>/run.json; strategy numbers are from bio/hypothesis_baselines.py (5 seeds, Nov 23)."""
import json
from pathlib import Path

OUT = Path("notes/poster/figs")
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FONT = "font-family='Helvetica, Arial, sans-serif'"


def runs(name):
    return json.load(open(f"ours/evals/{name}/run.json"))["rounds"]


class Svg:
    def __init__(s, w, h):
        s.w, s.h, s.el = w, h, [f"<rect width='{w}' height='{h}' fill='{BG}'/>"]

    def text(s, x, y, t, size=15, color=INK, anchor="start", weight="normal"):
        s.el.append(f"<text x='{x:.1f}' y='{y:.1f}' {FONT} font-size='{size}' fill='{color}' "
                    f"text-anchor='{anchor}' font-weight='{weight}'>{t}</text>")

    def line(s, x1, y1, x2, y2, color=GRID, width=1, dash=None):
        d = f" stroke-dasharray='{dash}'" if dash else ""
        s.el.append(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{color}' stroke-width='{width}'{d}/>")

    def path(s, pts, color, width=2, dash=None, opacity=1):
        d = f" stroke-dasharray='{dash}'" if dash else ""
        p = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        s.el.append(f"<path d='{p}' fill='none' stroke='{color}' stroke-width='{width}' stroke-opacity='{opacity}' "
                    f"stroke-linejoin='round' stroke-linecap='round'{d}/>")

    def bar(s, x, y0, w, y1, color):  # rounded top only, anchored to baseline y0
        r = min(4, w / 2, abs(y0 - y1))
        s.el.append(f"<path d='M{x:.1f},{y0:.1f} V{y1 + r:.1f} Q{x:.1f},{y1:.1f} {x + r:.1f},{y1:.1f} H{x + w - r:.1f} "
                    f"Q{x + w:.1f},{y1:.1f} {x + w:.1f},{y1 + r:.1f} V{y0:.1f} Z' fill='{color}'/>")

    def swatch(s, x, y, color, label, dash=None):
        s.line(x, y - 5, x + 26, y - 5, color, 3, dash); s.text(x + 34, y, label, 14, INK2)

    def save(s, name):
        (OUT / name).write_text(f"<svg xmlns='http://www.w3.org/2000/svg' width='{s.w}' height='{s.h}' "
                                f"viewBox='0 0 {s.w} {s.h}'>" + "".join(s.el) + "</svg>\n")


def axes(s, L, T, R, B, xmax, ymax, xstep, ystep, xlabel, ylabel, fmt=str):
    sx = lambda v: L + (R - L) * v / xmax
    sy = lambda v: B - (B - T) * v / ymax
    v = 0
    while v <= ymax + 1e-9:
        s.line(L, sy(v), R, sy(v)); s.text(L - 8, sy(v) + 5, fmt(v), 13, INK2, "end"); v += ystep
    v = 0
    while v <= xmax + 1e-9:
        s.text(sx(v), B + 20, fmt(v) if fmt is str else str(int(v)), 13, INK2, "middle"); v += xstep
    s.line(L, B, R, B, INK2, 1)
    s.text((L + R) / 2, B + 44, xlabel, 14, INK2, "middle")
    s.text(L - 52, (T + B) / 2, ylabel, 14, INK2, "middle")
    s.el[-1] = s.el[-1].replace("<text ", f"<text transform='rotate(-90 {L - 52} {(T + B) / 2})' ", 1)
    return sx, sy


def fig_hits():
    s = Svg(800, 470); L, T, R, B = 80, 60, 600, 370
    s.text(20, 30, "Cumulative hits, 100 rounds x 32 genes (4 runs per arm)", 18, weight="bold")
    sx, sy = axes(s, L, T, R, B, 100, 250, 20, 50, "round", "hits found")
    ends = {}
    for arm, color in (("base", ORANGE), ("ours", BLUE)):
        for name in [f"hyp_{arm}_s{k}" for k in range(3)] + [f"v3_{arm}_s0"]:
            r = runs(name)
            s.path([(sx(0), sy(0))] + [(sx(i + 1), sy(x["cum_hits"])) for i, x in enumerate(r)], color, 2, opacity=0.9)
            ends.setdefault(arm, []).append(r[-1]["cum_hits"])
    s.text(R + 8, sy(sum(ends["ours"]) / len(ends["ours"])) + 5, f"prototype {min(ends['ours'])}-{max(ends['ours'])}", 14, INK)
    s.text(R + 8, sy(sum(ends["base"]) / len(ends["base"])) + 22, f"plain Codex {min(ends['base'])}-{max(ends['base'])}", 14, INK)
    s.swatch(L, 455, BLUE, "prototype (Codex + structured context)"); s.swatch(L + 360, 455, ORANGE, "plain Codex")
    s.save("hits_100x32.svg")


def fig_repeats():
    s = Svg(800, 470); L, T, R, B = 80, 60, 600, 370
    s.text(20, 30, "Already-tested genes re-proposed (cumulative), 100x32", 18, weight="bold")
    sx, sy = axes(s, L, T, R, B, 100, 1200, 20, 300, "round", "repeats")
    for name, color, dash, lab in (("nf_base_s1", ORANGE, None, "plain Codex, no files (s1)"),
                                   ("nf_base_s0", ORANGE, "6 4", "plain Codex, no files (s0)"),
                                   ("dm_base_s0", ORANGE, "2 4", None),
                                   ("dm_ours_s0", BLUE, None, None), ("dm_ours_s1", BLUE, None, None),
                                   ("dm_ours_s2", BLUE, None, None)):
        r, c, pts = runs(name), 0, [(sx(0), sy(0))]
        for i, x in enumerate(r):
            c += len(x["repeats"]); pts.append((sx(i + 1), sy(c)))
        s.path(pts, color, 2, dash)
        if lab:
            s.text(R + 8, pts[-1][1] + 5, f"{c:,}", 14, INK)
    s.text(R + 8, sy(0) - 6, "prototype: 16, 0, 0", 13, INK2)
    s.swatch(L, 455, ORANGE, "plain Codex, no files (solid s1, dashed s0); dotted: files allowed")
    s.swatch(L + 520, 455, BLUE, "prototype (3 seeds)")
    s.save("repeats_100x32.svg")


STRATS = ["random", "hits grouped\nat random", "hits grouped\nby neighbours", "one module\ncopied 5x", "frozen after\ncheckpoint 1"]
GRADES = [("v1: original", BLUE, [0.021, 0.108, 0.155, 0.098, 0.090]),
          ("v2: + fresh, found", ORANGE, [0.027, 0.114, 0.218, 0.148, 0.012]),
          ("v3: + each gene once", AQUA, [0.017, 0.067, 0.106, 0.019, 0.006])]


def fig_grading():
    s = Svg(780, 470); L, T, R, B = 80, 60, 760, 360
    s.text(20, 30, "Offline strategies under three grading rules (no LLM, 100x32, 5 seeds)", 18, weight="bold")
    sy = lambda v: B - (B - T) * v / 0.25
    for k in range(6):
        v = k * 0.05; s.line(L, sy(v), R, sy(v)); s.text(L - 8, sy(v) + 5, f"{v:.2f}", 13, INK2, "end")
    s.line(L, B, R, B, INK2)
    gw = (R - L) / len(STRATS); bw = (gw - 30) / 3
    for i, lab in enumerate(STRATS):
        x0 = L + i * gw + 15
        for j, (_, color, vals) in enumerate(GRADES):
            x = x0 + j * bw; s.bar(x + 1, B, bw - 2, sy(vals[i]), color)
            if vals[i] >= 0.1 or j == 2:
                s.text(x + bw / 2, sy(vals[i]) - 6, f"{vals[i]:.2f}".lstrip("0"), 12, INK2, "middle")
        for k, part in enumerate(lab.split("\n")):
            s.text(L + i * gw + gw / 2, B + 22 + 17 * k, part, 14, INK, "middle")
    s.text(L - 56, (T + B) / 2, "hypothesis score", 14, INK2, "middle")
    s.el[-1] = s.el[-1].replace("<text ", f"<text transform='rotate(-90 {L - 56} {(T + B) / 2})' ", 1)
    for j, (lab, color, _) in enumerate(GRADES):
        s.swatch(L + j * 230, 450, color, lab)
    s.save("grading_rules.svg")


def fig_pilot():
    s = Svg(620, 400); L, T, R, B = 80, 60, 580, 320
    s.text(20, 30, "30x16 pilot (v2 rules): plain Codex copied one module 5 times", 18, weight="bold")
    sy = lambda v: B - (B - T) * v / 0.5
    for k in range(6):
        v = k * 0.1; s.line(L, sy(v), R, sy(v)); s.text(L - 8, sy(v) + 5, f"{v:.1f}", 13, INK2, "end")
    s.line(L, B, R, B, INK2)
    data = [("prototype", BLUE, 0.027, 0.017), ("plain Codex", ORANGE, 0.496, 0.117)]
    gw = (R - L) / 2
    for i, (lab, color, v2, v3) in enumerate(data):
        x0 = L + i * gw + gw / 2 - 90
        for j, (v, tag) in enumerate(((v2, "as graded"), (v3, "each gene once"))):
            x = x0 + j * 92
            s.bar(x, B, 86, sy(v), color if j == 0 else AQUA)
            s.text(x + 43, sy(v) - 6, f"{v:.3f}", 13, INK2, "middle")
            s.text(x + 43, B + 20, tag, 13, INK2, "middle")
        s.text(L + i * gw + gw / 2, B + 44, lab, 15, INK, "middle", "bold")
    s.text(L - 56, (T + B) / 2, "hypothesis score", 14, INK2, "middle")
    s.el[-1] = s.el[-1].replace("<text ", f"<text transform='rotate(-90 {L - 56} {(T + B) / 2})' ", 1)
    s.save("pilot_dedup.svg")


def fig_diagnosis():
    """Module members by type (v3 seed 0): good / known non-hit added as a new gene / other known bad."""
    d = {r["run"]: r for r in json.load(open("ours/diagnose_modules_nov23.json"))}
    s = Svg(760, 330); L, T, R = 170, 70, 720
    s.text(20, 30, "What went into the modules (v3 rules, seed 0): the facts were known", 18, weight="bold")
    parts = [("good (hit, right sign)", BLUE), ("new gene, known non-hit", ORANGE), ("other, score known", GRAY),
             ("score missing from files", "#e34948")]
    for i, (run, lab) in enumerate((("v3_ours_s0", "prototype"), ("v3_base_s0", "plain Codex"))):
        r = d[run]; y = T + i * 80; n = r["members"]
        vals = [r["good"], r["bad: fresh non-hit, score known"],
                r["bad: files had the correct score"] - r["bad: fresh non-hit, score known"],
                r["bad: no score in files"] + r["bad: files had a wrong score"]]
        s.text(L - 12, y + 32, lab, 15, INK, "end", "bold")
        x = L
        for (pl, color), v in zip(parts, vals):
            w = (R - L) * v / n
            if w > 0:
                s.el.append(f"<rect x='{x:.1f}' y='{y + 10}' width='{max(w - 2, 0):.1f}' height='34' rx='3' fill='{color}'/>")
                if w > 40:
                    s.text(x + w / 2, y + 32, str(v), 13, "#ffffff", "middle", "bold")
            x += w
        s.text(R, y + 62, f"{n} members", 12, INK2, "end")
    for j, (pl, color) in enumerate(parts):
        s.el.append(f"<rect x='{20 + j * 185}' y='{T + 182}' width='14' height='14' rx='2' fill='{color}'/>")
        s.text(40 + j * 185, T + 194, pl, 13, INK2)
    s.text(20, T + 232, "Same agents' data, neighbour grouping: 0.095 and 0.100 vs the agents' 0.048 and 0.055.", 14, INK)
    s.save("diagnosis_modules.svg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig_hits(); fig_repeats(); fig_grading(); fig_pilot(); fig_diagnosis()
    print(sorted(p.name for p in OUT.glob("*.svg")))
