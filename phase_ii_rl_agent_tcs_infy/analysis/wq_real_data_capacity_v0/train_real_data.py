"""Real-data capacity check — Tier B."""

import sys
import json
from pathlib import Path
import numpy as np

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.gym_wrapper import GymPairsTradingEnv


class DiagnosticsCallback(BaseCallback):
    def __init__(self, eval_env, out_dir: Path, verbose=0):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.out_dir = out_dir
        
        self.eval_episode_pnl = 0.0
        self.traversal_count = 0
        self.best_pnl = -float('inf')
        
        self.completed_pnls = []

    def _on_step(self) -> bool:
        action = float(np.asarray(self.locals["actions"]).reshape(-1)[0])
        done = bool(self.locals["dones"][0])
        
        eval_obs, eval_reward, eval_term, eval_trunc, _ = self.eval_env.step(np.array([action], dtype=np.float64))
        self.eval_episode_pnl += float(eval_reward)
        eval_done = eval_term or eval_trunc

        if eval_done != done:
            raise AssertionError(
                f"train/eval episode desync at global step {self.num_timesteps}: "
                f"train done={done}, eval done={eval_done}."
            )

        if done:
            self.logger.record("custom/eval_cost_adjusted_pnl", self.eval_episode_pnl)
            
            if self.eval_episode_pnl > self.best_pnl:
                self.best_pnl = self.eval_episode_pnl
                print(f"New best PnL: {self.best_pnl:.4f} at timestep {self.num_timesteps}, traversal {self.traversal_count}")
                self.model.save(self.out_dir / "best_model.zip")
            
            self.completed_pnls.append(self.eval_episode_pnl)
            self.traversal_count += 1
            
            self.eval_episode_pnl = 0.0
            self.eval_env.reset(seed=42)

        return True


def run_baselines(out_dir: Path) -> dict:
    """Run baseline evaluations (Always-flat, Random, Z-Score)."""
    print("\n--- Running Baselines ---")
    results = {}
    
    # 1. Always-Flat
    flat_env = GymPairsTradingEnv(
        core_id="730d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        reward_name="cost_adjusted_pnl", 
        cost_rate=0.0
    )
    flat_env.reset(seed=42)
    flat_pnl = 0.0
    done = False
    while not done:
        _, reward, term, trunc, _ = flat_env.step(np.array([0.0], dtype=np.float64))
        flat_pnl += float(reward)
        done = term or trunc
    results["always_flat"] = flat_pnl
    print(f"Always-Flat PnL: {flat_pnl:.4f}")
    
    # 2. Random Action
    print("Running Random Action baseline (357 traversals)...")
    random_env = GymPairsTradingEnv(
        core_id="730d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        reward_name="cost_adjusted_pnl", 
        cost_rate=0.0
    )
    rng = np.random.default_rng(42)
    random_pnls = []
    for _ in range(357):
        random_env.reset(seed=42)
        pnl = 0.0
        done = False
        while not done:
            action = rng.uniform(-1.0, 1.0)
            _, reward, term, trunc, _ = random_env.step(np.array([action], dtype=np.float64))
            pnl += float(reward)
            done = term or trunc
        random_pnls.append(pnl)
    
    results["random_mean"] = float(np.mean(random_pnls))
    results["random_std"] = float(np.std(random_pnls))
    print(f"Random Action - Mean PnL: {results['random_mean']:.4f}, Std: {results['random_std']:.4f}")
    
    # 3. Z-Score Baseline
    print("Running Z-Score Baseline...")
    z_env = GymPairsTradingEnv(
        core_id="730d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        reward_name="cost_adjusted_pnl", 
        cost_rate=0.0
    )
    z_env.reset(seed=42)
    z_pnl = 0.0
    done = False
    spreads = []
    action = 0.0
    while not done:
        _, reward, term, trunc, info = z_env.step(np.array([action], dtype=np.float64))
        z_pnl += float(reward)
        done = term or trunc
        
        spread = info["spread"]
        spreads.append(spread)
        
        if len(spreads) < 10:
            action = 0.0
        else:
            mean = np.mean(spreads)
            std = np.std(spreads)
            if std > 0:
                z = (spread - mean) / std
                action = float(np.clip(-z, -1.0, 1.0))
            else:
                action = 0.0
                
    results["z_score"] = z_pnl
    print(f"Z-Score Baseline PnL: {z_pnl:.4f}")
    
    return results


def main():
    out_dir = Path(__file__).resolve().parent
    
    train_env = GymPairsTradingEnv(
        core_id="730d_core",
        snapshot_id="tcs_infy_v4_2026-07-13",
        reward_name="differential_sharpe",
        cost_rate=0.0
    )
    train_env.reset(seed=42)
    
    eval_env = GymPairsTradingEnv(
        core_id="730d_core",
        snapshot_id="tcs_infy_v4_2026-07-13",
        reward_name="cost_adjusted_pnl",
        cost_rate=0.0
    )
    eval_env.reset(seed=42)
    
    callback = DiagnosticsCallback(eval_env=eval_env, out_dir=out_dir)
    
    model = PPO(
        "MlpPolicy",
        train_env,
        seed=42,
        verbose=1,
        tensorboard_log=str(out_dir / "tb_real")
    )
    
    print("\n--- Starting PPO Training ---")
    model.learn(total_timesteps=200_000, callback=callback)
    
    print("\n--- Training Complete ---")
    
    # Save final results to a temp json so we can easily read them for summary
    final_10_avg = float(np.mean(callback.completed_pnls[-10:])) if len(callback.completed_pnls) >= 10 else float(np.mean(callback.completed_pnls))
    ppo_results = {
        "best_pnl": callback.best_pnl,
        "final_10_avg": final_10_avg,
    }
    print(f"PPO Final 10 Traversals Average PnL: {final_10_avg:.4f}")
    print(f"PPO Best Single-Traversal PnL: {callback.best_pnl:.4f}")
    
    baseline_results = run_baselines(out_dir)
    
    all_results = {
        "ppo": ppo_results,
        "baselines": baseline_results
    }
    
    with open(out_dir / "temp_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
        
    print("\n--- Post-Training Sanity Check ---")
    best_model_path = out_dir / "best_model.zip"
    if best_model_path.exists():
        best_model = PPO.load(best_model_path)
        sanity_env = GymPairsTradingEnv(
            core_id="730d_core",
            snapshot_id="tcs_infy_v4_2026-07-13",
            reward_name="cost_adjusted_pnl",
            cost_rate=0.0
        )
        obs, _ = sanity_env.reset(seed=42)
        sanity_pnl = 0.0
        done = False
        while not done:
            action, _ = best_model.predict(obs, deterministic=True)
            obs, reward, term, trunc, _ = sanity_env.step(action)
            sanity_pnl += float(reward)
            done = term or trunc
        print(f"Sanity Check Replay PnL: {sanity_pnl:.4f} (Expected roughly {callback.best_pnl:.4f})")
    else:
        print("WARNING: best_model.zip not found for sanity check.")

if __name__ == "__main__":
    main()
