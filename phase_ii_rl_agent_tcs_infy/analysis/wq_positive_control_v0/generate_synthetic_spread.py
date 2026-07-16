"""Generate synthetic spread trajectory for PC-1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate_spread(length: int, kappa: float, sigma: float, master_seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(master_seed)
    
    sigma_stationary = np.sqrt(sigma**2 / (1 - (1 - kappa)**2))
    
    spread = np.zeros(length, dtype=float)
    spread[0] = rng.normal(0.0, sigma_stationary)
    
    eps = rng.normal(0.0, 1.0, size=length - 1)
    for t in range(length - 1):
        spread[t + 1] = (1 - kappa) * spread[t] + sigma * eps[t]
        
    return pd.DataFrame({"spread": spread}, index=np.arange(length))


def main() -> None:
    length = 51_000
    kappa = 0.1
    sigma = 0.3
    master_seed = 20260101
    
    out_dir = Path("data/snapshots/synthetic_positive_control_v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df = generate_spread(length, kappa, sigma, master_seed)
    df.to_csv(out_dir / "spread.csv", index=True, index_label="step")
    
    metadata = {
        "snapshot_id": "synthetic_positive_control_v1",
        "synthetic": True,
        "dgp": {
            "type": "AR(1) mean-reverting",
            "kappa": kappa,
            "sigma": sigma,
            "master_seed": master_seed,
            "length": length,
            "formula_initial": "spread_0 ~ N(0, sigma_stationary^2) where sigma_stationary^2 = sigma^2 / (1 - (1-kappa)^2)",
            "formula_step": "spread_{t+1} = (1 - kappa) * spread_t + sigma * eps_t, eps_t ~ N(0, 1) iid"
        }
    }
    
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    
    print(f"Generated synthetic spread of length {length} in {out_dir}")


if __name__ == "__main__":
    main()
