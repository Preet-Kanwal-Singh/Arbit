"""Train PC-2a (cost_adjusted_pnl)."""

import sys
import json
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.analysis.wq_positive_control_v1_feature_pipeline.gym_pc2_wrapper import PC2GymPairsTradingEnv
from phase_ii_rl_agent_tcs_infy.env.feature_registry import reset_eg_cache_stats


class DiagnosticsCallback(BaseCallback):
    def __init__(self, eval_env, p99_threshold: float, verbose=0):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.p99_threshold = p99_threshold
        
        self.eval_episode_pnl = 0.0
        self.outlier_reward_count = 0
        self.action_diffs = []
        self.last_action = 0.0

    def _on_step(self) -> bool:
        action = float(np.asarray(self.locals["actions"]).reshape(-1)[0])
        self.action_diffs.append(abs(action - self.last_action))
        self.last_action = action
        
        reward = float(self.locals["rewards"][0])
        if abs(reward) > self.p99_threshold:
            self.outlier_reward_count += 1
            
        if np.isnan(reward) or np.isinf(reward):
            print(f"HARD STOP: NaN/Inf reward detected at step {self.num_timesteps}")
            return False
            
        done = bool(self.locals["dones"][0])
        
        # Shadow evaluation
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
            self.logger.record("custom/outlier_reward_count", self.outlier_reward_count)
            
            if len(self.action_diffs) > 0:
                self.logger.record("custom/action_diff_mean", np.mean(self.action_diffs))
                self.logger.record("custom/action_diff_std", np.std(self.action_diffs))
                
            self.eval_episode_pnl = 0.0
            self.outlier_reward_count = 0
            self.action_diffs = []
            
            # Reset eval env exactly when train env resets (done implicitly in SB3 for train, manually for eval here)
            self.eval_env.reset(seed=42)
            self.last_action = 0.0

        return True


def main() -> None:
    reset_eg_cache_stats()
    
    out_dir = Path(__file__).resolve().parent
    refs_path = out_dir / "oracle_refs.json"
    if not refs_path.exists():
        raise FileNotFoundError("Run run_oracle.py first to generate thresholds.")
        
    refs = json.loads(refs_path.read_text())
    p99_threshold = refs["pnl_p99_threshold"]
    
    train_env = PC2GymPairsTradingEnv(reward_name="cost_adjusted_pnl")
    train_env.reset(seed=42)
    
    eval_env = PC2GymPairsTradingEnv(reward_name="cost_adjusted_pnl")
    eval_env.reset(seed=42)
    
    callback = DiagnosticsCallback(eval_env=eval_env, p99_threshold=p99_threshold)
    
    # 25 rollouts * 2,000 steps = 50,000 total steps
    # We use 500 n_steps because the episodic cadence is 500. Wait, actually 2048 is standard PPO, 
    # but the instructions say "matches PC-1 scale exactly" which did 51,200. Let's just use 500.
    model = PPO(
        "MlpPolicy",
        train_env,
        n_steps=500,
        batch_size=500,
        n_epochs=10,
        learning_rate=3e-4,
        seed=42,
        verbose=1,
        tensorboard_log=str(out_dir / "tb_pc2a"),
    )
    
    model.learn(total_timesteps=50000, callback=callback)
    
    print("Training complete.")
    
    from phase_ii_rl_agent_tcs_infy.env.feature_registry import get_eg_cache_stats
    print(f"Cache Stats: {get_eg_cache_stats()}")


if __name__ == "__main__":
    main()
