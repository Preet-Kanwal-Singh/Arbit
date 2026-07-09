import pandas as pd
import numpy as np
import statsmodels.api as sm
import math
import json
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

def analyze_drift(df_w, core_start, core_end, metrics):
    start_dt = pd.to_datetime(core_start)
    end_dt = pd.to_datetime(core_end)
    
    core_df = df_w[(df_w['date'] >= start_dt) & (df_w['date'] <= end_dt)].copy()
    core_df = core_df.sort_values('date').reset_index(drop=True)
    T = len(core_df)
    
    if T == 0:
        return []
        
    maxlags = math.floor(4 * ((T / 100.0) ** (2.0 / 9.0)))
    
    t_index = np.arange(T)
    X = sm.add_constant(t_index)
    
    results = []
    
    for metric in metrics:
        y = core_df[metric].values
        model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': maxlags})
        slope = model.params[1]
        tstat = model.tvalues[1]
        pvalue = model.pvalues[1]
        
        direction = "Rising" if slope > 0 else "Falling" if slope < 0 else "Flat"
        
        results.append({
            "metric": metric,
            "n_obs": T,
            "slope": slope,
            "hac_tstat": tstat,
            "hac_pvalue": pvalue,
            "direction": direction
        })
        
    return results

def main():
    # skip initial rows starting with #
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if not line.startswith('#'):
            start_idx = i
            break
            
    df = pd.read_csv(CSV_PATH, skiprows=start_idx)
    df['date'] = pd.to_datetime(df['date'])
    
    configs = {
        500: {
            "core_start": "2020-01-31",
            "core_end": "2021-12-31"
        },
        730: {
            "core_start": "2020-12-31",
            "core_end": "2023-03-31"
        }
    }
    
    metrics_to_test = ["engle_granger_p_value", "half_life", "beta", "spread_std"]
    
    table_rows = []
    
    for window in [500, 730]:
        c = configs[window]
        df_w = df[df['window_length'] == window]
        
        drift_results = analyze_drift(df_w, c["core_start"], c["core_end"], metrics_to_test)
        
        for r in drift_results:
            table_rows.append({
                "core": f"{window}d",
                "metric": r["metric"],
                "n_obs": r["n_obs"],
                "slope": f"{r['slope']:.6e}",
                "hac_tstat": f"{r['hac_tstat']:.4f}",
                "hac_pvalue": f"{r['hac_pvalue']:.4e}",
                "direction": r["direction"]
            })
            
    out_lines = [
        "| Core | Metric | N Obs | Slope | HAC t-stat | HAC p-value | Direction |",
        "|---|---|---|---|---|---|---|"
    ]
    for r in table_rows:
        out_lines.append(f"| {r['core']} | {r['metric']} | {r['n_obs']} | {r['slope']} | {r['hac_tstat']} | {r['hac_pvalue']} | {r['direction']} |")
        
    out_lines.append("")
    out_lines.append("*Note: Given how much the rolling windows overlap relative to each core's own length, the prescribed Newey-West lag count is very likely an under-correction, not a full fix — in the 730d core especially, most observations may share the bulk of their underlying daily data with each other. Report this as descriptive/exploratory. Do not treat the HAC p-values as validated significance claims.*")
    
    output_content = "\n".join(out_lines) + "\n"
    
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
-->
"""
    
    final_output = prov_header + "\n## wq_healthy_core_leading_drift_tier_b\n\n" + output_content + "\n"
    
    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)

if __name__ == "__main__":
    main()
