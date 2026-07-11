import pandas as pd
import numpy as np
import statsmodels.api as sm
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"c:\Users\preet\OneDrive\Desktop\Skool\Arbit")
PRICE_CSV = ROOT / "data" / "snapshots" / "tcs_infy_v1_2026-07-04" / "adjusted_close.csv"
METRICS_CSV = ROOT / "analysis" / "claim_002_healthy_episode_characterization" / "codex" / "rolling_metrics.csv"
OUT_DIR = ROOT / "analysis" / "wq_hurst_onset_dfa_tier_b"

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"

def calc_dfa(resid, min_s=30, max_s=None):
    if max_s is None:
        max_s = len(resid) // 4
        
    Y = np.cumsum(resid - np.mean(resid))
    N = len(Y)
    
    scales = np.arange(min_s, max_s + 1)
    F = np.zeros(len(scales))
    
    for idx, s in enumerate(scales):
        Ns = N // s
        F2_s = 0.0
        
        for v in range(Ns):
            start = v * s
            end = (v + 1) * s
            Y_seg = Y[start:end]
            x_idx = np.arange(1, s + 1)
            
            p = np.polyfit(x_idx, Y_seg, 1)
            y_trend = np.polyval(p, x_idx)
            
            F2_s += np.mean((Y_seg - y_trend) ** 2)
            
        F[idx] = np.sqrt(F2_s / Ns)
        
    log_s = np.log(scales)
    log_F = np.log(F)
    p = np.polyfit(log_s, log_F, 1)
    H = p[0]
    return H

def main():
    price_df = pd.read_csv(PRICE_CSV, parse_dates=['date']).set_index('date').dropna()
    y_all = np.log(price_df['TCS.NS'])
    x_all = np.log(price_df['INFY.NS'])
    
    with open(METRICS_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if not line.startswith('#'):
            start_idx = i
            break
            
    df = pd.read_csv(METRICS_CSV, skiprows=start_idx)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['window_length'].isin([500, 730])].copy()
    
    hurst_results = []
    
    for idx, row in df.iterrows():
        n = int(row['window_length'])
        end_date = row['date']
        try:
            end_loc = price_df.index.get_loc(pd.to_datetime(end_date))
        except KeyError:
            continue
            
        start_loc = end_loc - n + 1
        if start_loc < 0:
            continue
            
        y_win = y_all.iloc[start_loc:end_loc+1].values
        x_win = x_all.iloc[start_loc:end_loc+1].values
        
        X_win = sm.add_constant(x_win)
        model = sm.OLS(y_win, X_win).fit()
        resid = model.resid
        
        H = calc_dfa(resid, min_s=30, max_s=n//4)
        hurst_results.append({
            "date": end_date,
            "window_length": n,
            "H": H
        })
        
    H_df = pd.DataFrame(hurst_results)
    
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
    
    table_rows = []
    
    for window in [500, 730]:
        c = configs[window]
        w_df = H_df[H_df['window_length'] == window].copy()
        
        start_dt = pd.to_datetime(c["core_start"])
        end_dt = pd.to_datetime(c["core_end"])
        
        core_df = w_df[(w_df['date'] >= start_dt) & (w_df['date'] <= end_dt)]
        mean_H = core_df['H'].mean()
        std_H = core_df['H'].std()
        
        threshold = mean_H + 2 * std_H
        
        post_core = w_df[w_df['date'] > end_dt]
        fail = post_core[post_core['H'] > threshold]
        
        if len(fail) > 0:
            onset = fail.iloc[0]['date'].strftime('%Y-%m-%d')
        else:
            onset = "None"
            
        table_rows.append({
            "core": f"{window}d",
            "mean_H": f"{mean_H:.6f}",
            "std_H": f"{std_H:.6f}",
            "hurst_onset_date": onset
        })
        
    out_lines = [
        "| Core | Mean H | Std H | Hurst Onset Date |",
        "|---|---|---|---|"
    ]
    for r in table_rows:
        out_lines.append(f"| {r['core']} | {r['mean_H']} | {r['std_H']} | {r['hurst_onset_date']} |")
        
    out_lines.append("")
    out_lines.append("*Note: n=500–750 is near the literature-identified floor for stable DFA estimation (~1000 recommended); no pre-whitening, bias correction, or cross-estimator check was applied. Treat this onset date as exploratory, not on the same footing as the EG/HL/ADF/β/residual-variance onsets already logged.*")
        
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
    
    final_output = prov_header + "\n## wq_hurst_onset_dfa_tier_b\n\n" + output_content + "\n"
    
    worklog = ROOT / "ledger" / "worklog" / "worklog_tier_b.md"
    mode = "a" if worklog.exists() else "w"
    with open(worklog, mode, encoding="utf-8") as f:
        f.write(final_output)
        
if __name__ == "__main__":
    main()
