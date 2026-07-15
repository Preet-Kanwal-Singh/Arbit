"""Smoke training script for PPO with differential_sharpe reward."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

from phase_ii_rl_agent_tcs_infy.env.gym_wrapper import GymPairsTradingEnv


class DiagnosticsCallback(BaseCallback):
    def __init__(self, eval_env, verbose=0):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.outlier_reward_count = 0
        self.action_diffs = []
        self.last_action = 0.0
        
        self.eval_env_state_ok = False
        self.eval_episode_pnl = 0.0
    
    def _on_rollout_start(self) -> None:
        self.outlier_reward_count = 0
        self.action_diffs = []
        
    def _on_step(self) -> bool:
        # SB3 wraps the env in a DummyVecEnv, so locals have an extra batch dimension (size 1)
        reward = self.locals["rewards"][0]
        action = self.locals["actions"][0][0]
        done = self.locals["dones"][0]
        
        if abs(reward) > 5.19:
            self.outlier_reward_count += 1
            
        self.action_diffs.append(abs(action - self.last_action))
        self.last_action = action
        
        if not self.eval_env_state_ok:
            self.eval_env.reset()
            self.eval_env_state_ok = True
            self.eval_episode_pnl = 0.0
            
        _, eval_reward, eval_term, eval_trunc, _ = self.eval_env.step(action)
        self.eval_episode_pnl += float(eval_reward)
        eval_done = eval_term or eval_trunc

        if eval_done != done:
            raise AssertionError(
                f"train/eval episode desync at global step {self.num_timesteps}: "
                f"train done={done}, eval done={eval_done}. The eval_cost_adjusted_pnl "
                f"diagnostic assumes identical episode lengths between train_env and "
                f"eval_env; that assumption just failed."
            )

        if done:
            self.logger.record("custom/eval_cost_adjusted_pnl", self.eval_episode_pnl)
            self.eval_env.reset()
            self.eval_episode_pnl = 0.0
            self.last_action = 0.0
            
        return True

    def _on_rollout_end(self) -> None:
        self.logger.record("custom/outlier_reward_count", self.outlier_reward_count)
        if len(self.action_diffs) > 0:
            self.logger.record("custom/action_diff_mean", float(np.mean(self.action_diffs)))
            self.logger.record("custom/action_diff_std", float(np.std(self.action_diffs)))


def main():
    out_dir = Path(__file__).resolve().parent
    tb_log_dir = out_dir / "tb"
    
    env_kwargs = dict(
        core_id="500d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        bar_frequency="1d", 
        cost_rate=0.0
    )
    
    # Main training env
    train_env = GymPairsTradingEnv(reward_name="differential_sharpe", **env_kwargs)
    train_env = Monitor(train_env)
    
    # Parallel eval env for tracking raw PNL
    eval_env = GymPairsTradingEnv(reward_name="cost_adjusted_pnl", **env_kwargs)
    
    callback = DiagnosticsCallback(eval_env=eval_env)
    
    model = PPO(
        "MlpPolicy", 
        train_env, 
        seed=1337, 
        verbose=1, 
        tensorboard_log=str(tb_log_dir)
    )
    
    print("Starting smoke training...")
    model.learn(total_timesteps=50_000, callback=callback)
    print("Training complete.")


if __name__ == "__main__":
    main()
