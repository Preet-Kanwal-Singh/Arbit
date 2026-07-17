"""Generate synthetic data for PC-2: Feature-pipeline positive control."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

def generate_synthetic_pair():
    master_seed = 20260101
    np.random.seed(master_seed)

    n_bars = 2800
    kappa = 0.1
    sigma = 0.3
    beta = 0.70
    
    # X parameters
    sigma_x = 0.015

    # Generate dates (business days only, starting 2100-01-01)
    dates = pd.bdate_range(start="2100-01-01", periods=n_bars)

    # Generate spread
    # spread_0 ~ N(0, sigma_stationary^2) where sigma_stationary^2 = sigma^2 / (1 - (1-kappa)^2)
    sigma_stationary = sigma / np.sqrt(1 - (1 - kappa)**2)
    spread = np.zeros(n_bars)
    spread[0] = np.random.normal(0, sigma_stationary)
    
    eps_spread = np.random.normal(0, 1, n_bars)
    for t in range(1, n_bars):
        spread[t] = (1 - kappa) * spread[t-1] + sigma * eps_spread[t]

    # Generate log(X_t)
    # eps_x_t ~ N(0, 0.000225) (sigma_x = 0.015)
    eps_x = np.random.normal(0, sigma_x, n_bars)
    log_x = np.zeros(n_bars)
    log_x[0] = np.log(100.0) # Start X at 100
    for t in range(1, n_bars):
        log_x[t] = log_x[t-1] + eps_x[t]

    # Generate log(Y_t)
    log_y = beta * log_x + spread
    
    # Convert back to prices
    x = np.exp(log_x)
    y = np.exp(log_y)

    # DataFrame matching legacy close-only format
    # Requires 'date' column or index, and one column per ticker
    df = pd.DataFrame({
        "date": dates,
        "SYN.X": x,
        "SYN.Y": y
    })

    # Save outputs
    out_dir = Path(__file__).resolve().parents[3] / "data" / "snapshots" / "synthetic_pair_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(out_dir / "adjusted_close.csv", index=False)
    
    metadata = {
        "snapshot_id": "synthetic_pair_v1",
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[-1].strftime("%Y-%m-%d"),
        "tickers": ["SYN.X", "SYN.Y"],
        "synthetic_dgp": {
            "master_seed": master_seed,
            "kappa": kappa,
            "sigma": sigma,
            "beta": beta,
            "sigma_x": sigma_x,
            "variance_x": sigma_x ** 2,
            "n_bars": n_bars
        }
    }
    
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    print(f"Generated synthetic pair at: {out_dir}")
    print(f"Start: {metadata['start_date']}, End: {metadata['end_date']}")
    print(f"X mean: {x.mean():.2f}, Y mean: {y.mean():.2f}")
    
if __name__ == "__main__":
    generate_synthetic_pair()
