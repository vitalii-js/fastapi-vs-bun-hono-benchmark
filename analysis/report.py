# /// script
# requires-python = ">=3.12"
# dependencies = ["matplotlib", "pandas"]
# ///
"""Turns results/raw/*.json from bench/run.sh into results/summary.md and charts."""

import json
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
CHARTS = ROOT / "results" / "charts"
ARTICLE_IMG = ROOT / "docs" / "img"

# Validated categorical slots 1-2 (light surface), see dataviz reference palette.
COLORS = {"fastapi": "#2a78d6", "hono": "#eb6834"}
LABELS = {"fastapi": "FastAPI (Python 3.14)", "hono": "Hono (Bun 1.4)"}
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
ROUND_LABEL = {"A": "1 CPU · 1 process", "B": "4 CPU · 4 processes"}

NAME_RE = re.compile(r"(?P<app>\w+?)_(?P<round>[AB])_(?P<endpoint>static|insert)_c(?P<c>\d+)_r(?P<rep>\d+)")


def to_mib(s: str) -> float:
    num, unit = re.match(r"([\d.]+)\s*([KMG]i?B|B)", s).groups()
    return float(num) * {"B": 1 / 2**20, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[unit]


def load() -> pd.DataFrame:
    rows = []
    for f in sorted(RAW.glob("*_r*.json")):
        if f.name.endswith(".check.json"):
            continue
        m = NAME_RE.match(f.stem)
        d = json.loads(f.read_text())
        s, p = d["summary"], d["latencyPercentiles"]
        total = sum(d["statusCodeDistribution"].values()) + sum(d["errorDistribution"].values())
        ok = sum(v for k, v in d["statusCodeDistribution"].items() if k.startswith("2"))
        row = {
            **m.groupdict(),
            "rps": s["requestsPerSec"],
            "p50": p["p50"] * 1000,
            "p95": p["p95"] * 1000,
            "p99": p["p99"] * 1000,
            "errors_pct": 100 * (1 - ok / total) if total else 100.0,
            "requests": total,
        }
        stats = f.with_suffix(".stats.jsonl")
        samples = [json.loads(line) for line in stats.read_text().splitlines()] if stats.exists() else []
        app = [x for x in samples if f"-{m['app']}-" in x["Name"] and to_mib(x["MemUsage"].split(" /")[0]) > 0]
        pg = [x for x in samples if "-postgres-" in x["Name"]]
        oha = [x for x in samples if "-oha-" in x["Name"]]
        cpu = lambda xs: sum(float(x["CPUPerc"].rstrip("%")) for x in xs) / len(xs) if xs else float("nan")
        row["app_cpu_pct"] = cpu(app)
        row["pg_cpu_pct"] = cpu(pg)
        row["oha_cpu_pct"] = cpu(oha)
        row["app_mem_mib"] = max((to_mib(x["MemUsage"].split(" /")[0]) for x in app), default=float("nan"))
        check = f.with_suffix(".check.json")
        if check.exists():
            c = json.loads(check.read_text())
            row["rows_minus_201"] = c["rows"] - c["http_201"]
        rows.append(row)
    df = pd.DataFrame(rows)
    df["c"] = df["c"].astype(int)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["endpoint", "round", "c", "app"]
    agg = df.groupby(keys).agg(
        rps=("rps", "median"),
        p50=("p50", "median"),
        p95=("p95", "median"),
        p99=("p99", "median"),
        errors_pct=("errors_pct", "max"),
        app_cpu_pct=("app_cpu_pct", "median"),
        pg_cpu_pct=("pg_cpu_pct", "median"),
        oha_cpu_pct=("oha_cpu_pct", "max"),
        app_mem_mib=("app_mem_mib", "max"),
        rps_min=("rps", "min"),
        rps_max=("rps", "max"),
        reps=("rps", "size"),
    )
    if "rows_minus_201" in df:
        agg["rows_minus_201"] = df.groupby(keys)["rows_minus_201"].apply(lambda s: s.abs().max())
    return agg.reset_index().sort_values(["endpoint", "round", "c", "app"], ascending=[False, True, True, True])


def write_markdown(s: pd.DataFrame) -> None:
    env = (ROOT / "results" / "env.txt").read_text() if (ROOT / "results" / "env.txt").exists() else ""
    out = ["# Results", "", "```", env.strip(), "```", ""]
    out += ["Median of repetitions. Latency in ms, memory = peak RSS of the app container, CPU in % of one core.", ""]
    out += ["| Endpoint | Setup | Conc. | App | RPS | p50 | p95 | p99 | Errors % | App CPU % | PG CPU % | Peak mem MiB | Spread (min–max RPS) |"]
    out += ["|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in s.itertuples():
        out.append(
            f"| {r.endpoint} | {ROUND_LABEL[r.round]} | {r.c} | {r.app} | {r.rps:,.0f} | {r.p50:.2f} | {r.p95:.2f} | "
            f"{r.p99:.2f} | {r.errors_pct:.2f} | {r.app_cpu_pct:.0f} | {r.pg_cpu_pct:.0f} | {r.app_mem_mib:.0f} | "
            f"{r.rps_min:,.0f}–{r.rps_max:,.0f} |"
        )
    out += ["", "## Hono vs FastAPI", "", "| Endpoint | Setup | Conc. | RPS ratio (Hono / FastAPI) | p99 FastAPI | p99 Hono |", "|---|---|---|---:|---:|---:|"]
    for (ep, rnd, c), g in s.groupby(["endpoint", "round", "c"], sort=False):
        f, h = g.set_index("app").loc["fastapi"], g.set_index("app").loc["hono"]
        out.append(f"| {ep} | {ROUND_LABEL[rnd]} | {c} | **{h.rps / f.rps:.2f}×** | {f.p99:.2f} ms | {h.p99:.2f} ms |")
    if "rows_minus_201" in s:
        ins = s[s.endpoint == "insert"]
        out += ["", f"Insert integrity: max |rows in DB − HTTP 201 count| across all runs = **{int(ins.rows_minus_201.max())}**."]
    out += ["", f"Load generator (oha) peak CPU: {s.oha_cpu_pct.max():.0f}% of a 600% budget."]
    (ROOT / "results" / "summary.md").write_text("\n".join(out) + "\n")


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0, labelsize=11)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fmt_value(v: float, metric: str) -> str:
    if metric == "rps":
        return f"{v / 1000:.1f}k" if v < 100_000 else f"{v / 1000:.0f}k"
    if metric == "app_mem_mib":
        return f"{v:.0f}"
    return f"{v:.1f}" if v >= 1 else f"{v:.2f}"


def grouped_panels(s: pd.DataFrame, metric: str, title: str, subtitle: str, ylabel: str, fname: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.27), dpi=100, facecolor=SURFACE)
    width = 0.36
    for ax, ep in zip(axes, ["static", "insert"]):
        style(ax)
        sub = s[s.endpoint == ep]
        groups = list(sub.groupby(["round", "c"], sort=True).groups.keys())
        for i, app in enumerate(["fastapi", "hono"]):
            vals = [sub[(sub["round"] == r) & (sub.c == c) & (sub.app == app)][metric].iloc[0] for r, c in groups]
            xs = [g + (i - 0.5) * (width + 0.02) for g in range(len(groups))]
            bars = ax.bar(xs, vals, width, color=COLORS[app], label=LABELS[app], edgecolor=SURFACE, linewidth=2)
            for b, v in zip(bars, vals):
                ax.annotate(fmt_value(v, metric), (b.get_x() + b.get_width() / 2, b.get_height()),
                            xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                            fontsize=10, color=INK)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([f"{ROUND_LABEL[r].replace(' · ', chr(10))}\n{c} conn." for r, c in groups], fontsize=10)
        ax.set_title("GET /static  (6.9 KB JSON)" if ep == "static" else "POST /items  (validate + INSERT)",
                     loc="left", fontsize=13, color=INK, pad=10, fontweight="bold")
        ax.set_ylabel(ylabel, color=INK_2, fontsize=11)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v / 1000:.0f}k" if metric == "rps" and v >= 1000 else f"{v:g}"))
        ax.margins(y=0.12)
    fig.suptitle(title, x=0.02, y=0.97, ha="left", fontsize=18, fontweight="bold", color=INK)
    fig.text(0.02, 0.895, subtitle, ha="left", fontsize=11.5, color=INK_2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.985), ncol=2, frameon=False,
               fontsize=11, labelcolor=INK)
    fig.text(0.02, 0.015, "Docker on Apple M4 Pro · oha load generator · median of 3 × 30 s runs · Postgres 17",
             fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0.035, 1, 0.88))
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / fname, facecolor=SURFACE)
    plt.close(fig)


def cover(s: pd.DataFrame) -> None:
    """One headline chart for the post: Hono throughput as a multiple of FastAPI."""
    rows = []
    for (ep, rnd, c), g in s.groupby(["endpoint", "round", "c"], sort=False):
        g = g.set_index("app")
        name = "GET /static" if ep == "static" else "POST /items"
        rows.append((f"{name}  ·  {ROUND_LABEL[rnd]}  ·  {c} conn.", g.loc["hono", "rps"] / g.loc["fastapi", "rps"]))
    rows.reverse()
    fig, ax = plt.subplots(figsize=(12, 6.27), dpi=100, facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ys = range(len(rows))
    bars = ax.barh(list(ys), [r[1] for r in rows], height=0.62, color=COLORS["hono"], edgecolor=SURFACE, linewidth=2)
    for b, (_, v) in zip(bars, rows):
        ax.annotate(f"{v:.1f}×", (v, b.get_y() + b.get_height() / 2), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=12, color=INK, fontweight="bold")
    ax.axvline(1, color=INK_2, linewidth=1.2, linestyle=(0, (3, 3)))
    ax.annotate("1× = same as FastAPI", (1, len(rows) - 0.45), xytext=(6, 0), textcoords="offset points",
                fontsize=10, color=INK_2, va="center")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=11, color=INK)
    ax.set_xlim(0, max(r[1] for r in rows) * 1.15)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}×"))
    lo, hi = min(r[1] for r in rows), max(r[1] for r in rows)
    fig.suptitle(f"Hono on Bun served {lo:.1f}–{hi:.1f}× more requests/s than FastAPI",
                 x=0.02, y=0.96, ha="left", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.02, 0.88, "Same endpoints, same Docker CPU limits, same Postgres 17. Median of 3 × 30 s runs, 0 errors.",
             ha="left", fontsize=12, color=INK_2)
    fig.text(0.02, 0.015, "Docker on Apple M4 Pro · FastAPI + uvicorn + asyncpg vs Hono + Bun.SQL · load generator: oha",
             fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0.035, 1, 0.86))
    fig.savefig(CHARTS / "cover.png", facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]
    df = load()
    s = summarize(df)
    write_markdown(s)
    grouped_panels(s, "rps", "Requests per second (higher is better)",
                   "Same endpoints, same CPU limits, same Postgres pool. Bars = median throughput.",
                   "requests / s", "rps.png")
    grouped_panels(s, "p99", "p99 latency (lower is better)",
                   "99% of requests finished faster than this. Milliseconds.",
                   "ms", "p99.png")
    grouped_panels(s, "app_mem_mib", "Peak memory of the app container (lower is better)",
                   "Resident memory while under load, all worker processes combined. MiB.",
                   "MiB", "memory.png")
    cover(s)
    ARTICLE_IMG.mkdir(parents=True, exist_ok=True)
    for png in CHARTS.glob("*.png"):
        shutil.copy(png, ARTICLE_IMG / png.name)
    print((ROOT / "results" / "summary.md").read_text())


if __name__ == "__main__":
    main()
