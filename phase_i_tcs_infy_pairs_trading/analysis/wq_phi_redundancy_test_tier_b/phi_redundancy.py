import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
CSV_PATH = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def n_eff_of(series):
    """Lag-1-autocorrelation-based effective sample size, same convention as
    wq_healthy_core_leading_drift_tier_b."""
    rho = pd.Series(series).autocorr(lag=1)
    if pd.isna(rho):
        rho = 0.0
    rho = max(min(rho, 0.99), -0.99)
    n_eff = len(series) * (1 - rho) / (1 + rho)
    return rho, n_eff

def check_level_shift(series, dates):
    """Pre/post 2024-01-31 mean-shift test on a residual series, using
    n_eff-adjusted standard errors. Unchanged from the original script,
    EXCEPT it is now called on differenced-regression residuals,
    not on levels-regression residuals -- see run_metric_test()."""
    pre_mask = (dates <= pd.to_datetime('2024-01-31')).values
    post_mask = (dates > pd.to_datetime('2024-01-31')).values

    y_pre = series[pre_mask]
    y_post = series[post_mask]

    rho, n_eff = n_eff_of(series)
    n_eff_factor = (1 - rho) / (1 + rho) if (1 + rho) != 0 else 1e-5
    n_eff_pre = len(y_pre) * n_eff_factor
    n_eff_post = len(y_post) * n_eff_factor

    if n_eff_pre < 1e-5 or n_eff_post < 1e-5:
        return rho, n_eff, 0.0, "Not enough data"

    var_pre = np.var(y_pre, ddof=1) if len(y_pre) > 1 else 0
    var_post = np.var(y_post, ddof=1) if len(y_post) > 1 else 0

    se = np.sqrt(var_pre / max(n_eff_pre, 1e-5) + var_post / max(n_eff_post, 1e-5))
    if se < 1e-9:
        return rho, n_eff, 0.0, "Zero variance"

    t_stat = (np.mean(y_post) - np.mean(y_pre)) / se

    if abs(t_stat) > 2.0:
        verdict = f"Shift Detected (|t|={abs(t_stat):.2f})"
    else:
        verdict = f"No Structure (|t|={abs(t_stat):.2f})"

    return rho, n_eff, t_stat, verdict

def adf_on_residuals(resid):
    """Spurious-regression check: is the LEVELS regression's residual
    itself stationary? If not (p >= 0.05), the levels R^2 is not trustworthy
    on its own -- two trending series can produce a high R^2 with no real
    relationship. Same adfuller convention as the rest of this project
    (regression='n', autolag='aic'), applied here to a residual rather
    than the spread itself."""
    try:
        result = adfuller(resid, regression="n", autolag="aic")
        return float(result[1])
    except Exception:
        return float("nan")

def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))

def run_metric_test(y_levels, phi, dates, quadratic, label):
    """
    Runs the full battery for one metric:
      - levels regression (kept for comparison, NOT used for classification)
      - ADF test on levels-regression residuals (spurious-regression check)
      - differenced regression (PRIMARY, robust to shared trends)
      - level-shift test on the differenced-regression's residuals
    """
    # --- Levels regression (reference only) ---
    if quadratic:
        X_levels = sm.add_constant(np.column_stack((phi, phi**2)))
    else:
        X_levels = sm.add_constant(phi)
    model_levels = sm.OLS(y_levels, X_levels).fit()
    r2_levels = model_levels.rsquared
    adf_p_on_resid = adf_on_residuals(model_levels.resid)
    spurious_flag = "SPURIOUS RISK (resid non-stationary)" if adf_p_on_resid >= 0.05 else "OK (resid stationary)"

    # --- Differenced regression (primary) ---
    dy = np.diff(y_levels)
    dphi = np.diff(phi)
    if quadratic:
        dphi2 = np.diff(phi**2)
        X_diff = sm.add_constant(np.column_stack((dphi, dphi2)))
    else:
        X_diff = sm.add_constant(dphi)
    model_diff = sm.OLS(dy, X_diff).fit()
    r2_diff = model_diff.rsquared

    # Level-shift test on the DIFFERENCED regression's residuals
    # (dates trimmed by 1 to match np.diff length)
    dates_trimmed = dates.iloc[1:]
    rho, n_eff, t_stat, shift_verdict = check_level_shift(model_diff.resid, dates_trimmed)

    return {
        "metric": label,
        "r2_levels": r2_levels,
        "adf_p_on_levels_resid": adf_p_on_resid,
        "spurious_flag": spurious_flag,
        "r2_diff": r2_diff,
        "rho": rho,
        "n_eff": n_eff,
        "t_stat": t_stat,
        "shift_verdict": shift_verdict,
    }

def main():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if not line.startswith('#'):
            start_idx = i
            break

    df = pd.read_csv(CSV_PATH, skiprows=start_idx)
    df['date'] = pd.to_datetime(df['date'])

    results_dict = {500: [], 730: []}

    for window in [500, 730]:
        df_w = df[df['window_length'] == window].copy()
        dates = df_w['date']
        spread_std = df_w['spread_std'].values
        spread_phi = df_w['spread_phi'].values
        eg_p = df_w['engle_granger_p_value'].values
        adf_p = df_w['adf_p_value'].values

        sigma_eps_sq = (spread_std**2) * (1 - spread_phi**2)

        results_dict[window].append(
            run_metric_test(sigma_eps_sq, spread_phi, dates, quadratic=False, label="Residual Variance (sigma_eps_sq)")
        )
        results_dict[window].append(
            run_metric_test(logit(eg_p), spread_phi, dates, quadratic=True, label="EG p-value (logit)")
        )
        results_dict[window].append(
            run_metric_test(logit(adf_p), spread_phi, dates, quadratic=True, label="ADF p-value (logit)")
        )

    out_lines = []
    classifications = []

    for window in [500, 730]:
        out_lines.append(f"### {window}d Core")
        out_lines.append("| Metric | R2 (levels) | ADF-on-resid p | R2 (first-diff, PRIMARY) | n_eff | Shift verdict |")
        out_lines.append("|---|---|---|---|---|---|")

        num_real_signal = 0
        for r in results_dict[window]:
            out_lines.append(
                f"| {r['metric']} | {r['r2_levels']:.4f} | {r['adf_p_on_levels_resid']:.4f} ({r['spurious_flag']}) "
                f"| {r['r2_diff']:.4f} | {r['n_eff']:.1f} (rho={r['rho']:.2f}) | {r['shift_verdict']} |"
            )
            # Classification now driven by the DIFFERENCED r2 (robust to spurious
            # trend-sharing) and the shift test on differenced-regression residuals,
            # NOT the levels r2 alone. A metric counts as carrying real independent
            # information if EITHER the differenced relationship is weak (r2_diff low,
            # meaning changes in phi don't explain changes in the metric) OR a genuine
            # shift shows up in what's left after accounting for phi's influence.
            low_diff_r2 = r['r2_diff'] < 0.3
            real_shift = "Shift Detected" in r['shift_verdict']
            if low_diff_r2 or real_shift:
                num_real_signal += 1

        if num_real_signal == 0:
            cls_name = "Case 1 (pure redundancy)"
        elif num_real_signal == 1:
            cls_name = "Case 2 (partial redundancy)"
        else:
            cls_name = "Case 3 (multiple latent variables)"

        classifications.append(
            f"- **{window}d window**: {cls_name}. {num_real_signal}/3 metrics show real "
            f"independent information (low first-differenced R2 against phi, and/or a "
            f"genuine post-Jan-2024 shift in the differenced-regression residuals)."
        )
        out_lines.append("")

    out_lines.append("### Classification Summary")
    out_lines.extend(classifications)
    out_lines.append("")
    out_lines.append(
        "*Methodology note: classification is now based on the FIRST-DIFFERENCED "
        "regression R2 and the shift test on ITS residuals, not the levels R2. "
        "The levels R2 and the ADF-on-residuals check are reported for reference "
        "and to flag spurious-regression risk (two trending series can produce a "
        "high levels R2 with no real relationship) -- treat a large gap between "
        "levels R2 and first-diff R2, combined with a non-stationary levels "
        "residual, as a sign the levels R2 was inflated.*"
    )

    output_content = "\n".join(out_lines)

    commit = get_git_commit()
    script_path = str(Path(__file__).resolve())
    timestamp = datetime.now(timezone.utc).isoformat()
    content_hash = hashlib.sha256(output_content.encode('utf-8')).hexdigest()

    prov_header = f"""<!--
script_path: {script_path}
git_commit: {commit}
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: {timestamp}
output_content_sha256: {content_hash}
superseded_entry: wq_phi_redundancy_test_tier_b (2026-07-08 run -- classification
  logic did not use the reported correlation diagnostic, and the levels
  regression was not checked for spurious-regression risk)
-->
"""

    final_output = prov_header + "\n## wq_phi_redundancy_test_tier_b_v2\n\n" + output_content + "\n"

    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)

if __name__ == "__main__":
    main()