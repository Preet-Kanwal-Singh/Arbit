#!/usr/bin/env python3
"""
Claim 004: Episode 1 Beta Range
Antigravity/Opus -- Tier A independent computation

Descriptive reconstruction of month-end-sampled rolling beta
for TCS/INFY within each strict healthy core.

Snapshot: tcs_infy_v1_2026-07-04
"""

import os
import json
import hashlib
import datetime
import subprocess

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SNAPSHOT_CSV = os.path.join(
    REPO_ROOT, "data", "snapshots", "tcs_infy_v1_2026-07-04", "adjusted_close.csv"
)
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"

# ── Core definitions (hardcoded per spec section 1/3) ──────────────────

CORES = {
    500: {
        "start": pd.Timestamp("2020-01-31"),
        "end": pd.Timestamp("2021-12-31"),
        "window": 500,
    },
    730: {
        "start": pd.Timestamp("2020-12-31"),
        "end": pd.Timestamp("2023-03-31"),
        "window": 730,
    },
}

# ── Isolation declaration ──────────────────────────────────────────────
# This script has not read, opened, or referenced:
#   analysis/wq_recompute_episode1_beta_range/
#   analysis/wq_recompute_episode1_beta_range_v2/
#   ledger/worklog/worklog_tier_b.md
#   analysis/claim_004_episode1_beta_range/codex/
# No prior exposure to any of these paths in this conversation.


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def git_hash():
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unavailable"
    except Exception:
        return "unavailable"


def main():
    # ── Load snapshot ──
    df = pd.read_csv(SNAPSHOT_CSV, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    df.columns = ["TCS", "INFY"]

    # Drop rows missing either price
    df = df.dropna(subset=["TCS", "INFY"])

    # Log prices
    df["log_TCS"] = np.log(df["TCS"])
    df["log_INFY"] = np.log(df["INFY"])

    print(f"Snapshot: {SNAPSHOT_ID}")
    print(f"Trading days: {len(df)} ({df.index[0].date()} to {df.index[-1].date()})")

    # Month-end trading dates: actual last trading day per calendar month
    month_end_dates = df.groupby(df.index.to_period("M")).apply(
        lambda x: x.index.max()
    )

    commit = git_hash()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    output_hashes = {}
    all_stats = {}
    skips = {}

    for wlen, core in CORES.items():
        print(f"\n--- {wlen}d core: {core['start'].date()} to {core['end'].date()} ---")

        # Month-end dates within core bounds (inclusive)
        eval_dates = month_end_dates[
            (month_end_dates >= core["start"]) & (month_end_dates <= core["end"])
        ]

        betas = []
        beta_dates = []
        skipped = []

        for eval_date in eval_dates:
            # Trailing window: last N trading days ending at and including eval_date
            trailing = df.loc[:eval_date].tail(core["window"])

            if len(trailing) < core["window"]:
                skipped.append(str(eval_date.date()))
                continue

            y = trailing["log_TCS"].values
            x = trailing["log_INFY"].values

            # OLS with intercept: y = alpha + beta * x
            X = np.column_stack([np.ones(len(x)), x])
            params, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            beta_val = params[1]

            betas.append(beta_val)
            beta_dates.append(eval_date)

        skips[wlen] = skipped

        if skipped:
            print(f"  Skipped {len(skipped)} month-ends: {skipped}")

        # Save beta series CSV
        series_df = pd.DataFrame({"date": beta_dates, "beta": betas})
        series_df["date"] = series_df["date"].dt.strftime("%Y-%m-%d")
        csv_name = f"beta_series_{wlen}d_core.csv"
        csv_path = os.path.join(SCRIPT_DIR, csv_name)
        series_df.to_csv(csv_path, index=False)
        output_hashes[csv_name] = sha256_file(csv_path)

        # Compute descriptive statistics
        b_arr = np.array(betas)
        stats = {
            "n_observations": len(b_arr),
            "min_beta": float(b_arr.min()),
            "max_beta": float(b_arr.max()),
            "mean_beta": float(b_arr.mean()),
            "median_beta": float(np.median(b_arr)),
            "std_beta": float(b_arr.std(ddof=1)),
            "first_date": str(beta_dates[0].date()),
            "first_beta": float(betas[0]),
            "last_date": str(beta_dates[-1].date()),
            "last_beta": float(betas[-1]),
        }
        all_stats[wlen] = stats

        print(f"  n={stats['n_observations']}")
        print(f"  min={stats['min_beta']:.6f}  max={stats['max_beta']:.6f}")
        print(f"  mean={stats['mean_beta']:.6f}  median={stats['median_beta']:.6f}")
        print(f"  std={stats['std_beta']:.6f}")
        print(f"  first: {stats['first_date']} beta={stats['first_beta']:.6f}")
        print(f"  last:  {stats['last_date']} beta={stats['last_beta']:.6f}")

    # ── Write summary.md ──
    summary_lines = []
    summary_lines.append("<!--")
    summary_lines.append(f"script_path: {os.path.abspath(__file__)}")
    summary_lines.append(f"git_commit: {commit}")
    summary_lines.append(f"snapshot_id: {SNAPSHOT_ID}")
    summary_lines.append(f"timestamp_utc: {ts}")
    for fn, fh in output_hashes.items():
        summary_lines.append(f"{fn}_sha256: {fh}")
    summary_lines.append("-->")
    summary_lines.append("")
    summary_lines.append("# Claim 004: Episode 1 Beta Range -- Antigravity/Opus")
    summary_lines.append("")
    summary_lines.append("## Isolation Declaration")
    summary_lines.append("")
    summary_lines.append("This implementation has not read, opened, or referenced:")
    summary_lines.append("- `analysis/wq_recompute_episode1_beta_range/`")
    summary_lines.append("- `analysis/wq_recompute_episode1_beta_range_v2/`")
    summary_lines.append("- `ledger/worklog/worklog_tier_b.md`")
    summary_lines.append("- `analysis/claim_004_episode1_beta_range/codex/`")
    summary_lines.append("")
    summary_lines.append("## Method")
    summary_lines.append("")
    summary_lines.append("y = log(TCS.NS), x = log(INFY.NS). At each month-end trading date")
    summary_lines.append("within the core's date range (inclusive), OLS with intercept over the")
    summary_lines.append("trailing N trading days (N = window length). Beta = coefficient on x.")
    summary_lines.append("No pooling across cores or window lengths.")
    summary_lines.append("")

    for wlen in [500, 730]:
        s = all_stats[wlen]
        c = CORES[wlen]
        summary_lines.append(f"## {wlen}d Core ({c['start'].date()} to {c['end'].date()})")
        summary_lines.append("")
        summary_lines.append(f"| Statistic | Value |")
        summary_lines.append(f"|-----------|-------|")
        summary_lines.append(f"| n observations | {s['n_observations']} |")
        summary_lines.append(f"| min beta | {s['min_beta']:.6f} |")
        summary_lines.append(f"| max beta | {s['max_beta']:.6f} |")
        summary_lines.append(f"| mean beta | {s['mean_beta']:.6f} |")
        summary_lines.append(f"| median beta | {s['median_beta']:.6f} |")
        summary_lines.append(f"| std beta | {s['std_beta']:.6f} |")
        summary_lines.append(f"| first observation | {s['first_date']}, beta = {s['first_beta']:.6f} |")
        summary_lines.append(f"| last observation | {s['last_date']}, beta = {s['last_beta']:.6f} |")
        if skips[wlen]:
            summary_lines.append(f"| skipped month-ends | {', '.join(skips[wlen])} |")
        else:
            summary_lines.append(f"| skipped month-ends | none |")
        summary_lines.append("")

    summary_lines.append("## Limitation")
    summary_lines.append("")
    summary_lines.append("These are month-end sample points only. Beta could move outside")
    summary_lines.append("the reported range between sampled points. This does not characterize")
    summary_lines.append("intra-month excursions.")

    summary_path = os.path.join(SCRIPT_DIR, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")
    output_hashes["summary.md"] = sha256_file(summary_path)

    # ── Write provenance.json ──
    prov = {
        "snapshot_id": SNAPSHOT_ID,
        "git_commit": commit,
        "script_path": os.path.abspath(__file__),
        "execution_timestamp_utc": ts,
        "output_sha256": output_hashes,
    }
    prov_path = os.path.join(SCRIPT_DIR, "provenance.json")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)

    print(f"\nOutputs written to: {SCRIPT_DIR}")
    for fn in output_hashes:
        print(f"  {fn}: {output_hashes[fn]}")
    print("Done.")


if __name__ == "__main__":
    main()
