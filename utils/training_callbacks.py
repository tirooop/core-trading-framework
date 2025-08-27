"""
训练回调类，用于在训练过程中发送通知
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import Figure
from utils.unified_notifier import UnifiedNotifier

class NotifyCallback(BaseCallback):
    """训练通知回调，用于发送训练进度和指标"""
    
    def __init__(self, 
                 notifier: UnifiedNotifier,
                 check_freq: int = 1000,
                 plot_freq: int = 5000,
                 verbose: int = 0):
        """
        初始化回调
        Args:
            notifier: UnifiedNotifier实例
            check_freq: 发送文本更新的频率（步数）
            plot_freq: 发送图表的频率（步数）
            verbose: 详细程度
        """
        super().__init__(verbose)
        self.notifier = notifier
        self.check_freq = check_freq
        self.plot_freq = plot_freq
        
        # 存储历史指标
        self.rewards_history: List[float] = []
        self.ep_len_history: List[float] = []
        self.steps: List[int] = []

    def _on_step(self) -> bool:
        """每步调用"""
        # 记录指标
        if len(self.model.ep_info_buffer) > 0:
            self.rewards_history.append(np.mean([ep['r'] for ep in self.model.ep_info_buffer]))
            self.ep_len_history.append(np.mean([ep['l'] for ep in self.model.ep_info_buffer]))
            self.steps.append(self.num_timesteps)
        
        # 定期发送文本更新
        if self.n_calls % self.check_freq == 0:
            metrics = self._get_current_metrics()
            self.notifier.send_training_update(
                step=self.num_timesteps,
                metrics=metrics,
                fig=self._create_plot() if self.n_calls % self.plot_freq == 0 else None
            )
        return True

    def _on_training_end(self) -> None:
        """训练结束时调用"""
        metrics = self._get_current_metrics()
        self.notifier.send_training_complete(
            total_steps=self.num_timesteps,
            final_metrics=metrics,
            model_path=f"{self.model_class.__name__}_final"
        )

    def _get_current_metrics(self) -> Dict[str, float]:
        """获取当前训练指标"""
        metrics = {}
        if len(self.model.ep_info_buffer) > 0:
            metrics["mean_reward"] = np.mean([ep["r"] for ep in self.model.ep_info_buffer])
            metrics["mean_episode_length"] = np.mean([ep["l"] for ep in self.model.ep_info_buffer])
        return metrics

    def _create_plot(self) -> Optional[plt.Figure]:
        """创建训练指标图表"""
        if len(self.rewards_history) < 2:
            return None
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # 奖励曲线
        ax1.plot(self.steps, self.rewards_history, 'b-', label='Mean Reward')
        ax1.set_title('Training Progress')
        ax1.set_xlabel('Steps')
        ax1.set_ylabel('Mean Reward')
        ax1.grid(True)
        ax1.legend()
        
        # 回合长度曲线
        ax2.plot(self.steps, self.ep_len_history, 'g-', label='Episode Length')
        ax2.set_xlabel('Steps')
        ax2.set_ylabel('Mean Episode Length')
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        return fig 