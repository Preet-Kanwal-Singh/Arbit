import numpy as np
import pandas as pd
import statsmodels.api as sm
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / "tcs_infy_v1_2026-07-04"
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
OUT_DIR = ROOT / "analysis" / "wq_recompute_episode1_beta_range"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).sort_values("date")
    df = df.dropna(subset=["TCS.NS", "INFY.NS"])
    df.set_index("date", inplace=True)
    
    ep1_start = pd.to_datetime("2018-01-01")
    ep1_end = pd.to_datetime("2023-12-31")
    
    y_full = np.log(df["TCS.NS"])
    x_full = np.log(df["INFY.NS"])
    
    df["year_month"] = df.index.to_period("M")
    month_ends = df.groupby("year_month").apply(lambda x: x.index.max())
    
    month_ends = month_ends[(month_ends >= ep1_start) & (month_ends <= ep1_end)]
    
    WINDOWS = [60, 120, 250, 500, 730]
    results = []
    
    for i in range(len(month_ends)):
        me_date = month_ends.iloc[i]
        loc = df.index.get_loc(me_date)
        
        for n in WINDOWS:
            start_loc = loc - n + 1
            if start_loc < 0:
                continue
                
            y_win = y_full.iloc[start_loc : loc + 1].values
            x_win = x_full.iloc[start_loc : loc + 1].values
            
            X_win = sm.add_constant(x_win)
            model = sm.OLS(y_win, X_win).fit()
            beta = model.params[1]
            
            results.append({
                "date": me_date.strftime("%Y-%m-%d"),
                "window_length": n,
                "beta": beta
            })
            
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(["date", "window_length"])
    
    res_df[["date", "window_length", "beta"]].to_csv(OUT_DIR / "beta_series.csv", index=False)
    
    b_min = res_df["beta"].min()
    b_max = res_df["beta"].max()
    b_mean = res_df["beta"].mean()
    b_median = res_df["beta"].median()
    b_std = res_df["beta"].std()
    
    first_obs = res_df.iloc[0]
    last_obs = res_df.iloc[-1]
    n_obs = len(res_df)
    
    summary_md = f"""# Episode 1 Recomputed Beta Range

This is a descriptive reconstruction of the rolling beta range observed during Episode 1 (2018-01-01 to 2023-12-31), computed directly from the frozen snapshot (`tcs_infy_v1_2026-07-04`).

**These values supersede the previously untraceable "0.20–1.91" figure, which is now deprecated.**

## Descriptive Statistics
- **Minimum β:** {b_min:.6f}
- **Maximum β:** {b_max:.6f}
- **Mean β:** {b_mean:.6f}
- **Median β:** {b_median:.6f}
- **Standard Deviation:** {b_std:.6f}
- **First Observation:** {first_obs['date']} (window: {first_obs['window_length']}d, β: {first_obs['beta']:.6f})
- **Last Observation:** {last_obs['date']} (window: {last_obs['window_length']}d, β: {last_obs['beta']:.6f})
- **Number of Observations:** {n_obs} month-end β calculations (across all defined rolling windows)

*Note: No smoothing, filtering, thresholding, or statistical inference was applied. The computation strictly followed the established rolling-beta implementation on the frozen snapshot.*
"""
    
    with open(OUT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)
        
    commit = get_git_commit()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    with open(OUT_DIR / "beta_series.csv", "rb") as f:
        csv_hash = hashlib.sha256(f.read()).hexdigest()
        
    with open(OUT_DIR / "summary.md", "rb") as f:
        md_hash = hashlib.sha256(f.read()).hexdigest()
        
    prov_data = {
        "snapshot_id": "tcs_infy_v1_2026-07-04",
        "git_commit": commit,
        "script_path": str(Path(__file__).resolve()),
        "execution_timestamp_utc": timestamp,
        "outputs": {
            "beta_series.csv": csv_hash,
            "summary.md": md_hash
        }
    }
    
    with open(OUT_DIR / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(prov_data, f, indent=2)
        
    prov_header = f"""<!--
script_path: {prov_data['script_path']}
git_commit: {commit}
snapshot_id: {prov_data['snapshot_id']}
timestamp_utc: {timestamp}
output_content_sha256: {md_hash}
-->
"""
    
    final_output = prov_header + "\n## wq_recompute_episode1_beta_range\n\n" + summary_md + "\n"
    
    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)

if __name__ == "__main__":
    main()
