#!/usr/bin/env python3
"""
Independent critical evaluation of Claim 002 (Healthy Episode Characterization)
Antigravity/Opus -- Tier B

Uses frozen snapshot tcs_infy_v1_2026-07-04.
Does NOT reference or reproduce Codex's methodology; implements its own
rolling analysis and answers the four evaluation questions independently.
"""

import os
import sys
import hashlib
import datetime
import warnings
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SNAPSHOT_PATH = os.path.join(
    REPO_ROOT, "data", "snapshots", "tcs_infy_v1_2026-07-04", "adjusted_close.csv"
)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"

# Use only the longer, more reliable windows (per Claim 001 / our own Part A)
WINDOW_LENGTHS = [500, 730]
SIG = 0.05  # primary significance threshold


# ── Helpers ────────────────────────────────────────────────────────────


def load_snapshot():
    df = pd.read_csv(SNAPSHOT_PATH, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    df = df.rename(columns={"TCS.NS": "TCS", "INFY.NS": "INFY"})
    # Use log prices for the cointegration analysis
    df["log_TCS"] = np.log(df["TCS"])
    df["log_INFY"] = np.log(df["INFY"])
    return df


def rolling_diagnostics(df, wlen):
    """Monthly rolling cointegration diagnostics using trailing window of wlen days."""
    monthly = df.resample("ME").last().index
    rows = []
    prev_beta = None

    for eval_date in monthly:
        trailing = df.loc[:eval_date].tail(wlen)
        if len(trailing) < wlen:
            continue

        tcs = trailing["log_TCS"].values
        infy = trailing["log_INFY"].values

        # OLS: log(TCS) = alpha + beta * log(INFY) + eps
        X = sm.add_constant(infy)
        ols = sm.OLS(tcs, X).fit()
        beta = ols.params[1]
        resid = ols.resid

        abs_beta_chg = abs(beta - prev_beta) if prev_beta is not None else np.nan
        prev_beta = beta

        # Engle-Granger
        try:
            _, eg_pval, _ = coint(tcs, infy, trend="c", autolag="aic")
        except Exception:
            eg_pval = np.nan

        # Residual ADF
        try:
            _, adf_pval, *_ = adfuller(resid, regression="n", autolag="aic")
        except Exception:
            adf_pval = np.nan

        # Half-life from AR(1)
        try:
            lag = resid[:-1]
            now = resid[1:]
            phi_hat = sm.OLS(now, sm.add_constant(lag)).fit().params[1]
            hl = -np.log(2) / np.log(phi_hat) if 0 < phi_hat < 1 else np.nan
        except Exception:
            hl = np.nan
            phi_hat = np.nan

        # Spread statistics
        spread_std = np.std(resid, ddof=1)
        spread_daily_chg_std = np.std(np.diff(resid), ddof=1)

        rows.append({
            "date": eval_date,
            "window_length": wlen,
            "beta": beta,
            "abs_beta_change": abs_beta_chg,
            "eg_pval": eg_pval,
            "adf_pval": adf_pval,
            "phi_hat": phi_hat if not np.isnan(phi_hat) else np.nan,
            "half_life": hl,
            "spread_std": spread_std,
            "spread_daily_chg_std": spread_daily_chg_std,
            "eg_pass": int(eg_pval < SIG) if not np.isnan(eg_pval) else 0,
            "adf_pass": int(adf_pval < SIG) if not np.isnan(adf_pval) else 0,
            "strict_pass": int((eg_pval < SIG) and (adf_pval < SIG)),
        })

    return pd.DataFrame(rows)


def find_healthy_runs(metrics_df, wlen):
    """Find contiguous runs where strict_pass == 1 for a given window length."""
    w = metrics_df[metrics_df["window_length"] == wlen].copy()
    w = w.sort_values("date").reset_index(drop=True)

    runs = []
    current_start = None
    current_count = 0

    for i, row in w.iterrows():
        if row["strict_pass"] == 1:
            if current_start is None:
                current_start = row["date"]
            current_count += 1
        else:
            if current_start is not None:
                runs.append({
                    "start": current_start,
                    "end": w.iloc[i - 1]["date"],
                    "months": current_count,
                })
            current_start = None
            current_count = 0

    if current_start is not None:
        runs.append({
            "start": current_start,
            "end": w.iloc[len(w) - 1]["date"],
            "months": current_count,
        })

    return runs


def optimal_split_test(series_dict, n_perm=2000, rng_seed=42):
    """Find optimal binary split point on multivariate time series.

    For each candidate split point, compute total RSS reduction from splitting
    each variable into two-segment means vs one grand mean. Report the best
    split and a permutation p-value.

    series_dict: {name: array} -- all arrays same length, ordered by time.
    """
    n = None
    for k, v in series_dict.items():
        arr = np.asarray(v, dtype=float)
        series_dict[k] = arr
        if n is None:
            n = len(arr)
        assert len(arr) == n

    if n < 6:
        return None  # too short to split meaningfully

    def total_rss_ratio(perm_idx=None):
        """RSS improvement ratio for the best split under given ordering."""
        best_ratio = -np.inf
        best_k = None
        for k in range(2, n - 2):
            rss_full = 0.0
            rss_split = 0.0
            for name, arr in series_dict.items():
                vals = arr if perm_idx is None else arr[perm_idx]
                grand_mean = vals.mean()
                rss_full += np.sum((vals - grand_mean) ** 2)
                left = vals[:k]
                right = vals[k:]
                rss_split += np.sum((left - left.mean()) ** 2) + np.sum(
                    (right - right.mean()) ** 2
                )
            ratio = 1 - rss_split / rss_full if rss_full > 0 else 0
            if ratio > best_ratio:
                best_ratio = ratio
                best_k = k
        return best_ratio, best_k

    observed_ratio, observed_k = total_rss_ratio()

    # Permutation test
    rng = np.random.RandomState(rng_seed)
    count_ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(n)
        perm_ratio, _ = total_rss_ratio(perm)
        if perm_ratio >= observed_ratio:
            count_ge += 1
    perm_p = (count_ge + 1) / (n_perm + 1)

    return {
        "best_split_idx": observed_k,
        "rss_improvement": observed_ratio,
        "perm_p": perm_p,
    }


def mann_kendall_trend(series):
    """Simple Mann-Kendall trend test. Returns (tau, p_value)."""
    n = len(series)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = series[j] - series[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1
    # Variance
    var_s = n * (n - 1) * (2 * n + 5) / 18
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0
    p = 2 * sp_stats.norm.sf(abs(z))
    tau = s / (n * (n - 1) / 2)
    return tau, p


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit():
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10,
                           cwd=REPO_ROOT)
        return r.stdout.strip() if r.returncode == 0 else "unavailable"
    except Exception:
        return "unavailable"


# ── Main analysis ──────────────────────────────────────────────────────


def main():
    print("Loading frozen snapshot:", SNAPSHOT_ID)
    df = load_snapshot()
    print(f"  {len(df)} trading days, {df.index[0].date()} to {df.index[-1].date()}")

    # ── Step 1: Compute rolling diagnostics ──
    all_metrics = []
    for wlen in WINDOW_LENGTHS:
        print(f"\nComputing {wlen}d rolling diagnostics...")
        m = rolling_diagnostics(df, wlen)
        all_metrics.append(m)
        print(f"  {len(m)} monthly observations")

    metrics = pd.concat(all_metrics, ignore_index=True)

    # Save rolling metrics
    metrics_path = os.path.join(OUTPUT_DIR, "opus_rolling_metrics.csv")
    metrics.to_csv(metrics_path, index=False)

    # ── Step 2: Find healthy runs ──
    print("\n--- Healthy episode identification ---")
    runs_500 = find_healthy_runs(metrics, 500)
    runs_730 = find_healthy_runs(metrics, 730)

    print("\n500d strict-pass runs:")
    for r in runs_500:
        print(f"  {r['start'].strftime('%Y-%m-%d')} to {r['end'].strftime('%Y-%m-%d')} ({r['months']} months)")

    print("\n730d strict-pass runs:")
    for r in runs_730:
        print(f"  {r['start'].strftime('%Y-%m-%d')} to {r['end'].strftime('%Y-%m-%d')} ({r['months']} months)")

    # Identify the longest run as the candidate "healthy core"
    longest_500 = max(runs_500, key=lambda r: r["months"]) if runs_500 else None
    longest_730 = max(runs_730, key=lambda r: r["months"]) if runs_730 else None

    print("\nLongest 500d healthy run:",
          f"{longest_500['start'].strftime('%Y-%m-%d')} to {longest_500['end'].strftime('%Y-%m-%d')} ({longest_500['months']} mo)"
          if longest_500 else "None")
    print("Longest 730d healthy run:",
          f"{longest_730['start'].strftime('%Y-%m-%d')} to {longest_730['end'].strftime('%Y-%m-%d')} ({longest_730['months']} mo)"
          if longest_730 else "None")

    # ── Step 3: Sub-regime analysis within 500d healthy core ──
    if longest_500:
        core = metrics[
            (metrics["window_length"] == 500)
            & (metrics["date"] >= longest_500["start"])
            & (metrics["date"] <= longest_500["end"])
        ].sort_values("date").reset_index(drop=True)

        print(f"\n--- Sub-regime analysis (500d core, n={len(core)}) ---")
        print(f"Beta range: {core['beta'].min():.4f} to {core['beta'].max():.4f}")
        print(f"Beta std: {core['beta'].std():.4f}")
        print(f"Half-life range: {core['half_life'].min():.1f} to {core['half_life'].max():.1f}")

        # Optimal split test
        split_vars = {
            "beta": core["beta"].values,
            "half_life": core["half_life"].values,
            "eg_pval": core["eg_pval"].values,
            "spread_std": core["spread_std"].values,
        }
        split_result = optimal_split_test(split_vars, n_perm=2000, rng_seed=42)

        if split_result:
            split_date = core.iloc[split_result["best_split_idx"]]["date"]
            print(f"\nBest split: after index {split_result['best_split_idx']} "
                  f"(date: {split_date.strftime('%Y-%m-%d')})")
            print(f"RSS improvement: {split_result['rss_improvement']:.4f}")
            print(f"Permutation p-value: {split_result['perm_p']:.4f}")

            # Characterize the two segments
            left = core.iloc[: split_result["best_split_idx"]]
            right = core.iloc[split_result["best_split_idx"] :]

            print(f"\nLeft segment ({left['date'].min().strftime('%Y-%m-%d')} to "
                  f"{left['date'].max().strftime('%Y-%m-%d')}, n={len(left)}):")
            print(f"  Beta mean={left['beta'].mean():.4f}, std={left['beta'].std():.4f}")
            print(f"  Half-life mean={left['half_life'].mean():.1f}")
            print(f"  EG p median={left['eg_pval'].median():.6f}")

            print(f"\nRight segment ({right['date'].min().strftime('%Y-%m-%d')} to "
                  f"{right['date'].max().strftime('%Y-%m-%d')}, n={len(right)}):")
            print(f"  Beta mean={right['beta'].mean():.4f}, std={right['beta'].std():.4f}")
            print(f"  Half-life mean={right['half_life'].mean():.1f}")
            print(f"  EG p median={right['eg_pval'].median():.6f}")

            # Welch t-test on beta between segments
            t_stat, t_p = sp_stats.ttest_ind(left["beta"], right["beta"], equal_var=False)
            print(f"\n  Welch t-test on beta: t={t_stat:.3f}, p={t_p:.4f}")

            # Welch t-test on half-life
            t_hl, t_hl_p = sp_stats.ttest_ind(left["half_life"], right["half_life"], equal_var=False)
            print(f"  Welch t-test on half-life: t={t_hl:.3f}, p={t_hl_p:.4f}")

    # ── Step 4: Degradation ordering ──
    # Within and just after the healthy core, track which metric weakens first
    if longest_500:
        print("\n--- Degradation ordering (500d window) ---")

        # Get the full 500d series around and after the healthy core
        w500 = metrics[metrics["window_length"] == 500].sort_values("date").reset_index(drop=True)

        # Find the last month of the healthy core
        core_end = longest_500["end"]
        core_end_idx = w500[w500["date"] == core_end].index[0]

        # Look at the tail of the core + the post-core period
        # Use 6 months before core end through the next 18 months
        pre_end = max(0, core_end_idx - 5)
        post_end = min(len(w500) - 1, core_end_idx + 18)
        transition = w500.iloc[pre_end : post_end + 1].copy()

        print(f"Transition window: {transition['date'].min().strftime('%Y-%m-%d')} "
              f"to {transition['date'].max().strftime('%Y-%m-%d')}")

        # Mann-Kendall trend tests over the transition
        for metric in ["eg_pval", "half_life", "adf_pval", "spread_std"]:
            vals = transition[metric].dropna().values
            if len(vals) >= 5:
                tau, mk_p = mann_kendall_trend(vals)
                print(f"  {metric}: Mann-Kendall tau={tau:.3f}, p={mk_p:.4f}")

        # Identify the first month where each metric crosses a threshold
        # EG weakening: first p > 0.01 within core, first p > 0.05 (failure)
        post_core = w500[w500["date"] > core_end].sort_values("date")
        core_data = w500[(w500["date"] >= longest_500["start"]) &
                         (w500["date"] <= core_end)].sort_values("date")

        # Within the core: when does EG first go above 0.01?
        eg_above_01_in_core = core_data[core_data["eg_pval"] > 0.01]
        if not eg_above_01_in_core.empty:
            print(f"\n  First EG p > 0.01 within core: "
                  f"{eg_above_01_in_core['date'].min().strftime('%Y-%m-%d')} "
                  f"(p={eg_above_01_in_core.iloc[0]['eg_pval']:.4f})")

        # After core: first EG failure
        eg_fail_post = post_core[post_core["eg_pass"] == 0]
        if not eg_fail_post.empty:
            print(f"  First EG failure post-core: "
                  f"{eg_fail_post['date'].min().strftime('%Y-%m-%d')} "
                  f"(p={eg_fail_post.iloc[0]['eg_pval']:.4f})")

        # Half-life: when does it first exceed 20d?
        hl_high = post_core[post_core["half_life"] > 20]
        if not hl_high.empty:
            print(f"  First half-life > 20d post-core: "
                  f"{hl_high['date'].min().strftime('%Y-%m-%d')} "
                  f"(hl={hl_high.iloc[0]['half_life']:.1f})")
        else:
            # Check within the full transition zone
            hl_high_trans = transition[transition["half_life"] > 20]
            if not hl_high_trans.empty:
                print(f"  First half-life > 20d in transition: "
                      f"{hl_high_trans['date'].min().strftime('%Y-%m-%d')} "
                      f"(hl={hl_high_trans.iloc[0]['half_life']:.1f})")
            else:
                print("  Half-life stays <= 20d through the transition zone")

        # ADF: when does it first fail?
        adf_fail_post = post_core[post_core["adf_pass"] == 0]
        if not adf_fail_post.empty:
            print(f"  First ADF failure post-core: "
                  f"{adf_fail_post['date'].min().strftime('%Y-%m-%d')} "
                  f"(p={adf_fail_post.iloc[0]['adf_pval']:.4f})")
        else:
            print("  ADF never fails in the post-core period examined")

    # ── Step 5: Beta stability analysis ──
    if longest_500:
        print("\n--- Beta stability analysis (500d core) ---")

        # Split into first 6 months vs remaining
        n_core = len(core)
        early_n = min(6, n_core // 3)
        early = core.iloc[:early_n]
        late = core.iloc[early_n:]

        print(f"Early period ({early['date'].min().strftime('%Y-%m-%d')} to "
              f"{early['date'].max().strftime('%Y-%m-%d')}, n={len(early)}):")
        print(f"  Beta: mean={early['beta'].mean():.4f}, "
              f"std={early['beta'].std():.4f}, "
              f"range={early['beta'].min():.4f}-{early['beta'].max():.4f}")
        print(f"  Abs beta changes: mean={early['abs_beta_change'].dropna().mean():.4f}")

        print(f"Late period ({late['date'].min().strftime('%Y-%m-%d')} to "
              f"{late['date'].max().strftime('%Y-%m-%d')}, n={len(late)}):")
        print(f"  Beta: mean={late['beta'].mean():.4f}, "
              f"std={late['beta'].std():.4f}, "
              f"range={late['beta'].min():.4f}-{late['beta'].max():.4f}")
        print(f"  Abs beta changes: mean={late['abs_beta_change'].dropna().mean():.4f}")

        # Levene test for equal variances of beta changes
        early_chg = early["abs_beta_change"].dropna().values
        late_chg = late["abs_beta_change"].dropna().values
        if len(early_chg) >= 3 and len(late_chg) >= 3:
            lev_stat, lev_p = sp_stats.levene(early_chg, late_chg)
            print(f"\n  Levene test (beta change variance): F={lev_stat:.3f}, p={lev_p:.4f}")

        # Mann-Kendall on beta within core
        tau_b, mk_b_p = mann_kendall_trend(core["beta"].values)
        print(f"  Mann-Kendall on beta: tau={tau_b:.3f}, p={mk_b_p:.4f}")

    # ── Step 6: 730d analysis for comparison ──
    if longest_730:
        print("\n--- 730d window analysis ---")
        core_730 = metrics[
            (metrics["window_length"] == 730)
            & (metrics["date"] >= longest_730["start"])
            & (metrics["date"] <= longest_730["end"])
        ].sort_values("date").reset_index(drop=True)

        print(f"730d core: {longest_730['start'].strftime('%Y-%m-%d')} to "
              f"{longest_730['end'].strftime('%Y-%m-%d')} ({longest_730['months']} mo)")
        print(f"  Beta range: {core_730['beta'].min():.4f} to {core_730['beta'].max():.4f}")
        print(f"  Half-life range: {core_730['half_life'].min():.1f} to {core_730['half_life'].max():.1f}")
        print(f"  EG p range: {core_730['eg_pval'].min():.6f} to {core_730['eg_pval'].max():.6f}")

        # Sub-regime split
        if len(core_730) >= 6:
            split_730 = optimal_split_test(
                {
                    "beta": core_730["beta"].values,
                    "half_life": core_730["half_life"].values,
                    "eg_pval": core_730["eg_pval"].values,
                },
                n_perm=2000,
                rng_seed=42,
            )
            if split_730:
                sd = core_730.iloc[split_730["best_split_idx"]]["date"]
                print(f"\n  730d best split after: {sd.strftime('%Y-%m-%d')}")
                print(f"  RSS improvement: {split_730['rss_improvement']:.4f}")
                print(f"  Permutation p: {split_730['perm_p']:.4f}")

    # ── Provenance ──
    commit = git_commit()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    provenance = {
        "script_path": os.path.abspath(__file__),
        "git_commit": commit,
        "snapshot_id": SNAPSHOT_ID,
        "timestamp_utc": ts,
        "statsmodels_version": sm.__version__,
        "methods": {
            "engle_granger": "coint(trend='c', autolag='aic')",
            "adf": "adfuller(regression='n', autolag='aic')",
            "subregime_test": "multivariate RSS optimal-split with 2000 permutations",
        },
    }

    # Save provenance
    prov_path = os.path.join(OUTPUT_DIR, "opus_provenance.json")
    provenance["output_hashes"] = {
        "opus_rolling_metrics.csv": sha256_file(metrics_path),
    }
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print("\n\nOutputs saved to:", OUTPUT_DIR)
    print("  opus_rolling_metrics.csv")
    print("  opus_provenance.json")
    print("Done.")


if __name__ == "__main__":
    main()
