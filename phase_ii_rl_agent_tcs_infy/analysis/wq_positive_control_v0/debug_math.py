import numpy as np
import pandas as pd

def test_math():
    length = 51000
    kappa = 0.1
    sigma = 0.3
    master_seed = 20260101
    
    rng = np.random.default_rng(master_seed)
    sigma_stationary = np.sqrt(sigma**2 / (1 - (1 - kappa)**2))
    
    spread = np.zeros(length, dtype=float)
    spread[0] = rng.normal(0.0, sigma_stationary)
    eps = rng.normal(0.0, 1.0, size=length - 1)
    for t in range(length - 1):
        spread[t + 1] = (1 - kappa) * spread[t] + sigma * eps[t]
        
    pnl = 0.0
    for t in range(1, length):
        action = -1.0 if spread[t] > 0 else (1.0 if spread[t] < 0 else 0.0)
        ret = spread[t] - spread[t-1]
        pnl += action * ret
        
    print(f"Total PNL with action_t = -sign(spread_t): {pnl}")
    
    pnl2 = 0.0
    for t in range(1, length):
        action = -1.0 if spread[t-1] > 0 else (1.0 if spread[t-1] < 0 else 0.0)
        ret = spread[t] - spread[t-1]
        pnl2 += action * ret
        
    print(f"Total PNL with action_t = -sign(spread_{{t-1}}): {pnl2}")

if __name__ == "__main__":
    test_math()
