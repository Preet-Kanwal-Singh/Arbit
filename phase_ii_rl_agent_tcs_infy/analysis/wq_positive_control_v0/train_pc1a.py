"""Train PPO on SyntheticOracleEnv with cost_adjusted_pnl."""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

from phase_ii_rl_agent_tcs_infy.env.synthetic_oracle_gym_wrapper import GymSyntheticOracleEnv


class DiagnosticsCallback(BaseCallback):
    def __init__(self, eval_env, p99_threshold, verbose=0):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.p99_threshold = p99_threshold
        self.outlier_reward_count = 0
        self.action_diffs = []
        self.last_action = 0.0
        
        self.eval_env_state_ok = False
        self.eval_episode_pnl = 0.0
    
    def _on_rollout_start(self) -> None:
        self.outlier_reward_count = 0
        self.action_diffs = []
        
    def _on_step(self) -> bool:
        reward = self.locals["rewards"][0]
        action = self.locals["actions"][0][0]
        done = self.locals["dones"][0]
        
        if abs(reward) > self.p99_threshold:
            self.outlier_reward_count += 1
            
        self.action_diffs.append(abs(action - self.last_action))
        self.last_action = action
        
        if not self.eval_env_state_ok:
            self.eval_env.reset()
            self.eval_env_state_ok = True
            self.eval_episode_pnl = 0.0
            
        _, eval_reward, eval_term, eval_trunc, _ = self.eval_env.step(np.array([action]))
        self.eval_episode_pnl += float(eval_reward)
        eval_done = eval_term or eval_trunc

        if eval_done != done:
            raise AssertionError(
                f"train/eval episode desync at global step {self.num_timesteps}: "
                f"train done={done}, eval done={eval_done}."
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
    tb_log_dir = out_dir / "tb_pc1a"
    
    refs_path = out_dir / "oracle_refs.json"
    refs = json.loads(refs_path.read_text())
    p99_threshold = refs["pnl_p99_threshold"]
    
    env_kwargs = dict(
        reward_name="cost_adjusted_pnl",
        cost_rate=0.0,
        dsr_eta=0.01,
        dsr_epsilon=1e-12,
        dsr_warmup_steps=100,
        snapshot_id="synthetic_positive_control_v1",
        steps_per_episode=500
    )
    
    train_env = GymSyntheticOracleEnv(**env_kwargs)
    train_env = Monitor(train_env)
    
    eval_env = GymSyntheticOracleEnv(**env_kwargs)
    
    # Sync episodes
    train_env.unwrapped.set_episode(0)
    eval_env.unwrapped.set_episode(0)
    
    callback = DiagnosticsCallback(eval_env=eval_env, p99_threshold=p99_threshold)
    
    model = PPO(
        "MlpPolicy", 
        train_env, 
        seed=42, 
        verbose=1, 
        tensorboard_log=str(tb_log_dir)
    )
    
    print("Starting PC-1a training (cost_adjusted_pnl)...")
    model.learn(total_timesteps=50_000, callback=callback)
    print("Training complete.")


if __name__ == "__main__":
    main()
