"""
Multi-threaded Strategy Batch Trainer
Allows parallel training and evaluation of multiple trading strategies
"""
import os
import time
import logging
import datetime
import threading
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Callable, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyBatchTrainer:
    """
    Handles batch training of multiple trading strategies using multi-threading.
    """
    
    def __init__(self, 
                 max_workers: int = 3, 
                 results_dir: str = "results/strategy_training",
                 notify_function: Optional[Callable] = None):
        """
        Initialize the batch trainer.
        
        Args:
            max_workers: Maximum number of worker threads for parallel training
            results_dir: Directory to save training results
            notify_function: Optional callback function for notifications
        """
        self.max_workers = max_workers
        self.results_dir = results_dir
        self.notify_function = notify_function
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.ongoing_tasks = {}
        self.completed_tasks = {}
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        logger.info(f"Initialized Strategy Batch Trainer with {max_workers} workers")
    
    def _notify(self, message: str):
        """Send notification if notify function is provided."""
        if self.notify_function:
            self.notify_function(message)
        logger.info(message)
    
    def train_strategy(self, 
                      strategy_name: str, 
                      strategy_params: Dict[str, Any], 
                      data: pd.DataFrame,
                      training_function: Callable,
                      evaluation_metrics: List[str] = None) -> Dict[str, Any]:
        """
        Train and evaluate a single strategy.
        
        Args:
            strategy_name: Name of the strategy
            strategy_params: Parameters for the strategy
            data: Market data for training
            training_function: Function that performs the actual training
            evaluation_metrics: List of metrics to evaluate
            
        Returns:
            Dictionary with training results
        """
        start_time = time.time()
        
        try:
            # Notify start
            self._notify(f"Started training strategy '{strategy_name}'")
            
            # Call the provided training function
            training_result = training_function(strategy_name, strategy_params, data)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Prepare result with some basic metrics
            result = {
                "strategy_name": strategy_name,
                "parameters": strategy_params,
                "execution_time": execution_time,
                "training_result": training_result,
                "status": "completed",
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Save result to file
            self._save_result(strategy_name, result)
            
            # Notify completion
            self._notify(f"Completed training strategy '{strategy_name}' in {execution_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            error_msg = f"Error training strategy '{strategy_name}': {str(e)}"
            logger.error(error_msg)
            
            # Prepare error result
            result = {
                "strategy_name": strategy_name,
                "parameters": strategy_params,
                "execution_time": time.time() - start_time,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Save error result
            self._save_result(strategy_name, result, is_error=True)
            
            # Notify error
            self._notify(f"Failed training strategy '{strategy_name}': {str(e)}")
            
            return result
    
    def _save_result(self, strategy_name: str, result: Dict[str, Any], is_error: bool = False):
        """Save training result to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        status = "error" if is_error else "success"
        filename = f"{strategy_name}_{timestamp}_{status}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            # Convert non-serializable objects
            serializable_result = self._make_serializable(result)
            
            # Save to file
            with open(filepath, 'w') as f:
                import json
                json.dump(serializable_result, f, indent=2)
                
            logger.debug(f"Saved result to {filepath}")
        except Exception as e:
            logger.error(f"Error saving result to file: {str(e)}")
    
    def _make_serializable(self, obj):
        """Convert non-serializable objects to serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(i) for i in obj]
        elif isinstance(obj, (np.ndarray, pd.Series)):
            return obj.tolist()
        elif isinstance(obj, (pd.DataFrame)):
            return obj.to_dict()
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    def submit_batch(self, 
                    strategies: List[Tuple[str, Dict[str, Any]]], 
                    data: pd.DataFrame,
                    training_function: Callable) -> Dict[str, Any]:
        """
        Submit a batch of strategies for training.
        
        Args:
            strategies: List of tuples (strategy_name, strategy_params)
            data: Market data for training
            training_function: Function that performs the actual training
            
        Returns:
            Dictionary with task information
        """
        futures = {}
        batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self._notify(f"Starting batch training of {len(strategies)} strategies")
        
        for strategy_name, params in strategies:
            future = self.executor.submit(
                self.train_strategy, 
                strategy_name, 
                params, 
                data,
                training_function
            )
            futures[future] = strategy_name
            
            # Store in ongoing tasks
            task_id = f"{batch_id}_{strategy_name}"
            self.ongoing_tasks[task_id] = {
                "strategy_name": strategy_name,
                "parameters": params,
                "start_time": datetime.datetime.now().isoformat(),
                "status": "running",
                "batch_id": batch_id
            }
        
        # Create a monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_futures, 
            args=(futures, batch_id)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return {
            "batch_id": batch_id,
            "num_strategies": len(strategies),
            "status": "submitted"
        }
    
    def _monitor_futures(self, futures: Dict, batch_id: str):
        """Monitor futures and update task status."""
        for future in as_completed(futures):
            strategy_name = futures[future]
            task_id = f"{batch_id}_{strategy_name}"
            
            try:
                result = future.result()
                
                # Update completed tasks
                self.completed_tasks[task_id] = result
                
                # Remove from ongoing
                if task_id in self.ongoing_tasks:
                    del self.ongoing_tasks[task_id]
                
            except Exception as e:
                logger.error(f"Exception in future for {strategy_name}: {str(e)}")
                
                # Update as failed
                if task_id in self.ongoing_tasks:
                    self.ongoing_tasks[task_id]["status"] = "failed"
                    self.ongoing_tasks[task_id]["error"] = str(e)
                    
                    # Move to completed
                    self.completed_tasks[task_id] = self.ongoing_tasks[task_id]
                    del self.ongoing_tasks[task_id]
        
        # Batch completed
        self._notify(f"Completed batch training {batch_id}")
        
        # Generate summary for the batch
        self._generate_batch_summary(batch_id)
    
    def _generate_batch_summary(self, batch_id: str):
        """Generate summary for a completed batch."""
        batch_tasks = {k: v for k, v in self.completed_tasks.items() if k.startswith(batch_id)}
        
        if not batch_tasks:
            logger.warning(f"No completed tasks found for batch {batch_id}")
            return
        
        # Count successes and failures
        success_count = sum(1 for t in batch_tasks.values() if t.get("status") == "completed")
        failure_count = sum(1 for t in batch_tasks.values() if t.get("status") == "failed")
        
        # Generate summary
        summary = f"""
Batch Training Summary (ID: {batch_id})
----------------------------------------
Total Strategies: {len(batch_tasks)}
Successful: {success_count}
Failed: {failure_count}

Top Performing Strategies:
"""
        
        # Add top performing strategies if metrics available
        try:
            # Sort by a performance metric if available
            sorted_strategies = sorted(
                [t for t in batch_tasks.values() if t.get("status") == "completed"],
                key=lambda x: x.get("training_result", {}).get("score", 0),
                reverse=True
            )
            
            for i, strategy in enumerate(sorted_strategies[:3], 1):
                score = strategy.get("training_result", {}).get("score", "N/A")
                summary += f"{i}. {strategy['strategy_name']}: Score {score}\n"
                
        except Exception as e:
            logger.error(f"Error generating performance summary: {str(e)}")
            summary += "Performance data unavailable\n"
        
        # Notify summary
        self._notify(summary)
        
        # Save summary to file
        try:
            summary_file = os.path.join(self.results_dir, f"batch_summary_{batch_id}.txt")
            with open(summary_file, 'w') as f:
                f.write(summary)
            logger.info(f"Saved batch summary to {summary_file}")
        except Exception as e:
            logger.error(f"Error saving batch summary: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all tasks."""
        return {
            "ongoing_tasks": len(self.ongoing_tasks),
            "completed_tasks": len(self.completed_tasks),
            "ongoing_details": list(self.ongoing_tasks.values()),
            "active_workers": self.max_workers
        }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)
        logger.info("Strategy Batch Trainer shutdown complete")

# Example usage
if __name__ == "__main__":
    # Example data
    data = pd.DataFrame({
        'date': pd.date_range(start='2023-01-01', periods=100),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 101,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Example training function
    def mock_training(strategy_name, params, data):
        time.sleep(2)  # Simulate training time
        return {
            "score": np.random.random(),
            "metrics": {
                "sharpe": np.random.random() * 2,
                "drawdown": np.random.random() * 0.2
            }
        }
    
    # Example notification function
    def mock_notify(message):
        print(f"NOTIFICATION: {message}")
    
    # Create trainer and submit batch
    trainer = StrategyBatchTrainer(max_workers=3, notify_function=mock_notify)
    
    strategies = [
        ("MA_Crossover", {"short_window": 10, "long_window": 50}),
        ("RSI_Strategy", {"period": 14, "overbought": 70, "oversold": 30}),
        ("Bollinger_Bands", {"window": 20, "num_std": 2})
    ]
    
    batch_info = trainer.submit_batch(strategies, data, mock_training)
    print(f"Submitted batch: {batch_info}")
    
    # Keep main thread alive for demonstration
    try:
        while len(trainer.ongoing_tasks) > 0:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        trainer.shutdown() 