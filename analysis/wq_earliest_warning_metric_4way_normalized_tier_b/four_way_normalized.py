import pandas as pd
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
CSV_PATH = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"
OUT_DIR = ROOT / "analysis" / "wq_earliest_warning_metric_4way_normalized_tier_b"

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

def rank_metrics(eg, hl, beta, adf):
    metrics = [("EG", eg), ("HL", hl), ("Beta", beta), ("ADF", adf)]
    valid_metrics = [(name, date) for name, date in metrics if date != "None"]
    valid_metrics.sort(key=lambda x: x[1])
    ranked_names = [x[0] for x in valid_metrics]
    return " -> ".join(ranked_names)

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
    
    # Defined anchors
    configs = {
        500: {
            "core_start": "2020-01-31",
            "core_end": "2021-12-31",
            "beta": "2023-06-30"
        },
        730: {
            "core_start": "2020-12-31",
            "core_end": "2023-03-31",
            "beta": "2023-08-31"
        }
    }
    
    results = []
    
    for window in [500, 730]:
        c = configs[window]
        df_w = df[df['window_length'] == window]
        
        eg = get_normalized_onset(df_w, c["core_start"], c["core_end"], "engle_granger_p_value")
        hl = get_normalized_onset(df_w, c["core_start"], c["core_end"], "half_life")
        adf = get_normalized_onset(df_w, c["core_start"], c["core_end"], "adf_p_value")
        
        beta = c["beta"]
        
        rank = rank_metrics(eg, hl, beta, adf)
        
        results.append({
            "core": f"{window}d",
            "eg_onset": eg,
            "hl_onset": hl,
            "beta_onset": beta,
            "adf_onset": adf,
            "rank_1_to_4": rank
        })
    
    # Generate markdown table
    out_lines = [
        "| Core | EG Onset | HL Onset | β Onset | ADF Onset | Rank 1 to 4 |",
        "|---|---|---|---|---|---|"
    ]
    for r in results:
        out_lines.append(f"| {r['core']} | {r['eg_onset']} | {r['hl_onset']} | {r['beta_onset']} | {r['adf_onset']} | {r['rank_1_to_4']} |")
        
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
    
    final_output = prov_header + "\n## wq_earliest_warning_metric_4way_normalized_tier_b\n\n" + output_content + "\n"
    
    # Append to worklog.md
    worklog = ROOT / "ledger" / "worklog.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)
        
if __name__ == "__main__":
    main()
