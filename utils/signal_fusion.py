from typing import Dict, Any, Optional
from datetime import datetime
import json

class SignalFusionEngine:
    def __init__(self):
        # 定义各因子的权重
        self.weights = {
            "technical": 0.3,    # 技术指标
            "sentiment": 0.2,    # 市场情绪
            "sector": 0.1,       # 板块强度
            "options": 0.25,     # 期权链分析
            "news": 0.15         # 新闻情绪
        }
        
        # 定义信号阈值
        self.thresholds = {
            "high_confidence": 0.75,  # 高置信度阈值
            "low_confidence": 0.5,    # 低置信度阈值
            "min_signal_strength": 0.6 # 最小信号强度
        }
    
    def _calculate_signal_strength(self, analysis: Dict[str, Any]) -> float:
        """计算信号强度"""
        try:
            # 获取基础置信度
            base_confidence = float(analysis.get('confidence', 0))
            
            # 根据市场偏向调整置信度
            bias = analysis.get('bias', 'NEUTRAL')
            bias_multiplier = {
                'BULLISH': 1.0,
                'NEUTRAL': 0.8,
                'BEARISH': 1.0
            }.get(bias, 0.8)
            
            # 计算最终信号强度
            signal_strength = base_confidence * bias_multiplier
            
            return min(max(signal_strength, 0), 1)  # 确保在 0-1 之间
            
        except Exception as e:
            print(f"Error calculating signal strength: {str(e)}")
            return 0
    
    def _generate_trading_signal(self, analysis: Dict[str, Any], signal_strength: float) -> Dict[str, Any]:
        """生成交易信号"""
        try:
            bias = analysis.get('bias', 'NEUTRAL')
            suggested_strategy = analysis.get('suggested_strategy', {})
            
            # 根据信号强度决定是否生成交易信号
            if signal_strength >= self.thresholds['high_confidence']:
                signal_type = 'STRONG'
            elif signal_strength >= self.thresholds['low_confidence']:
                signal_type = 'MODERATE'
            else:
                signal_type = 'WEAK'
            
            # 构建交易信号
            signal = {
                'timestamp': datetime.now().isoformat(),
                'symbol': analysis.get('symbol', ''),
                'bias': bias,
                'signal_type': signal_type,
                'signal_strength': signal_strength,
                'suggested_strategy': suggested_strategy,
                'risk_factors': analysis.get('risk_factors', []),
                'logic_chain': analysis.get('logic_chain', [])
            }
            
            return signal
            
        except Exception as e:
            print(f"Error generating trading signal: {str(e)}")
            return None
    
    def process_analysis(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理 AI 分析结果并生成交易信号"""
        try:
            # 计算信号强度
            signal_strength = self._calculate_signal_strength(analysis)
            
            # 如果信号强度低于最小阈值，返回 None
            if signal_strength < self.thresholds['min_signal_strength']:
                return None
            
            # 生成交易信号
            signal = self._generate_trading_signal(analysis, signal_strength)
            
            return signal
            
        except Exception as e:
            print(f"Error processing analysis: {str(e)}")
            return None

if __name__ == "__main__":
    # 测试代码
    fusion_engine = SignalFusionEngine()
    
    # 示例 AI 分析结果
    test_analysis = {
        "symbol": "AAPL",
        "bias": "BULLISH",
        "confidence": 0.85,
        "logic_chain": [
            "RSI 显示超买",
            "MACD 金叉",
            "成交量放大"
        ],
        "risk_factors": [
            "市场整体波动性增加",
            "期权隐含波动率处于高位"
        ],
        "suggested_strategy": {
            "type": "CALL_SPREAD",
            "strikes": [150, 155],
            "expiry": "2024-03-15"
        }
    }
    
    # 处理分析结果
    signal = fusion_engine.process_analysis(test_analysis)
    if signal:
        print(json.dumps(signal, indent=2, ensure_ascii=False)) 