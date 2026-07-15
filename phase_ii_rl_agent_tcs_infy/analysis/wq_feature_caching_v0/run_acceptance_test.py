import sys
import time
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.pairs_trading_env import PairsTradingEnv

def run_env(core_id: str, num_steps: int = 100000) -> tuple[dict, float]:
    env = PairsTradingEnv(
        core_id=core_id,
        snapshot_id="tcs_infy_v4_2026-07-13"
    )
    obs, info = env.reset(seed=42)
    
    # We need to extract eg_p and eg_p_trend from the obs.
    # FeatureRegistry.default_v0() order is: beta, eg_p, eg_p_trend
    
    values = []
    
    start_time = time.time()
    steps = 0
    done = False
    
    while not done and steps < num_steps:
        values.append({
            "step": steps,
            "timestamp": info["timestamp"],
            "eg_p": float(obs[1]),
            "eg_p_trend": float(obs[2])
        })
        
        # take a random action, doesn't matter for features
        action = 0.0
        obs, reward, term, trunc, info = env.step(action)
        done = term or trunc
        steps += 1
        
    end_time = time.time()
    
    elapsed = end_time - start_time
    return values, elapsed

def main():
    print("Running 500d_core...")
    vals_500, time_500 = run_env("500d_core")
    print(f"500d_core completed {len(vals_500)} steps in {time_500:.2f}s (FPS: {len(vals_500)/time_500:.2f})")
    
    print("Running 730d_core...")
    vals_730, time_730 = run_env("730d_core")
    print(f"730d_core completed {len(vals_730)} steps in {time_730:.2f}s (FPS: {len(vals_730)/time_730:.2f})")
    
    out = {
        "500d_core": vals_500,
        "730d_core": vals_730
    }
    
    out_path = Path(__file__).parent / "output.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out))

if __name__ == "__main__":
    main()
