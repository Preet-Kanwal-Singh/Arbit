import pandas as pd
import numpy as np
import statsmodels.api as sm
import json
import hashlib
from datetime import datetime, timezone
import os
import subprocess

def safe_logit(p):
    p = np.clip(p, 1e-10, 1 - 1e-10)
    return np.log(p / (1 - p))

def bootstrap_granger(y, x, lag=1, n_boot=2000, seed=42):
    """
    Test if x Granger-causes y (y is diff logit EG, x is diff vol resid)
    Using residual bootstrap under the null hypothesis (gamma = 0).
    """
    df = pd.DataFrame({'y': y, 'x': x}).dropna()
    y_vals = df['y'].values
    x_vals = df['x'].values
    T = len(y_vals)
    
    if T <= lag + 1:
        return np.nan, np.nan
        
    # Restricted model: y_t = alpha + beta * y_{t-1} + u_t
    # Unrestricted model: y_t = alpha + beta * y_{t-1} + gamma * x_{t-1} + v_t
    Y = y_vals[lag:]
    X_restr = np.column_stack([np.ones(T - lag), y_vals[:-lag]])
    X_unrestr = np.column_stack([np.ones(T - lag), y_vals[:-lag], x_vals[:-lag]])
    
    model_restr = sm.OLS(Y, X_restr).fit()
    model_unrestr = sm.OLS(Y, X_unrestr).fit()
    
    ssr_restr = model_restr.ssr
    ssr_unrestr = model_unrestr.ssr
    
    q = 1 # Number of restrictions
    df_resid = model_unrestr.df_resid
    F_stat = ((ssr_restr - ssr_unrestr) / q) / (ssr_unrestr / df_resid) if ssr_unrestr > 0 else 0
    
    residuals = model_restr.resid
    residuals = residuals - np.mean(residuals) # center residuals
    
    np.random.seed(seed)
    F_boot = np.zeros(n_boot)
    
    for i in range(n_boot):
        u_boot = np.random.choice(residuals, size=T-lag, replace=True)
        Y_boot = model_restr.predict(X_restr) + u_boot
        
        m_r_boot = sm.OLS(Y_boot, X_restr).fit()
        m_u_boot = sm.OLS(Y_boot, X_unrestr).fit()
        
        ssr_r_b = m_r_boot.ssr
        ssr_u_b = m_u_boot.ssr
        
        if ssr_u_b > 0:
            F_b = ((ssr_r_b - ssr_u_b) / q) / (ssr_u_b / m_u_boot.df_resid)
        else:
            F_b = 0
        F_boot[i] = F_b
        
    p_value = np.mean(F_boot >= F_stat)
    return p_value, F_stat

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def main():
    base_dir = r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit"
    tcs_infy = pd.read_csv(os.path.join(base_dir, "data", "snapshots", "tcs_infy_v2_2026-07-11", "ohlcv.csv"), parse_dates=["date"])
    nifty_it = pd.read_csv(os.path.join(base_dir, "data", "snapshots", "nifty_it_benchmark_v1_2026-07-11", "ohlcv.csv"), parse_dates=["date"])
    
    tcs = tcs_infy[tcs_infy["ticker"] == "TCS.NS"].set_index("date")["volume"].rename("TCS")
    infy = tcs_infy[tcs_infy["ticker"] == "INFY.NS"].set_index("date")["volume"].rename("INFY")
    nsei = nifty_it[nifty_it["ticker"] == "^NSEI"].set_index("date")["volume"].rename("NSEI")
    
    df = pd.concat([tcs, infy, nsei], axis=1).dropna()
    df = df[df.index >= "2018-09-06"]
    
    df = df[(df["TCS"] > 0) & (df["INFY"] > 0) & (df["NSEI"] > 0)].copy()
    
    for col in ["TCS", "INFY", "NSEI"]:
        df[f"log_{col}"] = np.log(df[col])
        
    df["dow"] = df.index.dayofweek
    dow_dummies = pd.get_dummies(df["dow"], prefix="dow", drop_first=True).astype(int)
    df = pd.concat([df, dow_dummies], axis=1)
    
    dates_500d = "2022-01-31"
    dates_730d = "2023-04-28"
    
    idx_500d = df.index.get_loc(pd.to_datetime(dates_500d))
    idx_730d = df.index.get_loc(pd.to_datetime(dates_730d))
    
    event_500d_idx = df.index[idx_500d-20:idx_500d]
    event_730d_idx = df.index[idx_730d-20:idx_730d]
    
    df["event_500d"] = 0
    df.loc[event_500d_idx, "event_500d"] = 1
    
    df["event_730d"] = 0
    df.loc[event_730d_idx, "event_730d"] = 1
    
    results = {}
    
    X_base = sm.add_constant(df[["log_NSEI"] + list(dow_dummies.columns)])
    X_full = sm.add_constant(df[["log_NSEI", "event_500d", "event_730d"] + list(dow_dummies.columns)])
    
    # Run regressions for TCS and INFY
    for ticker in ["TCS", "INFY"]:
        y = df[f"log_{ticker}"]
        model = sm.OLS(y, X_full).fit(cov_type="HC3")
        
        # Calculate residuals from base model (no event dummies) for Part B
        base_model = sm.OLS(y, X_base).fit()
        resid = base_model.resid
        resid_monthly = resid.resample("ME").mean()
        
        results[ticker] = {
            "model": model,
            "resid_monthly": resid_monthly
        }
    
    # Part A Output formatting
    part_a_md = "### Part A: Abnormal Volume Event Study (CALT)\n"
    part_a_md += "| Ticker | Core | CALT (Coeff) | HC3 p-value | Result |\n"
    part_a_md += "|---|---|---|---|---|\n"
    
    part_a_flags = 0
    for ticker in ["TCS", "INFY"]:
        for core, dummy_col in [("500d", "event_500d"), ("730d", "event_730d")]:
            coef = results[ticker]["model"].params[dummy_col]
            pval = results[ticker]["model"].pvalues[dummy_col]
            flag = coef > 0 and pval < 0.05
            if flag:
                part_a_flags += 1
            res_str = "Positive/Significant" if flag else ("Empty (Positive, NS)" if coef > 0 else "Empty (Negative)")
            part_a_md += f"| {ticker} | {core} | {coef:.5f} | {pval:.5f} | {res_str} |\n"
            
    # Part B: Granger Causality
    rolling_metrics = pd.read_csv(os.path.join(base_dir, "phase_i_tcs_infy_pairs_trading", "analysis", "claim_002_healthy_episode_characterization", "codex_tier_a", "rolling_metrics.csv"), comment="#")
    rolling_metrics["date"] = pd.to_datetime(rolling_metrics["date"])
    
    part_b_md = "### Part B: Granger Causality (Volume -> logit EG p-value)\n"
    part_b_md += "| Ticker | Core | Bootstrap F | Bootstrap p-value | Result |\n"
    part_b_md += "|---|---|---|---|---|\n"
    
    part_b_flags = 0
    for ticker in ["TCS", "INFY"]:
        resid_monthly = results[ticker]["resid_monthly"]
        
        for core, (start_dt, end_dt), win_len in [
            ("500d", ("2020-01-31", "2021-12-31"), 500),
            ("730d", ("2020-12-31", "2023-03-31"), 730)
        ]:
            eg_data = rolling_metrics[rolling_metrics["window_length"] == win_len].copy()
            eg_data = eg_data.set_index("date")["eg_p"]
            eg_data = eg_data[(eg_data.index >= pd.to_datetime(start_dt)) & (eg_data.index <= pd.to_datetime(end_dt))]
            
            # logit transform
            logit_eg = eg_data.apply(safe_logit)
            
            # Alignment and differencing
            merged = pd.concat([logit_eg, resid_monthly], axis=1, join="inner")
            merged.columns = ["logit_eg", "resid"]
            merged_diff = merged.diff().dropna()
            
            pval, fstat = bootstrap_granger(y=merged_diff["logit_eg"], x=merged_diff["resid"], lag=1, n_boot=2000)
            flag = pval < 0.05
            if flag:
                part_b_flags += 1
            res_str = "Significant" if flag else "Empty"
            part_b_md += f"| {ticker} | {core} | {fstat:.4f} | {pval:.4f} | {res_str} |\n"

    # Combined Read
    combined_md = "### Classification Summary\n"
    if part_a_flags == 0 and part_b_flags == 0:
        combined_md += "**Verdict:** Empty. Both parts returned empty. This is a confirmed null on volume, converging with the volatility-redundancy finding. No third test is scoped.\n"
    else:
        combined_md += f"**Verdict:** Signal detected. Part A had {part_a_flags} flags, Part B had {part_b_flags} flags. This requires a follow-up decision.\n"

    # Limitation note
    limitation_note = "\n*Note: `^NSEI` is a broad-market control, not a sector control. The original reasoning — that TCS/INFY's volume is more likely contaminated by IT-sector-specific common factors than by generic market-wide volume — still holds and is not addressed by this substitution (`^CNXIT` and `ITBEES.NS` both failed a structural data-quality check and were dropped, not judged less relevant). Any result from this pass, positive or negative, is a market-adjusted finding only. It does not rule out a sector-specific volume relationship a market-wide control can't isolate — that channel remains genuinely untested, not settled by this result, and should not be cited as closed.*\n"

    output_content = f"## wq_volume_signal_test_tier_b_v2\n\n{part_a_md}\n{part_b_md}\n{combined_md}{limitation_note}"
    
    out_hash = hash_content(output_content)
    timestamp = datetime.now(timezone.utc).isoformat()
    script_path = os.path.abspath(__file__)
    commit = get_git_commit()
    
    header = f"<!--\nscript_path: {script_path}\ngit_commit: {commit}\nsnapshot_id: tcs_infy_v2_2026-07-11 (Volume) & nifty_it_benchmark_v1_2026-07-11 (^NSEI)\ntimestamp_utc: {timestamp}\noutput_content_sha256: {out_hash}\n-->\n\n"
    
    full_output = header + output_content
    
    with open(os.path.join(base_dir, "phase_i_tcs_infy_pairs_trading", "ledger", "worklog", "worklog_tier_b.md"), "a", encoding="utf-8") as f:
        f.write("\n" + full_output + "\n")
        
    print("Done. Appended to worklog_tier_b.md")
    print(output_content)

if __name__ == "__main__":
    main()
