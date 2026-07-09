import pandas as pd
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
CSV_PATH = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"
OUT_DIR = ROOT / "analysis" / "wq_beta_instability_vs_eg_ordering_tier_b"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def process_core(df, window, core_start, core_end, eg_loss_date):
    df_w = df[df['window_length'] == window].copy()
    df_w['date'] = pd.to_datetime(df_w['date'])
    df_w = df_w.sort_values('date')
    
    # Filter core
    start_dt = pd.to_datetime(core_start)
    end_dt = pd.to_datetime(core_end)
    
    core_df = df_w[(df_w['date'] >= start_dt) & (df_w['date'] <= end_dt)]
    mean_beta = core_df['beta'].mean()
    std_beta = core_df['beta'].std()
    
    lower_bound = mean_beta - 2 * std_beta
    upper_bound = mean_beta + 2 * std_beta
    
    post_core_df = df_w[df_w['date'] > end_dt]
    instability_df = post_core_df[(post_core_df['beta'] < lower_bound) | (post_core_df['beta'] > upper_bound)]
    
    if len(instability_df) > 0:
        beta_onset = instability_df.iloc[0]['date'].strftime('%Y-%m-%d')
    else:
        beta_onset = "None"
        
    if beta_onset == "None":
        which_first = "eg_loss"
    elif beta_onset < eg_loss_date:
        which_first = "beta_instability"
    elif beta_onset > eg_loss_date:
        which_first = "eg_loss"
    else:
        which_first = "same"
        
    return {
        "core": f"{window}d",
        "mean_beta": f"{mean_beta:.6f}",
        "std_beta": f"{std_beta:.6f}",
        "beta_instability_onset_date": beta_onset,
        "eg_loss_onset_date": eg_loss_date,
        "which_first": which_first
    }

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
    
    res_500 = process_core(df, 500, "2020-01-31", "2021-12-31", "2022-01-31")
    res_730 = process_core(df, 730, "2020-12-31", "2023-03-31", "2023-04-28")
    
    results = [res_500, res_730]
    
    # Generate markdown table
    out_lines = [
        "| Core | Mean β | Std β | β Instability Onset | EG Loss Onset | Which First |",
        "|---|---|---|---|---|---|"
    ]
    for r in results:
        out_lines.append(f"| {r['core']} | {r['mean_beta']} | {r['std_beta']} | {r['beta_instability_onset_date']} | {r['eg_loss_onset_date']} | {r['which_first']} |")
        
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
    
    final_output = prov_header + "\n## wq_beta_instability_vs_eg_ordering_tier_b\n\n" + output_content + "\n"
    
    # Append to worklog.md
    worklog = ROOT / "ledger" / "worklog.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)
        
    print(final_output)

if __name__ == "__main__":
    main()
