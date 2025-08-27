from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

class StrategyValidator:
    def __init__(self):
        # 定义验证参数
        self.validation_params = {
            "min_volume": 1000000,        # 最小成交量
            "max_implied_vol": 0.5,       # 最大隐含波动率
            "min_dte": 7,                 # 最小到期日
            "max_dte": 45,                # 最大到期日
            "min_delta": 0.2,             # 最小 Delta
            "max_delta": 0.8,             # 最大 Delta
            "min_spread_width": 2,        # 最小价差宽度
            "max_spread_width": 10,       # 最大价差宽度
            "min_credit": 0.1,            # 最小信用
            "max_risk": 0.5               # 最大风险
        }
        
        # 定义策略类型及其验证规则
        self.strategy_rules = {
            "CALL_SPREAD": {
                "required_fields": ["strikes", "expiry"],
                "validate": self._validate_call_spread
            },
            "PUT_SPREAD": {
                "required_fields": ["strikes", "expiry"],
                "validate": self._validate_put_spread
            },
            "IRON_CONDOR": {
                "required_fields": ["strikes", "expiry"],
                "validate": self._validate_iron_condor
            },
            "STRADDLE": {
                "required_fields": ["strike", "expiry"],
                "validate": self._validate_straddle
            }
        }
    
    def _validate_call_spread(self, strategy: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证看涨价差策略"""
        try:
            strikes = strategy.get('strikes', [])
            if len(strikes) != 2:
                return {"valid": False, "reason": "Invalid strikes format"}
            
            lower_strike, upper_strike = strikes
            spread_width = upper_strike - lower_strike
            
            # 验证价差宽度
            if not (self.validation_params["min_spread_width"] <= spread_width <= self.validation_params["max_spread_width"]):
                return {"valid": False, "reason": "Spread width out of range"}
            
            # 验证到期日
            expiry = datetime.strptime(strategy.get('expiry'), '%Y-%m-%d')
            dte = (expiry - datetime.now()).days
            if not (self.validation_params["min_dte"] <= dte <= self.validation_params["max_dte"]):
                return {"valid": False, "reason": "DTE out of range"}
            
            return {"valid": True, "risk_level": "MODERATE"}
            
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    def _validate_put_spread(self, strategy: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证看跌价差策略"""
        try:
            strikes = strategy.get('strikes', [])
            if len(strikes) != 2:
                return {"valid": False, "reason": "Invalid strikes format"}
            
            upper_strike, lower_strike = strikes
            spread_width = upper_strike - lower_strike
            
            # 验证价差宽度
            if not (self.validation_params["min_spread_width"] <= spread_width <= self.validation_params["max_spread_width"]):
                return {"valid": False, "reason": "Spread width out of range"}
            
            # 验证到期日
            expiry = datetime.strptime(strategy.get('expiry'), '%Y-%m-%d')
            dte = (expiry - datetime.now()).days
            if not (self.validation_params["min_dte"] <= dte <= self.validation_params["max_dte"]):
                return {"valid": False, "reason": "DTE out of range"}
            
            return {"valid": True, "risk_level": "MODERATE"}
            
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    def _validate_iron_condor(self, strategy: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证铁鹰策略"""
        try:
            strikes = strategy.get('strikes', [])
            if len(strikes) != 4:
                return {"valid": False, "reason": "Invalid strikes format"}
            
            # 验证价差宽度
            put_spread_width = strikes[1] - strikes[0]
            call_spread_width = strikes[3] - strikes[2]
            
            if not (self.validation_params["min_spread_width"] <= put_spread_width <= self.validation_params["max_spread_width"]):
                return {"valid": False, "reason": "Put spread width out of range"}
            
            if not (self.validation_params["min_spread_width"] <= call_spread_width <= self.validation_params["max_spread_width"]):
                return {"valid": False, "reason": "Call spread width out of range"}
            
            # 验证到期日
            expiry = datetime.strptime(strategy.get('expiry'), '%Y-%m-%d')
            dte = (expiry - datetime.now()).days
            if not (self.validation_params["min_dte"] <= dte <= self.validation_params["max_dte"]):
                return {"valid": False, "reason": "DTE out of range"}
            
            return {"valid": True, "risk_level": "LOW"}
            
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    def _validate_straddle(self, strategy: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证跨式策略"""
        try:
            strike = strategy.get('strike')
            if not strike:
                return {"valid": False, "reason": "Missing strike price"}
            
            # 验证到期日
            expiry = datetime.strptime(strategy.get('expiry'), '%Y-%m-%d')
            dte = (expiry - datetime.now()).days
            if not (self.validation_params["min_dte"] <= dte <= self.validation_params["max_dte"]):
                return {"valid": False, "reason": "DTE out of range"}
            
            return {"valid": True, "risk_level": "HIGH"}
            
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    def validate_strategy(self, strategy: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证交易策略"""
        try:
            strategy_type = strategy.get('type')
            if not strategy_type or strategy_type not in self.strategy_rules:
                return {"valid": False, "reason": "Invalid strategy type"}
            
            # 检查必需字段
            required_fields = self.strategy_rules[strategy_type]["required_fields"]
            for field in required_fields:
                if field not in strategy:
                    return {"valid": False, "reason": f"Missing required field: {field}"}
            
            # 执行策略特定的验证
            validation_result = self.strategy_rules[strategy_type]["validate"](strategy, market_data)
            
            return validation_result
            
        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    def validate_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证交易信号"""
        try:
            # 验证信号强度
            signal_strength = signal.get('signal_strength', 0)
            if signal_strength < 0.6:
                return {"valid": False, "reason": "Signal strength too low"}
            
            # 验证建议的策略
            suggested_strategy = signal.get('suggested_strategy', {})
            strategy_validation = self.validate_strategy(suggested_strategy, market_data)
            
            if not strategy_validation["valid"]:
                return {"valid": False, "reason": f"Strategy validation failed: {strategy_validation['reason']}"}
            
            # 构建验证结果
            validation_result = {
                "valid": True,
                "signal_quality": "HIGH" if signal_strength >= 0.8 else "MODERATE",
                "strategy_risk_level": strategy_validation.get("risk_level", "UNKNOWN"),
                "timestamp": datetime.now().isoformat(),
                "validation_details": {
                    "signal_strength": signal_strength,
                    "strategy_validation": strategy_validation
                }
            }
            
            return validation_result
            
        except Exception as e:
            return {"valid": False, "reason": f"Signal validation error: {str(e)}"}

if __name__ == "__main__":
    # 测试代码
    validator = StrategyValidator()
    
    # 示例市场数据
    market_data = {
        "symbol": "AAPL",
        "price": 150.0,
        "volume": 2000000,
        "implied_volatility": 0.3
    }
    
    # 示例交易信号
    test_signal = {
        "symbol": "AAPL",
        "bias": "BULLISH",
        "signal_type": "STRONG",
        "signal_strength": 0.85,
        "suggested_strategy": {
            "type": "CALL_SPREAD",
            "strikes": [150, 155],
            "expiry": "2024-03-15"
        }
    }
    
    # 验证信号
    validation_result = validator.validate_signal(test_signal, market_data)
    print(json.dumps(validation_result, indent=2, ensure_ascii=False)) 