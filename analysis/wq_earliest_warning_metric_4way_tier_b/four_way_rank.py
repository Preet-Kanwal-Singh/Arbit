import pandas as pd
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
CSV_PATH = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"
OUT_DIR = ROOT / "analysis" / "wq_earliest_warning_metric_4way_tier_b"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def get_adf_onset(df, window, core_end):
    df_w = df[df['window_length'] == window].copy()
    df_w['date'] = pd.to_datetime(df_w['date'])
    df_w = df_w.sort_values('date')
    
    end_dt = pd.to_datetime(core_end)
    
    post_core_df = df_w[df_w['date'] > end_dt]
    fail_df = post_core_df[post_core_df['adf_pass'] == False]
    
    if len(fail_df) > 0:
        return fail_df.iloc[0]['date'].strftime('%Y-%m-%d')
    return "None"

def rank_metrics(eg, hl, beta, adf):
    metrics = [("EG", eg), ("HL", hl), ("Beta", beta), ("ADF", adf)]
    # Filter out None if any (though we expect all to have dates in this case)
    valid_metrics = [(name, date) for name, date in metrics if date != "None"]
    
    # Sort by date
    valid_metrics.sort(key=lambda x: x[1])
    
    # Format the ranking string
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
    
    # Defined anchors
    anchors = {
        500: {
            "core_end": "2021-12-31",
            "eg": "2022-01-31",
            "hl": "2023-04-28",
            "beta": "2023-06-30"
        },
        730: {
            "core_end": "2023-03-31",
            "eg": "2023-04-28",
            "hl": "2023-04-28",
            "beta": "2023-08-31"
        }
    }
    
    results = []
    
    for window in [500, 730]:
        a = anchors[window]
        adf = get_adf_onset(df, window, a["core_end"])
        rank = rank_metrics(a["eg"], a["hl"], a["beta"], adf)
        
        results.append({
            "core": f"{window}d",
            "eg_onset": a["eg"],
            "hl_onset": a["hl"],
            "beta_onset": a["beta"],
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
    
    final_output = prov_header + "\n## wq_earliest_warning_metric_4way_tier_b\n\n" + output_content + "\n"
    
    # Append to worklog.md
    worklog = ROOT / "ledger" / "worklog.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)
        
if __name__ == "__main__":
    main()
