import pandas as pd
import numpy as np
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / "tcs_infy_v2_2026-07-11"
CSV_PATH = SNAPSHOT_DIR / "ohlcv.csv"
OUT_DIR = ROOT / "phase_i_tcs_infy_pairs_trading" / "analysis" / "wq_volume_signal_test_tier_b"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def get_normalized_onset(df_w, core_start, core_end, column_name):
    # EXACT mirror of phase_i_tcs_infy_pairs_trading/analysis/wq_residual_variance_volatility_vs_cluster_tier_b/six_way_normalized.py
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

def main():
    df = pd.read_csv(CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Pivot to get TCS and INFY volume
    tcs = df[df['ticker'] == 'TCS.NS'].set_index('date')['volume'].rename('TCS_vol')
    infy = df[df['ticker'] == 'INFY.NS'].set_index('date')['volume'].rename('INFY_vol')
    vol_df = pd.concat([tcs, infy], axis=1).dropna()
    
    # Get month-end dates (mirroring characterize_episode_1.py month_end_dates logic)
    dates = pd.DatetimeIndex(vol_df.index)
    s = pd.Series(dates, index=dates)
    m_ends = s.groupby([s.dt.year, s.dt.month]).max().dt.date.values
    
    # Defined anchors from previous tier b run (six_way_normalized.py)
    configs = {
        500: {
            "core_start": "2020-01-31",
            "core_end": "2021-12-31",
            "eg": "2022-01-31"
        },
        730: {
            "core_start": "2020-12-31",
            "core_end": "2023-03-31",
            "eg": "2023-04-28"
        }
    }
    
    results_list = []
    
    for window in [500, 730]:
        rows = []
        for me_date in m_ends:
            me_dt = pd.to_datetime(me_date)
            # Trailing window of `window` trading days up to me_date
            trailing = vol_df.loc[:me_dt].tail(window)
            
            if len(trailing) < window:
                continue
                
            # Data floor enforcement: no volume-derived rolling window, baseline, or normalization may start before 2018-09-06
            floor_date = pd.to_datetime("2018-09-06")
            truncated = trailing.loc[floor_date:]
            
            if len(truncated) == 0:
                continue
                
            tcs_mean = truncated['TCS_vol'].mean()
            infy_mean = truncated['INFY_vol'].mean()
            ratio = tcs_mean / infy_mean if infy_mean != 0 else np.nan
            
            rows.append({
                'date': me_dt,
                'tcs_vol_mean': tcs_mean,
                'infy_vol_mean': infy_mean,
                'vol_ratio': ratio
            })
            
        df_w = pd.DataFrame(rows)
        if len(df_w) == 0:
            continue
            
        c = configs[window]
        
        tcs_onset = get_normalized_onset(df_w, c["core_start"], c["core_end"], "tcs_vol_mean")
        infy_onset = get_normalized_onset(df_w, c["core_start"], c["core_end"], "infy_vol_mean")
        ratio_onset = get_normalized_onset(df_w, c["core_start"], c["core_end"], "vol_ratio")
        
        results_list.append({
            "core": f"{window}d",
            "tcs_onset": tcs_onset,
            "infy_onset": infy_onset,
            "ratio_onset": ratio_onset,
            "eg_onset": c["eg"]
        })
        
    out_lines = [
        "### Setup and Methodology",
        "Data snapshot used: `tcs_infy_v2_2026-07-11` (this snapshot has unadjusted volume, unlike v1).",
        "Data floor: Enforced `2018-09-06` boundary on all rolling windows. Any window extending prior to this date was truncated to start precisely on or after `2018-09-06`.",
        "Methodology: Directly mirrored the `six_way_normalized.py` script's `get_normalized_onset` (which tested and ruled out volatility). The threshold for an \"onset\" is exactly `mean + 2 * std` computed strictly over the core period. Values are computed at each month-end.",
        "",
        "### Pre-Declared Read on the Result",
        "**Tier B follow-up warranted if**: Any volume metric (TCS volume, INFY volume, or their ratio) fires a +2 STD threshold violation *before or simultaneously* with the EG breakdown date (`2022-01-31` for 500d, `2023-04-28` for 730d). This would indicate volume can act as a true leading indicator.",
        "**Empty, like volatility, if**: The volume metrics yield `None` (never fire) or fire *after* the EG breakdown date. This would confirm it is a lagging indicator or noise.",
        "",
        "### Results",
        "| Core | TCS Vol Onset | INFY Vol Onset | Ratio Onset | EG Onset (Reference) |",
        "|---|---|---|---|---|"
    ]
    for r in results_list:
        out_lines.append(f"| {r['core']} | {r['tcs_onset']} | {r['infy_onset']} | {r['ratio_onset']} | {r['eg_onset']} |")
        
    output_content = "\n".join(out_lines) + "\n"
    
    commit = get_git_commit()
    script_path = str(Path(__file__).resolve())
    timestamp = datetime.now(timezone.utc).isoformat()
    content_hash = hashlib.sha256(output_content.encode('utf-8')).hexdigest()
    
    prov_header = f"""<!--
script_path: {script_path}
git_commit: {commit}
snapshot_id: tcs_infy_v2_2026-07-11
timestamp_utc: {timestamp}
output_content_sha256: {content_hash}
-->
"""
    
    final_output = prov_header + "\n## wq_volume_signal_test_tier_b\n\n" + output_content + "\n"
    
    # Append to ledger/worklog/worklog_tier_b.md
    worklog = ROOT / "phase_i_tcs_infy_pairs_trading" / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)

if __name__ == '__main__':
    main()
