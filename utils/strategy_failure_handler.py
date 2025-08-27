"""
Strategy Failure Handler
Analyzes failed strategies and automatically generates improved versions using AI
"""
import os
import json
import logging
import datetime
from typing import Dict, Any, Optional, Tuple, List

# Import our AI chat agent
from api.ai_chat_agent import DeepSeekChatAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyFailureHandler:
    """
    Handles failed trading strategies by analyzing the failure and generating improved versions.
    Uses AI to understand failure patterns and propose fixes.
    """
    
    def __init__(self, 
                 save_dir: str = "strategies/generated",
                 failure_logs_dir: str = "results/failure_analysis",
                 ai_agent: Optional[DeepSeekChatAgent] = None):
        """
        Initialize the strategy failure handler.
        
        Args:
            save_dir: Directory to save generated strategies
            failure_logs_dir: Directory to store failure analysis logs
            ai_agent: Optional pre-configured AI agent instance
        """
        self.save_dir = save_dir
        self.failure_logs_dir = failure_logs_dir
        
        # Create directories if they don't exist
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(failure_logs_dir, exist_ok=True)
        
        # Initialize AI agent if not provided
        self.ai_agent = ai_agent or DeepSeekChatAgent()
        
        logger.info("Initialized Strategy Failure Handler")
    
    def analyze_failure(self, 
                       strategy_code: str, 
                       failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a failed strategy using AI.
        
        Args:
            strategy_code: The Python code of the failed strategy
            failure_data: Dictionary containing failure information
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Analyzing strategy failure")
        
        # Extract relevant failure information
        failure_reason = failure_data.get("error", "Unknown error")
        performance_metrics = failure_data.get("metrics", {})
        
        # Create metrics string
        metrics_str = "\n".join([f"- {k}: {v}" for k, v in performance_metrics.items()])
        
        # Prepare prompt for AI analysis
        system_prompt = """You are an expert quantitative finance engineer specializing in trading strategy diagnosis.
Your task is to analyze a failed trading strategy and identify the root causes of the failure.
Focus on algorithmic issues, logical flaws, and potential improvements."""
        
        query = f"""Please analyze this trading strategy that has failed:

```python
{strategy_code}
```

Failure information:
- Error: {failure_reason}
- Performance metrics:
{metrics_str}

Please provide:
1. A diagnosis of what might have caused the failure
2. Identification of potential algorithmic or logical issues
3. Key weaknesses in the strategy's approach
4. Areas that could be improved or optimized
"""
        
        # Get AI analysis
        analysis = self.ai_agent.ask(query, system_prompt=system_prompt, temperature=0.4)
        
        # Generate a summary analysis
        timestamp = datetime.datetime.now().isoformat()
        
        result = {
            "timestamp": timestamp,
            "strategy_code_hash": hash(strategy_code),
            "failure_reason": failure_reason,
            "analysis": analysis,
            "performance_metrics": performance_metrics
        }
        
        # Save analysis to file
        self._save_analysis(result)
        
        return result
    
    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save analysis to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"failure_analysis_{timestamp}.json"
        filepath = os.path.join(self.failure_logs_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2)
            logger.debug(f"Saved analysis to {filepath}")
        except Exception as e:
            logger.error(f"Error saving analysis to file: {str(e)}")
    
    def generate_improved_strategy(self, 
                                 strategy_code: str, 
                                 failure_data: Dict[str, Any],
                                 strategy_requirements: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate an improved version of the failed strategy.
        
        Args:
            strategy_code: The Python code of the failed strategy
            failure_data: Dictionary containing failure information
            strategy_requirements: Additional requirements or constraints
            
        Returns:
            Tuple containing (file_path, improved_strategy_code)
        """
        logger.info("Generating improved strategy")
        
        # First, analyze the failure
        analysis = self.analyze_failure(strategy_code, failure_data)
        
        # Extract strategy class name
        class_name = self._extract_class_name(strategy_code)
        improved_class_name = f"Improved{class_name}" if class_name else "ImprovedStrategy"
        
        # Prepare prompt for improved strategy generation
        system_prompt = """You are an expert quantitative finance AI that generates high-quality trading strategies.
Your task is to create an improved version of a trading strategy that has failed.
The strategy should:
1. Follow the base.strategy.Strategy implementation pattern
2. Include necessary imports, class definition, and complete implementation
3. Address the identified issues from the failure analysis
4. Include detailed comments explaining the improvements
5. Include the original logic but with fixes and enhancements
"""
        
        # Additional requirements
        req_str = f"\nAdditional Requirements:\n{strategy_requirements}" if strategy_requirements else ""
        
        query = f"""Please generate an improved version of this failed trading strategy:

```python
{strategy_code}
```

Failure Analysis:
{analysis["analysis"]}

Please create a complete, improved implementation that:
1. Addresses the identified issues
2. Maintains the core strategy concept but with better implementation
3. Includes better risk management and robustness
4. Uses the class name {improved_class_name}
5. Is completely executable without errors{req_str}

Return the complete Python code with imports, class definition, and implementation.
"""
        
        # Generate improved strategy
        improved_code = self.ai_agent.ask(query, system_prompt=system_prompt, temperature=0.7, max_tokens=2048)
        
        # Save improved strategy to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{improved_class_name}.py"
        filepath = os.path.join(self.save_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(improved_code)
            logger.info(f"Saved improved strategy to {filepath}")
        except Exception as e:
            logger.error(f"Error saving improved strategy to file: {str(e)}")
            filepath = "ERROR_SAVING_FILE"
        
        return filepath, improved_code
    
    def _extract_class_name(self, code: str) -> Optional[str]:
        """Extract the class name from strategy code."""
        try:
            import re
            # Simple regex to find class name
            match = re.search(r'class\s+(\w+)', code)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"Error extracting class name: {str(e)}")
        
        return None
    
    def batch_improve_strategies(self, failed_strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple failed strategies in batch.
        
        Args:
            failed_strategies: List of dictionaries with strategy code and failure data
            
        Returns:
            List of dictionaries with improvement results
        """
        results = []
        
        for idx, strategy_info in enumerate(failed_strategies):
            logger.info(f"Processing failed strategy {idx+1}/{len(failed_strategies)}")
            
            try:
                strategy_code = strategy_info.get("code", "")
                failure_data = strategy_info.get("failure_data", {})
                requirements = strategy_info.get("requirements", None)
                
                filepath, improved_code = self.generate_improved_strategy(
                    strategy_code, failure_data, requirements
                )
                
                results.append({
                    "original_strategy": strategy_code,
                    "improved_strategy": improved_code,
                    "filepath": filepath,
                    "success": True,
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error improving strategy: {str(e)}")
                results.append({
                    "original_strategy": strategy_info.get("code", ""),
                    "error": str(e),
                    "success": False,
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        return results

# Example usage
if __name__ == "__main__":
    # Example failed strategy code
    example_code = """
import numpy as np
from base.strategy import Strategy

class BrokenStrategy(Strategy):
    def __init__(self, name, symbols, params):
        super().__init__(name, symbols)
        self.window = params.get('window', 20)
        
    def on_tick(self, symbol, tick_data):
        # This has a logic error - doesn't properly check array length
        prices = [tick['close'] for tick in self.history[symbol][-self.window:]]
        if len(prices) > 0:  # Bug: should check if len(prices) >= window
            avg = np.mean(prices)
            if tick_data['close'] > avg * 1.05:
                self.order_target(symbol, 100)
            elif tick_data['close'] < avg * 0.95:
                self.order_target(symbol, -100)
    """
    
    # Example failure data
    example_failure = {
        "error": "IndexError: list index out of range",
        "metrics": {
            "sharpe": -0.2,
            "drawdown": 0.25,
            "win_rate": 0.35
        }
    }
    
    # Create handler and analyze/improve
    handler = StrategyFailureHandler()
    
    # Analyze the failure
    analysis = handler.analyze_failure(example_code, example_failure)
    print(f"Analysis complete. Found issues: {analysis['analysis'][:100]}...")
    
    # Generate improved strategy
    filepath, improved_code = handler.generate_improved_strategy(
        example_code, example_failure, "Should handle market volatility better"
    )
    
    print(f"Improved strategy generated and saved to: {filepath}")
    print(f"Preview: {improved_code[:200]}...") 