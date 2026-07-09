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
OUT_DIR = ROOT / "analysis" / "wq_recompute_episode1_beta_range_v2"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def compute_beta_range(df, y_full, x_full, start_date_str, end_date_str, window_length):
    ep_start = pd.to_datetime(start_date_str)
    ep_end = pd.to_datetime(end_date_str)
    
    # Filter month ends to the core date range
    month_ends = df.groupby("year_month").apply(lambda x: x.index.max())
    month_ends = month_ends[(month_ends >= ep_start) & (month_ends <= ep_end)]
    
    results = []
    
    for i in range(len(month_ends)):
        me_date = month_ends.iloc[i]
        loc = df.index.get_loc(me_date)
        
        start_loc = loc - window_length + 1
        if start_loc < 0:
            continue
            
        y_win = y_full.iloc[start_loc : loc + 1].values
        x_win = x_full.iloc[start_loc : loc + 1].values
        
        X_win = sm.add_constant(x_win)
        model = sm.OLS(y_win, X_win).fit()
        beta = model.params[1]
        
        results.append({
            "date": me_date.strftime("%Y-%m-%d"),
            "beta": beta
        })
        
    res_df = pd.DataFrame(results).sort_values("date")
    return res_df

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).sort_values("date")
    df = df.dropna(subset=["TCS.NS", "INFY.NS"])
    df.set_index("date", inplace=True)
    df["year_month"] = df.index.to_period("M")
    
    y_full = np.log(df["TCS.NS"])
    x_full = np.log(df["INFY.NS"])
    
    # 500d Core
    df_500 = compute_beta_range(df, y_full, x_full, "2020-01-31", "2021-12-31", 500)
    df_500.to_csv(OUT_DIR / "beta_series_500d_core.csv", index=False)
    
    # 730d Core
    df_730 = compute_beta_range(df, y_full, x_full, "2020-12-31", "2023-03-31", 730)
    df_730.to_csv(OUT_DIR / "beta_series_730d_core.csv", index=False)
    
    # Descriptive statistics
    def get_stats(res_df):
        return {
            "min": res_df["beta"].min(),
            "max": res_df["beta"].max(),
            "mean": res_df["beta"].mean(),
            "median": res_df["beta"].median(),
            "std": res_df["beta"].std(),
            "first": res_df.iloc[0],
            "last": res_df.iloc[-1],
            "n_obs": len(res_df)
        }
        
    stats_500 = get_stats(df_500)
    stats_730 = get_stats(df_730)
    
    summary_md = f"""# Episode 1 Recomputed Beta Range v2

This descriptive reconstruction replaces both the historically untraceable "0.20–1.91" figure and the flawed v1 recomputation (which incorrectly pooled multiple window lengths over an unestablished 2018–2023 date range).

The values below establish the authoritative reference for Episode 1 beta ranges, computed individually for each of the two established healthy cores using their matching window lengths, straight from the frozen snapshot (`tcs_infy_v1_2026-07-04`).

## 500d Strict Core (2020-01-31 to 2021-12-31)
- **Minimum β:** {stats_500['min']:.6f}
- **Maximum β:** {stats_500['max']:.6f}
- **Mean β:** {stats_500['mean']:.6f}
- **Median β:** {stats_500['median']:.6f}
- **Standard Deviation:** {stats_500['std']:.6f}
- **First Observation:** {stats_500['first']['date']} (β: {stats_500['first']['beta']:.6f})
- **Last Observation:** {stats_500['last']['date']} (β: {stats_500['last']['beta']:.6f})
- **Number of Observations:** {stats_500['n_obs']} month-end β calculations

## 730d Strict Core (2020-12-31 to 2023-03-31)
- **Minimum β:** {stats_730['min']:.6f}
- **Maximum β:** {stats_730['max']:.6f}
- **Mean β:** {stats_730['mean']:.6f}
- **Median β:** {stats_730['median']:.6f}
- **Standard Deviation:** {stats_730['std']:.6f}
- **First Observation:** {stats_730['first']['date']} (β: {stats_730['first']['beta']:.6f})
- **Last Observation:** {stats_730['last']['date']} (β: {stats_730['last']['beta']:.6f})
- **Number of Observations:** {stats_730['n_obs']} month-end β calculations

*Note: No smoothing, filtering, thresholding, or statistical inference was applied. The computation strictly followed the established rolling-beta implementation on the frozen snapshot.*
"""
    
    with open(OUT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)
        
    commit = get_git_commit()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    def file_hash(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    prov_data = {
        "snapshot_id": "tcs_infy_v1_2026-07-04",
        "git_commit": commit,
        "script_path": str(Path(__file__).resolve()),
        "execution_timestamp_utc": timestamp,
        "outputs": {
            "beta_series_500d_core.csv": file_hash(OUT_DIR / "beta_series_500d_core.csv"),
            "beta_series_730d_core.csv": file_hash(OUT_DIR / "beta_series_730d_core.csv"),
            "summary.md": file_hash(OUT_DIR / "summary.md")
        }
    }
    
    # Write provenance.json to disk (a requirement missing in v1)
    with open(OUT_DIR / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(prov_data, f, indent=2)
        
    prov_data["outputs"]["provenance.json"] = file_hash(OUT_DIR / "provenance.json")
    
    # Append to Tier B Worklog
    prov_header = f"""<!--
script_path: {prov_data['script_path']}
git_commit: {commit}
snapshot_id: {prov_data['snapshot_id']}
timestamp_utc: {timestamp}
output_content_sha256: {prov_data['outputs']['summary.md']}
-->
"""
    
    worklog_append = prov_header + "\n## wq_recompute_episode1_beta_range_v2\n\n"
    worklog_append += "> **Deviations from v1:**\n"
    worklog_append += "> 1. Fixed the date range to map strictly to the established 500d and 730d cores from `VERIFIED_FACTS.md` instead of a generic 2018-2023 boundary.\n"
    worklog_append += "> 2. Fixed the pooled window length issue: used 500d for the 500d core, and 730d for the 730d core, strictly separate.\n"
    worklog_append += "> 3. Fixed `beta_series.csv` column format by emitting two specific CSVs containing only `date` and `beta`.\n"
    worklog_append += "> 4. Fixed `provenance.json` serialization by exporting it as a standalone file instead of relying on manual copying.\n\n"
    worklog_append += summary_md + "\n"
    
    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(worklog_append)

if __name__ == "__main__":
    main()
