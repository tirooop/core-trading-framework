"""
Portfolio Optimizer
Optimizes strategy allocations for maximum return and minimum risk
"""
import os
import json
import logging
import datetime
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Optimizes portfolio allocations across multiple trading strategies
    to maximize risk-adjusted returns.
    """
    
    def __init__(self, 
                 results_dir: str = "results/portfolio_optimization",
                 risk_free_rate: float = 0.0):
        """
        Initialize the portfolio optimizer.
        
        Args:
            results_dir: Directory to save optimization results
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
        """
        self.results_dir = results_dir
        self.risk_free_rate = risk_free_rate
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        logger.info("Initialized Portfolio Optimizer")
    
    def _calculate_portfolio_metrics(self, 
                                   weights: np.ndarray, 
                                   returns: np.ndarray, 
                                   cov_matrix: np.ndarray) -> Tuple[float, float, float]:
        """
        Calculate portfolio expected return, volatility, and Sharpe ratio.
        
        Args:
            weights: Array of weights for each strategy
            returns: Array of expected returns for each strategy
            cov_matrix: Covariance matrix of strategy returns
            
        Returns:
            Tuple of (expected_return, volatility, sharpe_ratio)
        """
        # Expected portfolio return
        portfolio_return = np.sum(returns * weights)
        
        # Portfolio volatility (standard deviation)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Sharpe ratio
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return portfolio_return, portfolio_volatility, sharpe_ratio
    
    def _objective_sharpe(self, 
                         weights: np.ndarray, 
                         returns: np.ndarray, 
                         cov_matrix: np.ndarray) -> float:
        """
        Objective function to maximize Sharpe ratio (negated for minimization).
        
        Args:
            weights: Array of weights for each strategy
            returns: Array of expected returns for each strategy
            cov_matrix: Covariance matrix of strategy returns
            
        Returns:
            Negated Sharpe ratio (for minimization)
        """
        _, _, sharpe = self._calculate_portfolio_metrics(weights, returns, cov_matrix)
        return -sharpe  # Negate for minimization
    
    def _objective_min_volatility(self, 
                                weights: np.ndarray, 
                                cov_matrix: np.ndarray) -> float:
        """
        Objective function to minimize portfolio volatility.
        
        Args:
            weights: Array of weights for each strategy
            cov_matrix: Covariance matrix of strategy returns
            
        Returns:
            Portfolio volatility
        """
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    
    def _objective_max_return(self, 
                            weights: np.ndarray, 
                            returns: np.ndarray) -> float:
        """
        Objective function to maximize portfolio return (negated for minimization).
        
        Args:
            weights: Array of weights for each strategy
            returns: Array of expected returns for each strategy
            
        Returns:
            Negated portfolio return (for minimization)
        """
        return -np.sum(returns * weights)  # Negate for minimization
    
    def optimize(self, 
                strategy_returns: Dict[str, pd.Series], 
                optimization_goal: str = "sharpe", 
                constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optimize portfolio allocations across strategies.
        
        Args:
            strategy_returns: Dictionary mapping strategy names to return series
            optimization_goal: Optimization objective ("sharpe", "min_volatility", "max_return")
            constraints: Additional constraints for optimization
            
        Returns:
            Dictionary with optimization results
        """
        logger.info(f"Starting portfolio optimization with goal: {optimization_goal}")
        
        # Extract strategies and convert to DataFrame
        strategies = list(strategy_returns.keys())
        returns_df = pd.DataFrame({name: returns for name, returns in strategy_returns.items()})
        
        # Calculate expected returns and covariance matrix
        expected_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        
        # Number of strategies
        num_strategies = len(strategies)
        
        # Initial weights (equal allocation)
        initial_weights = np.ones(num_strategies) / num_strategies
        
        # Bounds for weights (0 to 1)
        bounds = tuple((0, 1) for _ in range(num_strategies))
        
        # Constraint: weights sum to 1
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        # Add user-defined constraints if provided
        if constraints and 'min_allocation' in constraints:
            min_allocation = constraints['min_allocation']
            constraints_list.append(
                {'type': 'ineq', 'fun': lambda x: x - min_allocation}
            )
        
        if constraints and 'max_allocation' in constraints:
            max_allocation = constraints['max_allocation']
            constraints_list.append(
                {'type': 'ineq', 'fun': lambda x: max_allocation - x}
            )
        
        # Select objective function based on optimization goal
        if optimization_goal == "min_volatility":
            objective = lambda weights: self._objective_min_volatility(weights, cov_matrix.values)
        elif optimization_goal == "max_return":
            objective = lambda weights: self._objective_max_return(weights, expected_returns.values)
        else:  # Default to Sharpe ratio
            objective = lambda weights: self._objective_sharpe(weights, expected_returns.values, cov_matrix.values)
        
        # Run optimization
        try:
            optimization_result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list
            )
            
            # Check if optimization was successful
            if optimization_result['success']:
                optimized_weights = optimization_result['x']
                
                # Calculate portfolio metrics with optimized weights
                portfolio_return, portfolio_volatility, sharpe_ratio = self._calculate_portfolio_metrics(
                    optimized_weights, expected_returns.values, cov_matrix.values
                )
                
                # Create result dictionary
                result = {
                    "success": True,
                    "optimization_goal": optimization_goal,
                    "weights": {strategies[i]: optimized_weights[i] for i in range(num_strategies)},
                    "metrics": {
                        "expected_return": portfolio_return,
                        "volatility": portfolio_volatility,
                        "sharpe_ratio": sharpe_ratio
                    },
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Save result
                self._save_result(result)
                
                logger.info(f"Portfolio optimization successful: Sharpe ratio = {sharpe_ratio:.4f}")
                return result
                
            else:
                error_msg = f"Optimization failed: {optimization_result['message']}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Error in portfolio optimization: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def _save_result(self, result: Dict[str, Any]):
        """Save optimization result to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_optimization_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            # Convert numpy types to Python types for JSON serialization
            serializable_result = self._make_serializable(result)
            
            with open(filepath, 'w') as f:
                json.dump(serializable_result, f, indent=2)
                
            logger.debug(f"Saved optimization result to {filepath}")
        except Exception as e:
            logger.error(f"Error saving optimization result: {str(e)}")
    
    def _make_serializable(self, obj):
        """Convert non-serializable objects to serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(i) for i in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        else:
            return obj
    
    def generate_efficient_frontier(self, 
                                  strategy_returns: Dict[str, pd.Series], 
                                  num_portfolios: int = 20) -> Dict[str, Any]:
        """
        Generate the efficient frontier by calculating multiple portfolios with different risk-return profiles.
        
        Args:
            strategy_returns: Dictionary mapping strategy names to return series
            num_portfolios: Number of portfolios to generate along the frontier
            
        Returns:
            Dictionary with efficient frontier data
        """
        logger.info(f"Generating efficient frontier with {num_portfolios} portfolios")
        
        # Extract strategies and convert to DataFrame
        strategies = list(strategy_returns.keys())
        returns_df = pd.DataFrame({name: returns for name, returns in strategy_returns.items()})
        
        # Calculate expected returns and covariance matrix
        expected_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        
        # Number of strategies
        num_strategies = len(strategies)
        
        # Storage for results
        results = []
        
        try:
            # Generate random portfolios
            for _ in range(num_portfolios):
                # Generate random weights and normalize
                weights = np.random.random(num_strategies)
                weights = weights / np.sum(weights)
                
                # Calculate portfolio metrics
                portfolio_return, portfolio_volatility, sharpe_ratio = self._calculate_portfolio_metrics(
                    weights, expected_returns.values, cov_matrix.values
                )
                
                # Store portfolio data
                portfolio = {
                    "weights": {strategies[i]: weights[i] for i in range(num_strategies)},
                    "return": portfolio_return,
                    "volatility": portfolio_volatility,
                    "sharpe_ratio": sharpe_ratio
                }
                
                results.append(portfolio)
            
            # Find minimum volatility portfolio
            min_vol_portfolio = self.optimize(strategy_returns, "min_volatility")
            
            # Find maximum return portfolio
            max_return_portfolio = self.optimize(strategy_returns, "max_return")
            
            # Find maximum Sharpe ratio portfolio
            max_sharpe_portfolio = self.optimize(strategy_returns, "sharpe")
            
            # Add special portfolios to results
            if min_vol_portfolio["success"]:
                min_vol = {
                    "weights": min_vol_portfolio["weights"],
                    "return": min_vol_portfolio["metrics"]["expected_return"],
                    "volatility": min_vol_portfolio["metrics"]["volatility"],
                    "sharpe_ratio": min_vol_portfolio["metrics"]["sharpe_ratio"],
                    "type": "min_volatility"
                }
                results.append(min_vol)
                
            if max_return_portfolio["success"]:
                max_ret = {
                    "weights": max_return_portfolio["weights"],
                    "return": max_return_portfolio["metrics"]["expected_return"],
                    "volatility": max_return_portfolio["metrics"]["volatility"],
                    "sharpe_ratio": max_return_portfolio["metrics"]["sharpe_ratio"],
                    "type": "max_return"
                }
                results.append(max_ret)
                
            if max_sharpe_portfolio["success"]:
                max_sharpe = {
                    "weights": max_sharpe_portfolio["weights"],
                    "return": max_sharpe_portfolio["metrics"]["expected_return"],
                    "volatility": max_sharpe_portfolio["metrics"]["volatility"],
                    "sharpe_ratio": max_sharpe_portfolio["metrics"]["sharpe_ratio"],
                    "type": "max_sharpe"
                }
                results.append(max_sharpe)
            
            # Save frontier to file
            frontier_data = {
                "portfolios": results,
                "strategies": strategies,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"efficient_frontier_{timestamp}.json"
            filepath = os.path.join(self.results_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(self._make_serializable(frontier_data), f, indent=2)
                
            logger.info(f"Generated efficient frontier saved to {filepath}")
            
            return frontier_data
            
        except Exception as e:
            error_msg = f"Error generating efficient frontier: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.datetime.now().isoformat()
            }

# Example usage
if __name__ == "__main__":
    # Example strategy returns data
    np.random.seed(42)  # For reproducibility
    
    # Create simulated return series for different strategies
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    strategy_returns = {
        "MA_Crossover": pd.Series(np.random.normal(0.001, 0.01, 100), index=dates),
        "RSI_Strategy": pd.Series(np.random.normal(0.0015, 0.015, 100), index=dates),
        "Bollinger_Bands": pd.Series(np.random.normal(0.0005, 0.008, 100), index=dates),
        "Trend_Following": pd.Series(np.random.normal(0.002, 0.02, 100), index=dates)
    }
    
    # Add some correlation between strategies
    strategy_returns["RSI_Strategy"] += 0.3 * strategy_returns["MA_Crossover"]
    strategy_returns["Trend_Following"] -= 0.2 * strategy_returns["Bollinger_Bands"]
    
    # Create optimizer and run optimization
    optimizer = PortfolioOptimizer()
    
    # Optimize for maximum Sharpe ratio
    result = optimizer.optimize(strategy_returns, "sharpe")
    print("\nOptimized Portfolio Weights (Sharpe):")
    for strategy, weight in result["weights"].items():
        print(f"  {strategy}: {weight:.4f}")
    print(f"Expected Return: {result['metrics']['expected_return']:.4%}")
    print(f"Volatility: {result['metrics']['volatility']:.4%}")
    print(f"Sharpe Ratio: {result['metrics']['sharpe_ratio']:.4f}")
    
    # Generate efficient frontier
    frontier = optimizer.generate_efficient_frontier(strategy_returns, num_portfolios=50)
    print(f"\nGenerated {len(frontier['portfolios'])} portfolios for the efficient frontier") 