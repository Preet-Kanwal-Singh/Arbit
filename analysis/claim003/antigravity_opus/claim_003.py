#!/usr/bin/env python3
"""
Claim 003: EG-Halflife Ordering Robustness
Antigravity/Opus -- Tier A independent computation

Fixed-transition regime-switching simulation to test whether
Engle-Granger deterioration reliably precedes half-life deterioration
across independently-varied threshold configs.

Frozen snapshot: tcs_infy_v1_2026-07-04
"""

import os
import sys
import json
import hashlib
import datetime
import warnings
import subprocess
import time

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
from scipy.stats import beta as beta_dist

warnings.filterwarnings("ignore")

# ── Paths and constants ────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SNAPSHOT_CSV = os.path.join(
    REPO_ROOT, "data", "snapshots", "tcs_infy_v1_2026-07-04", "adjusted_close.csv"
)
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"

B = 2000
SEED = 42

# Healthy cores from Claim 002 Q1
CORES = {
    500: (pd.Timestamp("2020-01-31"), pd.Timestamp("2021-12-31")),
    730: (pd.Timestamp("2020-12-31"), pd.Timestamp("2023-03-31")),
}
# Degradation end: Claim 002 Opus-reported first-ADF-failure date
DEG_END = pd.Timestamp("2023-12-31")

# Threshold configurations (5 configs x 2 windows = 10 cells)
CONFIGS = {
    "C1": {"eg": 0.05, "hl": 20.0},  # baseline
    "C2": {"eg": 0.03, "hl": 20.0},  # tighter EG
    "C3": {"eg": 0.10, "hl": 20.0},  # looser EG
    "C4": {"eg": 0.05, "hl": 15.0},  # tighter HL
    "C5": {"eg": 0.05, "hl": 25.0},  # looser HL
}


# ── Data loading ───────────────────────────────────────────────────────

def load_data():
    df = pd.read_csv(SNAPSHOT_CSV, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    df.columns = ["TCS", "INFY"]
    df["log_TCS"] = np.log(df["TCS"])
    df["log_INFY"] = np.log(df["INFY"])
    return df


# ── Regime parameter fitting ──────────────────────────────────────────

def fit_regime(log_tcs_arr, log_infy_arr):
    """Fit OLS cointegration + AR(1) on spread + AR(1) on INFY returns.

    Returns dict with: alpha, beta, c_s, phi_s, se_phi_s, spread_resids,
                        c_r, phi_r, mu_r, ret_resids
    """
    n = len(log_tcs_arr)

    # OLS: log(TCS) = alpha + beta * log(INFY) + residuals
    X = np.column_stack([np.ones(n), log_infy_arr])
    params, _, _, _ = np.linalg.lstsq(X, log_tcs_arr, rcond=None)
    alpha, beta_val = params[0], params[1]
    spread = log_tcs_arr - alpha - beta_val * log_infy_arr

    # AR(1) on spread: s_t = c_s + phi_s * s_{t-1} + eta_t
    s_lag = spread[:-1]
    s_now = spread[1:]
    X_ar = np.column_stack([np.ones(len(s_lag)), s_lag])
    ar_fit = sm.OLS(s_now, X_ar).fit()
    c_s, phi_s = ar_fit.params
    se_phi_s = ar_fit.bse[1]
    spread_resids = ar_fit.resid

    # INFY daily log-returns and AR(1) on them
    infy_rets = np.diff(log_infy_arr)
    mu_r = infy_rets.mean()

    if len(infy_rets) > 2:
        r_lag = infy_rets[:-1]
        r_now = infy_rets[1:]
        X_r = np.column_stack([np.ones(len(r_lag)), r_lag])
        ar_r = sm.OLS(r_now, X_r).fit()
        c_r, phi_r = ar_r.params
        ret_resids = ar_r.resid
    else:
        c_r, phi_r = 0.0, 0.0
        ret_resids = np.array([0.0])

    return {
        "alpha": alpha, "beta": beta_val,
        "c_s": c_s, "phi_s": phi_s, "se_phi_s": se_phi_s,
        "spread_resids": spread_resids,
        "c_r": c_r, "phi_r": phi_r, "mu_r": mu_r,
        "ret_resids": ret_resids,
    }


# ── Simulation ─────────────────────────────────────────────────────────

def simulate_one(pre, post, n_pre, n_post, init_log_infy, rng):
    """Simulate one replicate of the regime-switching AR(1) model.

    Pre-regime parameters apply for indices 0..n_pre-1,
    post-regime for indices n_pre..n_pre+n_post-1.

    Returns (log_infy, log_tcs) as 1-D numpy arrays.
    """
    n = n_pre + n_post
    log_infy = np.empty(n)
    spread = np.empty(n)

    log_infy[0] = init_log_infy
    spread[0] = 0.0  # unconditional mean of OLS residuals
    prev_ret = pre["mu_r"]

    # Pre-draw all innovations for speed
    pre_ret_pool = pre["ret_resids"]
    post_ret_pool = post["ret_resids"]
    pre_sp_pool = pre["spread_resids"]
    post_sp_pool = post["spread_resids"]

    ret_draws_pre = rng.choice(pre_ret_pool, size=n, replace=True)
    ret_draws_post = rng.choice(post_ret_pool, size=n, replace=True)
    sp_draws_pre = rng.choice(pre_sp_pool, size=n, replace=True)
    sp_draws_post = rng.choice(post_sp_pool, size=n, replace=True)

    for t in range(1, n):
        if t < n_pre:
            r = pre["c_r"] + pre["phi_r"] * prev_ret + ret_draws_pre[t]
            spread[t] = pre["c_s"] + pre["phi_s"] * spread[t - 1] + sp_draws_pre[t]
        else:
            r = post["c_r"] + post["phi_r"] * prev_ret + ret_draws_post[t]
            spread[t] = post["c_s"] + post["phi_s"] * spread[t - 1] + sp_draws_post[t]
        log_infy[t] = log_infy[t - 1] + r
        prev_ret = r

    # Reconstruct log(TCS) with regime-specific alpha/beta
    log_tcs = np.empty(n)
    log_tcs[:n_pre] = pre["alpha"] + pre["beta"] * log_infy[:n_pre] + spread[:n_pre]
    log_tcs[n_pre:] = post["alpha"] + post["beta"] * log_infy[n_pre:] + spread[n_pre:]

    return log_infy, log_tcs


# ── Rolling pipeline for simulated data ────────────────────────────────

def rolling_metrics_at(log_tcs, log_infy, eval_indices, wlen):
    """Compute EG p-value and half-life at each evaluation index.

    Returns list of (eg_pval, half_life) tuples.
    """
    results = []
    for idx in eval_indices:
        ws = idx - wlen + 1
        if ws < 0:
            results.append((np.nan, np.nan))
            continue

        tcs_w = log_tcs[ws:idx + 1]
        infy_w = log_infy[ws:idx + 1]

        # Engle-Granger p-value
        try:
            _, eg_p, _ = coint(tcs_w, infy_w, trend="c", autolag="aic")
        except Exception:
            eg_p = np.nan

        # Half-life from AR(1) on OLS residuals
        try:
            X = np.column_stack([np.ones(len(infy_w)), infy_w])
            beta_ols = np.linalg.lstsq(X, tcs_w, rcond=None)[0]
            resid = tcs_w - X @ beta_ols
            lag = resid[:-1]
            now = resid[1:]
            X_ar = np.column_stack([np.ones(len(lag)), lag])
            phi_hat = np.linalg.lstsq(X_ar, now, rcond=None)[0][1]
            hl = -np.log(2) / np.log(phi_hat) if 0 < phi_hat < 1 else np.nan
        except Exception:
            hl = np.nan

        results.append((eg_p, hl))

    return results


# ── Statistical helpers ────────────────────────────────────────────────

def clopper_pearson(k, n, alpha=0.05):
    """Exact Clopper-Pearson 95% binomial CI."""
    if n == 0:
        return (0.0, 1.0)
    lo = beta_dist.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta_dist.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (lo, hi)


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


# ── Summary builder ────────────────────────────────────────────────────

def build_summary(cell_results, window_results, study_class, prov):
    L = []
    L.append("# Claim 003: EG-Halflife Ordering Robustness -- Antigravity/Opus\n")

    # Provenance header
    L.append("## Provenance\n")
    L.append(f"- Script: `{prov['script_path']}`")
    L.append(f"- Git commit: `{prov['git_commit']}`")
    L.append(f"- Snapshot: `{prov['snapshot_id']}`")
    L.append(f"- Timestamp UTC: `{prov['timestamp_utc']}`")
    L.append(f"- Replicates: B={prov['B']}, seed={prov['seed']}")
    for fn, fh in prov.get("output_hashes", {}).items():
        L.append(f"- `{fn}` SHA256: `{fh}`")
    L.append("")

    # Study-level
    L.append(f"## Study-Level Classification: {study_class}\n")

    # Per-window detail
    for wlen in [500, 730]:
        wr = window_results.get(wlen)
        if wr is None:
            continue
        L.append(f"### {wlen}d Window\n")
        L.append(f"- Classification: **{wr['classification']}**")
        L.append(f"- WELL-POWERED: {wr['well_powered']}")
        L.append(f"- PARAMETER-STABLE: {wr['param_stable']}")
        L.append("")

        # Cell table
        L.append("| Config | EG thresh | HL thresh | N_eff | P_hat | CI_lo | CI_hi | Classification | EG-only | HL-only | Neither | Simul |")
        L.append("|--------|-----------|-----------|-------|-------|-------|-------|----------------|---------|---------|---------|-------|")
        for cr in cell_results:
            if cr["window"] == wlen:
                ph = cr["p_hat"] if cr["p_hat"] is not None else "N/A"
                L.append(
                    f"| {cr['config']} | {cr['eg_thresh']} | {cr['hl_thresh']} | "
                    f"{cr['n_eff']} | {ph} | {cr['ci_lo']} | {cr['ci_hi']} | "
                    f"{cr['classification']} | {cr['rate_eg_only']} | {cr['rate_hl_only']} | "
                    f"{cr['rate_neither']} | {cr['rate_simultaneous']} |"
                )
        L.append("")

        # AR(1) parameters
        cells = wr.get("cells", {})
        c1 = cells.get("C1", {})
        if c1:
            L.append("**Spread AR(1) parameters:**\n")
            L.append(f"- phi_pre = {c1.get('phi_pre')} (SE = {c1.get('se_phi_pre')})")
            L.append(f"- phi_post = {c1.get('phi_post')} (SE = {c1.get('se_phi_post')})")
            L.append(f"- PARAMETER-UNSTABLE: {c1.get('param_unstable')}")
            L.append("")

        # Real-data anchor table
        L.append("**Real-data anchor:**\n")
        L.append("| Config | EG crossing | HL crossing | Order |")
        L.append("|--------|------------|------------|-------|")
        for cr in cell_results:
            if cr["window"] == wlen:
                eg_d = cr.get("real_anchor_eg") or "never"
                hl_d = cr.get("real_anchor_hl") or "never"
                L.append(f"| {cr['config']} | {eg_d} | {hl_d} | {cr['real_anchor_order']} |")
        L.append("")

    # Limitations
    L.append("## Stated Limitations\n")
    L.append("- 500d and 730d cores and degradation windows overlap; a WINDOW-LENGTH-DEPENDENT or CONTRADICTED result reflects overlapping, not independent, procedures.")
    L.append("- INFY's AR(1)-residual treatment preserves first-order serial correlation but not volatility clustering.")
    L.append("- Simulation uses bootstrap residuals (resampling with replacement), preserving marginal distribution but not temporal dependence of innovations.")
    L.append("")

    # Method summary
    L.append("## Method\n")
    L.append(
        "Fixed-transition regime-switching simulation. Pre-regime parameters fitted on daily data "
        "within the strict healthy core; post-regime parameters fitted on daily data from the day "
        "after core end through 2023-12-31. INFY daily log-returns and spread (OLS residuals) "
        "each modeled as AR(1) with bootstrap innovations drawn from the regime-specific residual pool. "
        "At each month-end in the degradation window, the rolling pipeline re-estimates beta via OLS, "
        "computes Engle-Granger p-value via coint(trend='c', autolag='aic'), and half-life via AR(1) "
        "on the rolling OLS residuals. Crossing order determined by which metric first exceeds its "
        "threshold. P_hat = EG-first / (EG-first + HL-first); CI is Clopper-Pearson exact binomial at 95%."
    )

    return "\n".join(L)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 70)
    print("Claim 003: EG-Halflife Ordering Robustness")
    print("Antigravity/Opus -- Tier A")
    print("=" * 70)

    data = load_data()
    all_dates = data.index
    all_month_ends = data.resample("ME").last().index

    print(f"Snapshot: {SNAPSHOT_ID}")
    print(f"Trading days: {len(data)} ({all_dates[0].date()} to {all_dates[-1].date()})")

    cell_results = []
    window_results = {}

    for wlen in [500, 730]:
        core_s, core_e = CORES[wlen]
        deg_months = all_month_ends[
            (all_month_ends > core_e) & (all_month_ends <= DEG_END)
        ]

        if len(deg_months) == 0:
            print(f"\n[{wlen}d] No degradation months -- skipping.")
            continue

        print(f"\n{'=' * 70}")
        print(f"Window length: {wlen}d")
        print(f"Core: {core_s.date()} -- {core_e.date()}")
        print(f"Degradation: {deg_months[0].date()} -- {deg_months[-1].date()} "
              f"({len(deg_months)} months)")

        # ── Simulation boundaries ──
        first_deg_global = all_dates.get_indexer([deg_months[0]], method="ffill")[0]
        sim_start = max(0, first_deg_global - wlen)
        sim_end = all_dates.get_indexer([deg_months[-1]], method="ffill")[0]

        transition_global = all_dates.get_indexer([core_e], method="ffill")[0]
        transition_local = transition_global - sim_start
        n_pre = transition_local + 1  # indices 0..transition_local are pre-regime
        n_total = sim_end - sim_start + 1
        n_post = n_total - n_pre

        # Eval indices within the simulation array
        eval_local = []
        for d in deg_months:
            g = all_dates.get_indexer([d], method="ffill")[0]
            eval_local.append(g - sim_start)

        print(f"Sim: {n_total} days (n_pre={n_pre}, n_post={n_post})")
        print(f"Transition at local index {transition_local}")
        print(f"Eval points: {len(eval_local)}")

        # ── Fit regime parameters from real daily data ──
        core_s_idx = all_dates.get_indexer([core_s], method="ffill")[0]
        core_e_idx = transition_global

        pre_lt = data["log_TCS"].values[core_s_idx:core_e_idx + 1]
        pre_li = data["log_INFY"].values[core_s_idx:core_e_idx + 1]
        pre = fit_regime(pre_lt, pre_li)

        post_s_idx = transition_global + 1
        post_lt = data["log_TCS"].values[post_s_idx:sim_end + 1]
        post_li = data["log_INFY"].values[post_s_idx:sim_end + 1]
        post = fit_regime(post_lt, post_li)

        print(f"\nPre:  beta={pre['beta']:.4f}  phi_s={pre['phi_s']:.4f} "
              f"(SE={pre['se_phi_s']:.4f})  phi_r={pre['phi_r']:.4f}  "
              f"n={len(pre_lt)}")
        print(f"Post: beta={post['beta']:.4f}  phi_s={post['phi_s']:.4f} "
              f"(SE={post['se_phi_s']:.4f})  phi_r={post['phi_r']:.4f}  "
              f"n={len(post_lt)}")

        # PARAMETER-UNSTABLE check
        phi_post_upper = post["phi_s"] + 1.96 * post["se_phi_s"]
        param_unstable = bool(phi_post_upper >= 0.98)
        print(f"phi_post CI upper: {phi_post_upper:.4f} "
              f"{'** PARAMETER-UNSTABLE **' if param_unstable else '(stable)'}")

        # ── Real-data anchor ──
        print("\nReal-data anchor:")
        real_lt = data["log_TCS"].values[sim_start:sim_end + 1]
        real_li = data["log_INFY"].values[sim_start:sim_end + 1]
        real_metrics = rolling_metrics_at(real_lt, real_li, eval_local, wlen)

        real_anchor = {}
        for cn, cfg in CONFIGS.items():
            fe = next(
                (i for i, (ep, _) in enumerate(real_metrics)
                 if not np.isnan(ep) and ep >= cfg["eg"]),
                None,
            )
            fh = next(
                (i for i, (_, hl) in enumerate(real_metrics)
                 if not np.isnan(hl) and hl > cfg["hl"]),
                None,
            )
            fe_date = deg_months[fe] if fe is not None else None
            fh_date = deg_months[fh] if fh is not None else None

            if fe is not None and fh is not None:
                if fe < fh:
                    order = "EG-first"
                elif fh < fe:
                    order = "HL-first"
                else:
                    order = "simultaneous"
            elif fe is not None:
                order = "EG-only"
            elif fh is not None:
                order = "HL-only"
            else:
                order = "neither"

            real_anchor[cn] = {"eg_date": fe_date, "hl_date": fh_date, "order": order}
            eg_str = str(fe_date.date()) if fe_date is not None else "never"
            hl_str = str(fh_date.date()) if fh_date is not None else "never"
            print(f"  {cn}: EG={eg_str}  HL={hl_str}  -> {order}")

        # ── Simulation loop ──
        print(f"\nRunning B={B} replicates (seed={SEED})...")
        init_li = data["log_INFY"].values[sim_start]

        counters = {
            cn: {"eg_first": 0, "hl_first": 0, "simul": 0,
                 "eg_only": 0, "hl_only": 0, "neither": 0}
            for cn in CONFIGS
        }

        rng = np.random.RandomState(SEED)
        t_sim_start = time.time()

        for b in range(B):
            if (b + 1) % 500 == 0:
                elapsed = time.time() - t_sim_start
                rate = (b + 1) / elapsed
                eta = (B - b - 1) / rate if rate > 0 else 0
                print(f"  {b + 1}/{B}  ({rate:.1f} rep/s, ETA {eta:.0f}s)")

            sim_li, sim_lt = simulate_one(pre, post, n_pre, n_post, init_li, rng)
            metrics = rolling_metrics_at(sim_lt, sim_li, eval_local, wlen)

            for cn, cfg in CONFIGS.items():
                fe = next(
                    (i for i, (ep, _) in enumerate(metrics)
                     if not np.isnan(ep) and ep >= cfg["eg"]),
                    None,
                )
                fh = next(
                    (i for i, (_, hl) in enumerate(metrics)
                     if not np.isnan(hl) and hl > cfg["hl"]),
                    None,
                )

                if fe is not None and fh is not None:
                    if fe < fh:
                        counters[cn]["eg_first"] += 1
                    elif fh < fe:
                        counters[cn]["hl_first"] += 1
                    else:
                        counters[cn]["simul"] += 1
                elif fe is not None:
                    counters[cn]["eg_only"] += 1
                elif fh is not None:
                    counters[cn]["hl_only"] += 1
                else:
                    counters[cn]["neither"] += 1

        sim_elapsed = time.time() - t_sim_start
        print(f"  Done in {sim_elapsed:.1f}s")

        # ── Per-cell statistics ──
        print(f"\n--- Results for {wlen}d ---")
        window_cells = {}

        for cn in CONFIGS:
            cnt = counters[cn]
            n_eff = cnt["eg_first"] + cnt["hl_first"]

            if n_eff > 0:
                p_hat = cnt["eg_first"] / n_eff
                ci_lo, ci_hi = clopper_pearson(cnt["eg_first"], n_eff)
            else:
                p_hat = None
                ci_lo, ci_hi = 0.0, 1.0

            adequate = n_eff >= 100

            if n_eff == 0:
                classification = "INCONCLUSIVE -- INSUFFICIENT DATA"
            elif ci_lo > 0.5:
                classification = "ROBUST"
            elif ci_hi < 0.5:
                classification = "CONTRADICTED"
            else:
                classification = "INCONCLUSIVE"

            ra = real_anchor[cn]
            cell = {
                "window": wlen,
                "config": cn,
                "eg_thresh": CONFIGS[cn]["eg"],
                "hl_thresh": CONFIGS[cn]["hl"],
                "n_eff": n_eff,
                "eg_first_count": cnt["eg_first"],
                "hl_first_count": cnt["hl_first"],
                "p_hat": round(p_hat, 4) if p_hat is not None else None,
                "ci_lo": round(ci_lo, 4),
                "ci_hi": round(ci_hi, 4),
                "adequate_n": adequate,
                "classification": classification,
                "rate_eg_only": round(cnt["eg_only"] / B, 4),
                "rate_hl_only": round(cnt["hl_only"] / B, 4),
                "rate_neither": round(cnt["neither"] / B, 4),
                "rate_simultaneous": round(cnt["simul"] / B, 4),
                "phi_pre": round(pre["phi_s"], 6),
                "se_phi_pre": round(pre["se_phi_s"], 6),
                "phi_post": round(post["phi_s"], 6),
                "se_phi_post": round(post["se_phi_s"], 6),
                "param_unstable": param_unstable,
                "real_anchor_eg": (str(ra["eg_date"].date())
                                   if ra["eg_date"] is not None else None),
                "real_anchor_hl": (str(ra["hl_date"].date())
                                   if ra["hl_date"] is not None else None),
                "real_anchor_order": ra["order"],
            }
            window_cells[cn] = cell
            cell_results.append(cell)

            ph_str = f"{p_hat:.4f}" if p_hat is not None else "N/A"
            print(f"  {cn}: N_eff={n_eff:>5}  P_hat={ph_str}  "
                  f"CI=[{ci_lo:.4f},{ci_hi:.4f}]  {classification}")
            print(f"       eg_only={cnt['eg_only']}  hl_only={cnt['hl_only']}  "
                  f"neither={cnt['neither']}  simul={cnt['simul']}")

        # ── Per-window summary ──
        all_cls = [window_cells[cn]["classification"] for cn in CONFIGS]

        if any("CONTRADICTED" in c for c in all_cls):
            w_class = "CONTRADICTED"
        elif all(c == "ROBUST" for c in all_cls):
            w_class = "ROBUST"
        else:
            w_class = "INCONCLUSIVE"

        well_powered = all(window_cells[cn]["adequate_n"] for cn in CONFIGS)
        param_stable = not param_unstable

        window_results[wlen] = {
            "classification": w_class,
            "well_powered": well_powered,
            "param_stable": param_stable,
            "param_unstable": param_unstable,
            "cells": window_cells,
        }

        print(f"\n  {wlen}d summary: {w_class}")
        print(f"  WELL-POWERED: {well_powered}")
        print(f"  PARAMETER-STABLE: {param_stable}")

    # ── Study-level synthesis ──────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("Study-level synthesis")
    print("=" * 70)

    w500 = window_results.get(500, {})
    w730 = window_results.get(730, {})
    c500 = w500.get("classification", "INCONCLUSIVE")
    c730 = w730.get("classification", "INCONCLUSIVE")
    pu500 = w500.get("param_unstable", False)
    pu730 = w730.get("param_unstable", False)
    wp500 = w500.get("well_powered", False)
    wp730 = w730.get("well_powered", False)
    ps500 = w500.get("param_stable", True)
    ps730 = w730.get("param_stable", True)

    # Rule 1: CONTRADICTED if either window is CONTRADICTED
    if "CONTRADICTED" in c500 or "CONTRADICTED" in c730:
        unstable = []
        if "CONTRADICTED" in c500 and pu500:
            unstable.append("500d")
        if "CONTRADICTED" in c730 and pu730:
            unstable.append("730d")
        if unstable:
            study_class = (
                f"CONTRADICTED -- PARAMETER-UNSTABLE ({', '.join(unstable)})"
            )
        else:
            study_class = "CONTRADICTED"

    # Rule 2: ROBUST if both windows are ROBUST
    elif c500 == "ROBUST" and c730 == "ROBUST":
        unstable = []
        if pu500:
            unstable.append("500d")
        if pu730:
            unstable.append("730d")
        if unstable:
            study_class = (
                f"ROBUST -- PARAMETER-UNSTABLE ({', '.join(unstable)})"
            )
        else:
            study_class = "ROBUST"

    # Rule 3: At least one INCONCLUSIVE, neither CONTRADICTED
    else:
        if wp500 and wp730 and ps500 and ps730:
            if c500 != c730:
                study_class = "WINDOW-LENGTH-DEPENDENT"
            else:
                study_class = "INCONCLUSIVE -- GENUINE AMBIGUITY"
        else:
            parts = []
            if not wp500 or not wp730:
                insuff = []
                if not wp500:
                    insuff.append("500d")
                if not wp730:
                    insuff.append("730d")
                parts.append(
                    f"INCONCLUSIVE -- INSUFFICIENT DATA ({', '.join(insuff)})"
                )
            if not ps500 or not ps730:
                unst = []
                if not ps500:
                    unst.append("500d")
                if not ps730:
                    unst.append("730d")
                parts.append(
                    f"INCONCLUSIVE -- PARAMETER-UNSTABLE ({', '.join(unst)})"
                )
            study_class = "; ".join(parts) if parts else "INCONCLUSIVE"

    print(f"\nStudy-level classification: {study_class}")

    # ── Write outputs ──────────────────────────────────────────────────
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    # cell_results.csv
    cells_df = pd.DataFrame(cell_results)
    cells_path = os.path.join(SCRIPT_DIR, "cell_results.csv")
    cells_df.to_csv(cells_path, index=False)

    # provenance
    commit = git_hash()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prov = {
        "script_path": os.path.abspath(__file__),
        "git_commit": commit,
        "snapshot_id": SNAPSHOT_ID,
        "timestamp_utc": ts,
        "B": B,
        "seed": SEED,
        "statsmodels_version": sm.__version__,
        "methods": {
            "engle_granger": "coint(trend='c', autolag='aic')",
            "half_life": "-log(2)/log(phi_hat) from AR(1) with intercept on OLS residuals",
            "simulation": "regime-switching AR(1) on spread and INFY returns, bootstrap residuals",
            "ci": "Clopper-Pearson exact binomial 95%",
        },
        "output_hashes": {
            "cell_results.csv": sha256_file(cells_path),
        },
    }

    # summary.md
    summary_text = build_summary(cell_results, window_results, study_class, prov)
    summary_path = os.path.join(SCRIPT_DIR, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    prov["output_hashes"]["summary.md"] = sha256_file(summary_path)

    # provenance.json
    prov_path = os.path.join(SCRIPT_DIR, "provenance.json")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)

    total_elapsed = time.time() - t0
    print(f"\nOutputs:")
    print(f"  -> {cells_path}")
    print(f"  -> {summary_path}")
    print(f"  -> {prov_path}")
    print(f"\nTotal elapsed: {total_elapsed:.1f}s")
    print("Done.")


if __name__ == "__main__":
    main()
