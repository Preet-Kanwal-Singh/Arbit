import pandas as pd
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess
from collections import defaultdict

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
CSV_PATH = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"
OUT_DIR = ROOT / "analysis" / "wq_residual_variance_volatility_vs_cluster_tier_b"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def get_normalized_onset(df_w, core_start, core_end, column_name):
    start_dt = pd.to_datetime(core_start)
    end_dt = pd.to_datetime(core_end)
    
    core_df = df_w[(df_w['date'] >= start_dt) & (df_w['date'] <= end_dt)]
    mean_val = core_df[column_name].mean()
    std_val = core_df[column_name].std()
    
    threshold = mean_val + 2 * std_val
    
    post_core_df = df_w[df_w['date'] > end_dt]
    fail_df = post_core_df[post_core_df[column_name] > threshold]
    
    if len(fail_df) > 0:
        return fail_df.iloc[0]['date'].strftime('%Y-%m-%d')
    return "None"

def rank_metrics_grouped(metrics):
    valid_metrics = [(name, date) for name, date in metrics if date != "None"]
    
    date_groups = defaultdict(list)
    for name, date in valid_metrics:
        date_groups[date].append(name)
        
    sorted_dates = sorted(date_groups.keys())
    rank_parts = []
    for date in sorted_dates:
        names = date_groups[date]
        if len(names) > 1:
            # Sort names for deterministic output (e.g. {ADF, EG})
            rank_parts.append("{" + ", ".join(sorted(names)) + "}")
        else:
            rank_parts.append(names[0])
            
    return " -> ".join(rank_parts)

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
    df = df.sort_values('date')
    
    # Defined anchors from previous tier b run
    configs = {
        500: {
            "core_start": "2020-01-31",
            "core_end": "2021-12-31",
            "eg": "2022-01-31",
            "hl": "2022-03-31",
            "adf": "2022-01-31",
            "beta": "2023-06-30"
        },
        730: {
            "core_start": "2020-12-31",
            "core_end": "2023-03-31",
            "eg": "2023-04-28",
            "hl": "2023-04-28",
            "adf": "2023-04-28",
            "beta": "2023-08-31"
        }
    }
    
    results = []
    
    for window in [500, 730]:
        c = configs[window]
        df_w = df[df['window_length'] == window]
        
        # Calculate new metrics
        resid_var = get_normalized_onset(df_w, c["core_start"], c["core_end"], "spread_std")
        vol = get_normalized_onset(df_w, c["core_start"], c["core_end"], "spread_daily_change_std")
        
        # Build metric list for ranking
        metrics_list = [
            ("EG", c["eg"]),
            ("HL", c["hl"]),
            ("ADF", c["adf"]),
            ("β", c["beta"]),
            ("ResidVar", resid_var),
            ("Vol", vol)
        ]
        
        rank = rank_metrics_grouped(metrics_list)
        
        results.append({
            "core": f"{window}d",
            "eg_onset": c["eg"],
            "hl_onset": c["hl"],
            "adf_onset": c["adf"],
            "beta_onset": c["beta"],
            "resid_var_onset": resid_var,
            "vol_onset": vol,
            "rank_grouped": rank
        })
    
    # Generate markdown table
    out_lines = [
        "| Core | EG Onset | HL Onset | ADF Onset | β Onset | Resid Var Onset | Vol Onset | Rank Grouped |",
        "|---|---|---|---|---|---|---|---|"
    ]
    for r in results:
        out_lines.append(f"| {r['core']} | {r['eg_onset']} | {r['hl_onset']} | {r['adf_onset']} | {r['beta_onset']} | {r['resid_var_onset']} | {r['vol_onset']} | {r['rank_grouped']} |")
        
    output_content = "\n".join(out_lines) + "\n"
    
    # Provenance
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
    
    final_output = prov_header + "\n## wq_residual_variance_volatility_vs_cluster_tier_b\n\n" + output_content + "\n"
    
    # Append to ledger/worklog/worklog_tier_b.md
    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)
        
if __name__ == "__main__":
    main()
