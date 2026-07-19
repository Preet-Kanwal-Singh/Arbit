"""Tier B — Seam-index reanalysis (extends wq_zscore_seam_diagnostics_v1)."""

import pandas as pd
import numpy as np
from pathlib import Path

def main():
    out_dir = Path(__file__).resolve().parent
    csv_path = out_dir / "seams_raw.csv"
    
    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # T = 559, L = 20
    T = 559
    L = 20
    
    df["seam_index"] = (df["position_in_path"] * T / L).round().astype(int)
    
    results = {}
    
    buckets = [1, 2, 3, 4, 5]
    for b in buckets:
        sub_df = df[df["seam_index"] == b]
        n = len(sub_df)
        mean = sub_df["reward_at_dist0"].mean()
        std = sub_df["reward_at_dist0"].std(ddof=1) if n > 1 else 0
        se = std / np.sqrt(n) if n > 0 else 0
        results[b] = {"n": n, "mean": mean, "se": se}
        
    sub_df_6 = df[df["seam_index"] >= 6]
    n_6 = len(sub_df_6)
    mean_6 = sub_df_6["reward_at_dist0"].mean()
    std_6 = sub_df_6["reward_at_dist0"].std(ddof=1) if n_6 > 1 else 0
    se_6 = std_6 / np.sqrt(n_6) if n_6 > 0 else 0
    results["6+"] = {"n": n_6, "mean": mean_6, "se": se_6}
    
    md_content = f"""# Seam-index Reanalysis (Tier B)

Extends `wq_zscore_seam_diagnostics_v1` by deriving `seam_index = round(position_in_path * T / L)` and tracking granular seam performance.

## Results by Seam Index

| Seam Index | n | Mean Reward | SE |
|---|---|---|---|
"""
    for b in buckets:
        md_content += f"| {b} | {results[b]['n']} | {results[b]['mean']:.5f} | {results[b]['se']:.5f} |\n"
    
    md_content += f"| 6+ | {results['6+']['n']} | {results['6+']['mean']:.5f} | {results['6+']['se']:.5f} |\n\n"
    
    md_content += """*(Exploratory check only. No significance threshold was applied or evaluated.)*"""
    
    with open(out_dir / "seam_index_reanalysis.md", "w") as f:
        f.write(md_content)
        
    print("Reanalysis complete. Output written to seam_index_reanalysis.md.")
    for k, v in results.items():
        print(f"Index {k}: n={v['n']}, mean={v['mean']:.5f}, SE={v['se']:.5f}")

if __name__ == "__main__":
    main()
