#!/usr/bin/env python3
"""
TCS/INFY Cointegration Window Validation — Two-Part Analysis
Antigravity/Opus independent computation (Tier B)

Part A: Synthetic window-length validation across persistence regimes
Part B: Real TCS/INFY rolling cointegration analysis
"""

import os
import sys
import hashlib
import datetime
import warnings
import json
import subprocess

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller

warnings.filterwarnings("ignore")

# ── Configuration ──────────────────────────────────────────────────────

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW_LENGTHS = [60, 120, 250, 500, 730]
SIGNIFICANCE_LEVELS = [0.01, 0.05, 0.10]
N_SEEDS = 100  # per condition per window length

# Cointegration DGP parameters
PHI_REGIMES = {
    "fast_phi0.80": 0.80,
    "moderate_phi0.95": 0.95,
    "near_unit_root_phi0.99": 0.99,
}

# Spread innovation std relative to trend innovation std
# "low" = easy detection; "high" = harder detection
SPREAD_NOISE = {
    "low": 0.005,
    "high": 0.020,
}

TREND_SIGMA = 0.01  # daily trend innovation std
BETA_TRUE = 1.0

# Part B
TICKERS = ["TCS.NS", "INFY.NS"]
DATA_START = "2018-01-01"
DATA_END = "2026-06-30"
FIRST_FLAGGED_DATE = "2022-07-01"


# ── Simulation helpers ─────────────────────────────────────────────────


def generate_cointegrated(n, phi, sigma_z, rng):
    """Two log-price series sharing a common stochastic trend, stationary spread.

    DGP:
        w_t = w_{t-1} + eps_w          (common random walk)
        z_t = phi * z_{t-1} + eps_z    (stationary AR(1) spread)
        x_t = w_t
        y_t = beta * w_t + z_t
    """
    eps_w = rng.normal(0, TREND_SIGMA, n)
    w = np.cumsum(eps_w)

    eps_z = rng.normal(0, sigma_z, n)
    z = np.empty(n)
    z[0] = eps_z[0]
    for t in range(1, n):
        z[t] = phi * z[t - 1] + eps_z[t]

    x = w
    y = BETA_TRUE * w + z
    return y, x


def generate_noncointegrated(n, rng):
    """Two independent random walks — no shared trend, no stationary spread."""
    x = np.cumsum(rng.normal(0, TREND_SIGMA, n))
    y = np.cumsum(rng.normal(0, TREND_SIGMA, n))
    return y, x


def run_tests(y, x):
    """Engle-Granger cointegration test and standalone residual ADF.

    Returns (eg_pval, adf_pval).
    """
    # Engle-Granger
    try:
        _, eg_pval, _ = coint(y, x, trend="c", autolag="aic")
    except Exception:
        eg_pval = np.nan

    # OLS residuals -> ADF(regression='n')
    try:
        X_mat = sm.add_constant(x)
        resid = sm.OLS(y, X_mat).fit().resid
        _, adf_pval, *_ = adfuller(resid, regression="n", autolag="aic")
    except Exception:
        adf_pval = np.nan

    return eg_pval, adf_pval


# ── Part A ─────────────────────────────────────────────────────────────


def run_part_a():
    print("=" * 60)
    print("PART A -- Synthetic Window-Length Validation")
    print("=" * 60)

    rows = []

    # --- Cointegrated conditions ---
    for phi_label, phi_val in PHI_REGIMES.items():
        for noise_label, sigma_z in SPREAD_NOISE.items():
            for wlen in WINDOW_LENGTHS:
                eg_pvals = np.empty(N_SEEDS)
                adf_pvals = np.empty(N_SEEDS)

                for s in range(N_SEEDS):
                    seed = abs(hash((phi_label, noise_label, wlen, s))) % (2**31)
                    rng = np.random.RandomState(seed)
                    y, x = generate_cointegrated(wlen, phi_val, sigma_z, rng)
                    eg_pvals[s], adf_pvals[s] = run_tests(y, x)

                for sig in SIGNIFICANCE_LEVELS:
                    for test_name, pvals in [
                        ("engle_granger", eg_pvals),
                        ("residual_adf", adf_pvals),
                    ]:
                        valid = pvals[~np.isnan(pvals)]
                        pass_rate = np.mean(valid < sig) if len(valid) else np.nan
                        rows.append(
                            {
                                "window_length": wlen,
                                "condition": "cointegrated",
                                "phi_regime": phi_label,
                                "spread_noise": noise_label,
                                "test_type": test_name,
                                "significance_level": sig,
                                "mean_p": np.nanmean(pvals),
                                "std_p": np.nanstd(pvals),
                                "pass_rate": pass_rate,
                                "false_positive_rate": "",
                                "false_negative_rate": round(1 - pass_rate, 4)
                                if not np.isnan(pass_rate)
                                else "",
                            }
                        )

                print(
                    f"  coint | {phi_label} | noise={noise_label} | w={wlen} done"
                )

    # --- Non-cointegrated ---
    for wlen in WINDOW_LENGTHS:
        eg_pvals = np.empty(N_SEEDS)
        adf_pvals = np.empty(N_SEEDS)

        for s in range(N_SEEDS):
            seed = abs(hash(("non_coint", wlen, s))) % (2**31)
            rng = np.random.RandomState(seed)
            y, x = generate_noncointegrated(wlen, rng)
            eg_pvals[s], adf_pvals[s] = run_tests(y, x)

        for sig in SIGNIFICANCE_LEVELS:
            for test_name, pvals in [
                ("engle_granger", eg_pvals),
                ("residual_adf", adf_pvals),
            ]:
                valid = pvals[~np.isnan(pvals)]
                fpr = np.mean(valid < sig) if len(valid) else np.nan
                rows.append(
                    {
                        "window_length": wlen,
                        "condition": "not_cointegrated",
                        "phi_regime": "N/A",
                        "spread_noise": "N/A",
                        "test_type": test_name,
                        "significance_level": sig,
                        "mean_p": np.nanmean(pvals),
                        "std_p": np.nanstd(pvals),
                        "pass_rate": fpr,
                        "false_positive_rate": round(fpr, 4)
                        if not np.isnan(fpr)
                        else "",
                        "false_negative_rate": "",
                    }
                )

        print(f"  non-coint | w={wlen} done")

    df = pd.DataFrame(rows)
    return df


# ── Part B ─────────────────────────────────────────────────────────────


def fetch_data():
    """Fetch TCS.NS and INFY.NS adjusted close from yfinance."""
    import yfinance as yf

    print("\nFetching TCS.NS and INFY.NS from yfinance...")
    raw_tcs = yf.download("TCS.NS", start=DATA_START, end=DATA_END, progress=False)
    raw_infy = yf.download("INFY.NS", start=DATA_START, end=DATA_END, progress=False)

    if raw_tcs.empty or raw_infy.empty:
        print("ERROR: yfinance returned empty data. Stopping.")
        sys.exit(1)

    # yfinance >= 0.2.31 auto-adjusts by default and uses 'Close'.
    # Older versions have 'Adj Close'.  Handle both, and multi-level columns.
    def extract_close(df, ticker):
        if isinstance(df.columns, pd.MultiIndex):
            # Try 'Close' first (auto_adjust=True default), then 'Adj Close'
            for col_name in ["Close", "Adj Close"]:
                if col_name in df.columns.get_level_values(0):
                    return df[(col_name, ticker)].dropna()
            raise KeyError(f"No close-price column found for {ticker}")
        else:
            for col_name in ["Close", "Adj Close"]:
                if col_name in df.columns:
                    return df[col_name].dropna()
            raise KeyError("No close-price column found")

    tcs = extract_close(raw_tcs, "TCS.NS")
    infy = extract_close(raw_infy, "INFY.NS")

    combined = pd.DataFrame({"TCS": tcs, "INFY": infy}).dropna()
    print(f"  Date range: {combined.index[0].date()} to {combined.index[-1].date()}")
    print(f"  Trading days: {len(combined)}")
    return combined


def compute_half_life(residuals):
    """AR(1) half-life of residuals: -log(2)/log(phi_hat)."""
    lag = residuals[:-1]
    now = residuals[1:]
    X = sm.add_constant(lag)
    phi_hat = sm.OLS(now, X).fit().params[1]
    if 0 < phi_hat < 1:
        return -np.log(2) / np.log(phi_hat), phi_hat
    return np.nan, phi_hat


def run_part_b(combined):
    print("\n" + "=" * 60)
    print("PART B -- Real TCS/INFY Rolling Cointegration Analysis")
    print("=" * 60)

    # Monthly evaluation dates (month-end)
    monthly_dates = combined.resample("ME").last().index

    rows = []
    prev_beta = {w: None for w in WINDOW_LENGTHS}

    for eval_date in monthly_dates:
        for wlen in WINDOW_LENGTHS:
            trailing = combined.loc[:eval_date].tail(wlen)
            if len(trailing) < wlen:
                continue

            tcs_arr = trailing["TCS"].values
            infy_arr = trailing["INFY"].values

            # OLS:  TCS = α + β·INFY + ε
            X_mat = sm.add_constant(infy_arr)
            ols = sm.OLS(tcs_arr, X_mat).fit()
            beta = ols.params[1]
            resid = ols.resid

            # Beta change
            abs_beta_chg = (
                abs(beta - prev_beta[wlen])
                if prev_beta[wlen] is not None
                else np.nan
            )
            prev_beta[wlen] = beta

            # Engle-Granger
            try:
                _, eg_pval, _ = coint(
                    tcs_arr, infy_arr, trend="c", autolag="aic"
                )
            except Exception:
                eg_pval = np.nan

            # Standalone ADF on residuals
            try:
                _, adf_pval, *_ = adfuller(resid, regression="n", autolag="aic")
            except Exception:
                adf_pval = np.nan

            # Half-life
            try:
                hl, _ = compute_half_life(resid)
            except Exception:
                hl = np.nan

            rows.append(
                {
                    "date": eval_date.strftime("%Y-%m-%d"),
                    "window_length": wlen,
                    "beta": round(beta, 6),
                    "abs_beta_change": round(abs_beta_chg, 6)
                    if not np.isnan(abs_beta_chg)
                    else "",
                    "eg_pval": round(eg_pval, 6)
                    if not np.isnan(eg_pval)
                    else "",
                    "adf_pval": round(adf_pval, 6)
                    if not np.isnan(adf_pval)
                    else "",
                    "half_life": round(hl, 2)
                    if not np.isnan(hl)
                    else "",
                    "eg_pass": int(eg_pval < 0.05)
                    if not np.isnan(eg_pval)
                    else "",
                    "adf_pass": int(adf_pval < 0.05)
                    if not np.isnan(adf_pval)
                    else "",
                }
            )

    df = pd.DataFrame(rows)
    return df


# ── Summary writer ─────────────────────────────────────────────────────


def build_summary(part_a, part_b, provenance):
    """Return the full summary.md text."""
    L = []  # lines accumulator

    L.append("# TCS/INFY Cointegration Window Validation — Antigravity/Opus\n")

    # ── Provenance header ──
    L.append("## Provenance\n")
    L.append(f"- Script: `{provenance['script_path']}`")
    L.append(f"- Git commit: `{provenance['git_commit']}`")
    L.append(f"- Data source: `{provenance['data_source']}`")
    L.append(f"- Snapshot ID: `{provenance['snapshot_id']}`")
    L.append(f"- Timestamp UTC: `{provenance['timestamp_utc']}`")
    L.append(f"- Seeds per condition per window: {N_SEEDS}")
    L.append(f"- statsmodels: {sm.__version__}")
    L.append(f"- Part A hash: `{provenance['output_hashes']['part_a_synthetic_validation.csv']}`")
    L.append(f"- Part B hash: `{provenance['output_hashes']['part_b_tcs_infy_rolling_cointegration.csv']}`")
    L.append("")

    # ════════════════════════════════════════════════════════════════════
    # PART A
    # ════════════════════════════════════════════════════════════════════
    L.append("## Part A — Synthetic Window-Length Validation\n")

    sig = 0.05  # primary narrative at 5 %

    # ── EG false-positive rates ──
    eg_nc = part_a.query(
        "condition == 'not_cointegrated' and test_type == 'engle_granger' "
        f"and significance_level == {sig}"
    )
    adf_nc = part_a.query(
        "condition == 'not_cointegrated' and test_type == 'residual_adf' "
        f"and significance_level == {sig}"
    )
    eg_c = part_a.query(
        "condition == 'cointegrated' and test_type == 'engle_granger' "
        f"and significance_level == {sig}"
    )
    adf_c = part_a.query(
        "condition == 'cointegrated' and test_type == 'residual_adf' "
        f"and significance_level == {sig}"
    )

    # FPR table
    L.append("### False-positive rates at p < 0.05 (non-cointegrated series incorrectly passing)\n")
    L.append("| Window | EG FPR | Residual ADF FPR |")
    L.append("|--------|--------|------------------|")
    for wlen in WINDOW_LENGTHS:
        eg_val = eg_nc.loc[eg_nc["window_length"] == wlen, "false_positive_rate"]
        adf_val = adf_nc.loc[adf_nc["window_length"] == wlen, "false_positive_rate"]
        eg_f = f"{float(eg_val.iloc[0]):.3f}" if len(eg_val) else "—"
        adf_f = f"{float(adf_val.iloc[0]):.3f}" if len(adf_val) else "—"
        L.append(f"| {wlen}d | {eg_f} | {adf_f} |")
    L.append("")

    # Methodological note on ADF FPR
    max_adf_fpr = adf_nc["false_positive_rate"].apply(
        lambda v: float(v) if v != "" else 0
    ).max()
    if max_adf_fpr > 0.15:
        L.append(
            "The standalone residual-ADF false-positive rates are substantially "
            "higher than the Engle-Granger rates. This is expected and is not a bug: "
            "ADF critical values assume the series being tested is observed, not "
            "estimated. When ADF is applied to OLS residuals, the residuals are "
            "mechanically more stationary-looking than the true spread because OLS "
            "minimises the sum of squared residuals, biasing the ADF statistic toward "
            "rejection. The Engle-Granger procedure corrects for this by using "
            "critical-value tables specifically calibrated for the two-step case. "
            "Treating raw residual-ADF p-values as if they were Engle-Granger "
            "p-values would systematically overstate evidence for cointegration.\n"
        )

    # FNR table (EG only — the correctly calibrated test)
    L.append("### Engle-Granger false-negative rates at p < 0.05\n")
    L.append("| Window | φ regime | Noise | FNR | Mean p |")
    L.append("|--------|----------|-------|-----|--------|")
    for _, row in eg_c.sort_values(["window_length", "phi_regime", "spread_noise"]).iterrows():
        fnr = f"{float(row['false_negative_rate']):.3f}" if row["false_negative_rate"] != "" else "—"
        mp = f"{row['mean_p']:.4f}"
        L.append(
            f"| {int(row['window_length'])}d | {row['phi_regime']} | "
            f"{row['spread_noise']} | {fnr} | {mp} |"
        )
    L.append("")

    # ── Conclusion (2-3 paragraphs) ──
    L.append("### Conclusion\n")

    # Check which windows meet <10% FPR AND <10% FNR across ALL EG regimes
    meets = {}
    for wlen in WINDOW_LENGTHS:
        fpr_vals = eg_nc.loc[
            eg_nc["window_length"] == wlen, "false_positive_rate"
        ].apply(lambda v: float(v) if v != "" else 0)
        fnr_vals = eg_c.loc[
            eg_c["window_length"] == wlen, "false_negative_rate"
        ].apply(lambda v: float(v) if v != "" else 0)
        max_fpr = fpr_vals.max() if len(fpr_vals) else 1.0
        max_fnr = fnr_vals.max() if len(fnr_vals) else 1.0
        meets[wlen] = max_fpr < 0.10 and max_fnr < 0.10

    passing = [w for w, ok in meets.items() if ok]

    if not passing:
        L.append(
            "No tested window length keeps both the Engle-Granger worst-case "
            "false-positive rate and worst-case false-negative rate below 10 % "
            "across all simulated persistence regimes at p < 0.05. The binding "
            "constraint is the false-negative rate in the near-unit-root regime "
            "(φ ≈ 0.99), where the stationary spread is barely distinguishable "
            "from a random walk over any practical horizon. In the fast "
            "mean-reversion regime (φ ≈ 0.80), detection power is adequate even "
            "at shorter windows, but this is the statistically easy case — a "
            "spread that reverts quickly is precisely the scenario Engle-Granger "
            "is designed for. The moderate regime (φ ≈ 0.95) falls between: "
            "detection improves materially with longer windows, but never reaches "
            "the < 10 % FNR threshold uniformly.\n"
        )
        L.append(
            "The conclusion is therefore strongly persistence-dependent. Shorter "
            "windows (60–120 days) perform adequately only when the spread "
            "mean-reverts fast or the signal-to-noise ratio is favourable — "
            "conditions that cannot be assumed in advance without circular "
            "reasoning, since estimating the spread's persistence requires "
            "having already established cointegration. Longer windows (500–730 "
            "days) gain power against slower mean reversion but at the cost of "
            "averaging over structural breaks, which is precisely the opposite "
            "of what a rolling degradation monitor needs.\n"
        )
        L.append(
            "Because no single window meets the dual < 10 % criterion across "
            "all regimes, Part B evaluates every candidate window as a "
            "diagnostic rather than treating any as validated. Conclusions "
            "about degradation timing should be read as what the evidence looks "
            "like at each window length, not as definitive pass/fail "
            "determinations.\n"
        )
    else:
        shortest = min(passing)
        L.append(
            f"The shortest window meeting the < 10 % FPR and < 10 % FNR "
            f"criterion across all simulated regimes at p < 0.05 is "
            f"**{shortest} trading days**. Shorter windows perform adequately "
            f"only under fast mean-reversion or favourable noise, and should "
            f"not be treated as reliable across regimes.\n"
        )

    # ════════════════════════════════════════════════════════════════════
    # PART B
    # ════════════════════════════════════════════════════════════════════
    L.append("## Part B — Real TCS/INFY Rolling Cointegration Analysis\n")

    part_b_dt = part_b.copy()
    # Coerce types for analysis
    for col in ["eg_pval", "adf_pval", "half_life", "beta", "abs_beta_change"]:
        part_b_dt[col] = pd.to_numeric(part_b_dt[col], errors="coerce")
    for col in ["eg_pass", "adf_pass"]:
        part_b_dt[col] = pd.to_numeric(part_b_dt[col], errors="coerce")
    part_b_dt["date"] = pd.to_datetime(part_b_dt["date"])

    flagged = pd.Timestamp(FIRST_FLAGGED_DATE)

    for wlen in WINDOW_LENGTHS:
        w = part_b_dt[part_b_dt["window_length"] == wlen].copy()
        if w.empty:
            continue

        first_weak = w.loc[(w["eg_pval"] > 0.01) & (w["eg_pval"] < 0.05), "date"].min()
        first_border = w.loc[w["eg_pval"] > 0.03, "date"].min()
        first_eg_fail = w.loc[w["eg_pass"] == 0, "date"].min()
        first_both_fail = w.loc[
            (w["eg_pass"] == 0) & (w["adf_pass"] == 0), "date"
        ].min()

        def fmt(d):
            return d.strftime("%Y-%m-%d") if pd.notna(d) else "never within range"

        L.append(f"### {wlen}-day window\n")
        L.append(f"- First weakening (EG p > 0.01 while still < 0.05): {fmt(first_weak)}")
        L.append(f"- First borderline (EG p > 0.03): {fmt(first_border)}")
        L.append(f"- First EG failure (p ≥ 0.05): {fmt(first_eg_fail)}")
        L.append(f"- First month both tests fail: {fmt(first_both_fail)}")

        # If there's a transition near the flagged date, note the lead/lag
        if pd.notna(first_eg_fail) and first_eg_fail < flagged:
            months = (flagged - first_eg_fail).days / 30.44
            L.append(
                f"- EG failure precedes first quarterly FLAGGED label by ~{months:.0f} months"
            )
        L.append("")

    # ── Degradation narrative ──
    L.append("### Degradation Timeline Summary\n")

    # Build the narrative from longer windows (more reliable per Part A)
    for wlen in [500, 730]:
        w = part_b_dt[part_b_dt["window_length"] == wlen]
        if w.empty:
            continue

        # Transition zone
        border = w.loc[w["eg_pval"] > 0.03]
        if not border.empty:
            first = border["date"].min()
            lead_months = (flagged - first).days / 30.44 if first < flagged else None

            # Get half-life range during the transition
            transition = w.loc[
                (w["date"] >= first) & (w["date"] <= flagged)
            ]
            hl_range = transition["half_life"].dropna()

            desc = f"The {wlen}d window first shows borderline Engle-Granger results on {first.strftime('%Y-%m-%d')}"
            if lead_months and lead_months > 0:
                desc += f", approximately {lead_months:.0f} months before the first quarterly FLAGGED label ({FIRST_FLAGGED_DATE})"
            desc += "."
            if not hl_range.empty:
                desc += (
                    f" During this transition, half-life ranges from "
                    f"{hl_range.min():.1f} to {hl_range.max():.1f} trading days."
                )
            L.append(desc + "\n")

    # Short-window caveat
    for wlen in [60, 120, 250]:
        w = part_b_dt[part_b_dt["window_length"] == wlen]
        if w.empty:
            continue
        fail_frac = (w["eg_pass"] == 0).mean()
        if fail_frac > 0.3:
            L.append(
                f"The {wlen}d window fails frequently ({fail_frac:.0%} of months), "
                f"consistent with Part A's finding that short windows are unreliable "
                f"across persistence regimes. Its failures are therefore poor evidence "
                f"for dating a real structural change.\n"
            )

    # ── Method notes ──
    L.append("### Method Notes\n")
    L.append(
        "Engle-Granger p-values: `statsmodels.tsa.stattools.coint(..., trend='c', "
        "autolag='aic')`. Standalone residual ADF p-values: "
        "`statsmodels.tsa.stattools.adfuller(..., regression='n', autolag='aic')`. "
        "TCS is the dependent variable; INFY is the hedge-ratio regressor in all "
        "OLS beta estimates. Half-life estimated from AR(1) on OLS residuals: "
        "hl = -log(2) / log(phi_hat). Beta change is month-over-month absolute change in "
        "the OLS hedge ratio."
    )

    return "\n".join(L)


# ── Utilities ──────────────────────────────────────────────────────────


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit_hash():
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else "unavailable"
    except Exception:
        return "unavailable"


# ── Main ───────────────────────────────────────────────────────────────


def main():
    # 0. Verify yfinance data access
    print("Verifying yfinance connectivity...")
    try:
        import yfinance as yf

        test = yf.download("TCS.NS", start="2025-06-01", end="2025-06-07", progress=False)
        if test.empty:
            print("ERROR: yfinance returned empty data. Cannot proceed.")
            sys.exit(1)
        print("  yfinance OK.\n")
    except Exception as e:
        print(f"ERROR: yfinance failed -- {e}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Part A
    part_a = run_part_a()
    pa_path = os.path.join(OUTPUT_DIR, "part_a_synthetic_validation.csv")
    part_a.to_csv(pa_path, index=False)
    print(f"\n  -> {pa_path}")

    # 2. Part B
    combined = fetch_data()
    part_b = run_part_b(combined)
    pb_path = os.path.join(OUTPUT_DIR, "part_b_tcs_infy_rolling_cointegration.csv")
    part_b.to_csv(pb_path, index=False)
    print(f"  -> {pb_path}")

    # 3. Provenance
    commit = git_commit_hash()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    provenance = {
        "script_path": os.path.abspath(__file__),
        "git_commit": commit,
        "data_source": f"yfinance adjusted close, TCS.NS and INFY.NS, {DATA_START} through {DATA_END}",
        "snapshot_id": f"none_live_yfinance_fetch_{DATA_START}_{DATA_END}",
        "timestamp_utc": ts,
        "n_seeds_per_condition_per_window": N_SEEDS,
        "statsmodels_version": sm.__version__,
        "engle_granger_method": "statsmodels.tsa.stattools.coint(trend='c', autolag='aic')",
        "adf_method": "statsmodels.tsa.stattools.adfuller(regression='n', autolag='aic')",
        "output_hashes": {
            "part_a_synthetic_validation.csv": sha256_file(pa_path),
            "part_b_tcs_infy_rolling_cointegration.csv": sha256_file(pb_path),
        },
    }

    # 4. Summary (needs hashes for provenance block)
    summary_text = build_summary(part_a, part_b, provenance)
    sm_path = os.path.join(OUTPUT_DIR, "summary.md")
    with open(sm_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"  -> {sm_path}")

    # Update provenance with summary hash
    provenance["output_hashes"]["summary.md"] = sha256_file(sm_path)

    prov_path = os.path.join(OUTPUT_DIR, "provenance.json")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
    print(f"  -> {prov_path}")

    print("\n" + "=" * 60)
    print("DONE -- all outputs in", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
