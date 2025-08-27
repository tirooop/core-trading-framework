# Core Trading Framework

A robust and extensible foundation for building quantitative trading systems, providing essential components for data management, trade execution, risk management, and system monitoring.

![Core Trading Framework](https://via.placeholder.com/800x400.png?text=Core+Trading+Framework)

## 🌟 Key Features

### Data Management
- **Multi-Source Data Integration**: Support for multiple data providers
- **Real-time Data Streaming**: Live market data processing
- **Historical Data Management**: Efficient historical data storage and retrieval
- **Data Validation**: Comprehensive data quality checks and validation

### Trade Execution
- **Multi-Broker Support**: Integration with multiple broker APIs
- **Order Management**: Comprehensive order lifecycle management
- **Execution Analytics**: Trade execution performance analysis
- **Slippage Management**: Intelligent slippage handling and optimization

### Risk Management
- **Portfolio Risk Monitoring**: Real-time portfolio risk assessment
- **Position Limits**: Dynamic position sizing and limits
- **Risk Alerts**: Automated risk warning system
- **Compliance Monitoring**: Regulatory compliance tracking

### System Infrastructure
- **Modular Architecture**: Extensible component-based design
- **Event-Driven Processing**: Asynchronous event handling
- **Configuration Management**: Flexible configuration system
- **Logging and Monitoring**: Comprehensive system monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Database (PostgreSQL, SQLite)
- Message queue (Redis, RabbitMQ)
- Basic understanding of trading systems

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/core-trading-framework.git
cd core-trading-framework
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure the system**:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

## 🧠 Usage Examples

### Data Management

```python
from core_trading_framework import DataManager

# Initialize data manager
data_manager = DataManager()

# Get real-time data
real_time_data = data_manager.get_real_time_data(
    symbols=["AAPL", "MSFT", "GOOGL"],
    data_types=["price", "volume", "bid", "ask"]
)

# Get historical data
historical_data = data_manager.get_historical_data(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31",
    interval="1d"
)

print(f"Latest AAPL price: ${real_time_data['AAPL']['price']:.2f}")
```

### Trade Execution

```python
from core_trading_framework import TradeExecutor

# Initialize trade executor
executor = TradeExecutor()

# Place a market order
order = executor.place_order(
    symbol="AAPL",
    side="buy",
    quantity=100,
    order_type="market",
    broker="ibkr"
)

print(f"Order placed: {order.order_id}")
print(f"Status: {order.status}")

# Monitor order status
order_status = executor.get_order_status(order.order_id)
print(f"Order status: {order_status}")
```

### Risk Management

```python
from core_trading_framework import RiskManager

# Initialize risk manager
risk_manager = RiskManager()

# Check portfolio risk
portfolio_risk = risk_manager.assess_portfolio_risk(
    positions=current_positions,
    market_data=market_data
)

print(f"Portfolio VaR: ${portfolio_risk.var:.2f}")
print(f"Portfolio Beta: {portfolio_risk.beta:.3f}")
print(f"Risk Level: {portfolio_risk.risk_level}")

# Check position limits
position_check = risk_manager.check_position_limits(
    symbol="AAPL",
    quantity=1000,
    current_positions=current_positions
)

if not position_check.allowed:
    print(f"Position limit exceeded: {position_check.reason}")
```

### System Monitoring

```python
from core_trading_framework import SystemMonitor

# Initialize system monitor
monitor = SystemMonitor()

# Start system monitoring
monitor.start_monitoring(
    components=["data_manager", "trade_executor", "risk_manager"],
    callback=alert_callback
)

def alert_callback(alert):
    if alert.level == "critical":
        print(f"Critical alert: {alert.message}")
    elif alert.level == "warning":
        print(f"Warning: {alert.message}")

# Get system status
system_status = monitor.get_system_status()
print(f"System health: {system_status.health}")
print(f"Active components: {system_status.active_components}")
```

## 🏗️ Architecture Components

### Data Layer
- **Data Providers**: Interface for multiple data sources
- **Data Processors**: Real-time and batch data processing
- **Data Storage**: Efficient data storage and retrieval
- **Data Validation**: Data quality and integrity checks

### Execution Layer
- **Order Management**: Order creation, modification, and cancellation
- **Broker Integration**: Multi-broker API integration
- **Execution Engine**: Trade execution logic and optimization
- **Execution Analytics**: Performance and cost analysis

### Risk Layer
- **Risk Models**: Portfolio and position risk models
- **Risk Limits**: Position and portfolio limit management
- **Risk Monitoring**: Real-time risk surveillance
- **Risk Reporting**: Risk metrics and reporting

### Infrastructure Layer
- **Event System**: Asynchronous event processing
- **Configuration**: System configuration management
- **Logging**: Comprehensive logging and audit trails
- **Monitoring**: System health and performance monitoring

## 🔧 Configuration

### System Configuration
```yaml
# config.yaml
system:
  name: "Core Trading Framework"
  version: "1.0.0"
  environment: "production"
  
data:
  providers:
    yfinance:
      enabled: true
      cache_duration: "5m"
    alpha_vantage:
      enabled: false
      api_key: "your-api-key"
    ibkr:
      enabled: true
      host: "127.0.0.1"
      port: 7497
      
execution:
  brokers:
    ibkr:
      enabled: true
      paper_trading: true
      max_orders_per_second: 10
    alpaca:
      enabled: false
      api_key: "your-api-key"
      
risk:
  position_limits:
    max_position_size: 0.1  # 10% of portfolio
    max_sector_exposure: 0.3  # 30% per sector
  portfolio_limits:
    max_drawdown: 0.2  # 20% max drawdown
    var_limit: 0.05  # 5% VaR limit
    
monitoring:
  log_level: "INFO"
  metrics_interval: "1m"
  alert_channels: ["email", "slack"]
```

### Database Configuration
```python
# Database configuration
DATABASE_CONFIG = {
    "type": "postgresql",  # or "sqlite", "mysql"
    "host": "localhost",
    "port": 5432,
    "database": "trading_framework",
    "username": "trading_user",
    "password": "secure_password",
    "pool_size": 10,
    "max_overflow": 20
}
```

### Event System Configuration
```python
# Event system configuration
EVENT_CONFIG = {
    "queue_type": "redis",  # or "rabbitmq", "memory"
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
    "max_workers": 4,
    "event_timeout": 30
}
```

## 📊 Performance Metrics

### System Performance
- **Throughput**: Orders per second processing capacity
- **Latency**: End-to-end order execution time
- **Uptime**: System availability percentage
- **Error Rate**: System error frequency

### Trading Performance
- **Execution Quality**: Slippage and market impact analysis
- **Order Fill Rate**: Percentage of filled orders
- **Execution Speed**: Time from order to fill
- **Cost Analysis**: Trading costs and fees

### Risk Metrics
- **Portfolio VaR**: Value at Risk calculations
- **Position Limits**: Limit utilization tracking
- **Risk Alerts**: Alert frequency and severity
- **Compliance**: Regulatory compliance status

## 🛠️ Advanced Features

### Custom Data Providers
```python
# Create custom data provider
class CustomDataProvider:
    def __init__(self, config):
        self.config = config
    
    def get_real_time_data(self, symbols, data_types):
        # Implement real-time data retrieval
        pass
    
    def get_historical_data(self, symbol, start_date, end_date, interval):
        # Implement historical data retrieval
        pass

# Register custom provider
data_manager.register_provider("custom", CustomDataProvider(config))
```

### Custom Risk Models
```python
# Create custom risk model
class CustomRiskModel:
    def __init__(self, parameters):
        self.parameters = parameters
    
    def calculate_risk(self, positions, market_data):
        # Implement custom risk calculation
        pass
    
    def check_limits(self, new_position, current_positions):
        # Implement custom limit checking
        pass

# Register custom risk model
risk_manager.register_model("custom", CustomRiskModel(parameters))
```

### Event Handlers
```python
# Create custom event handler
class CustomEventHandler:
    def __init__(self):
        self.processed_events = 0
    
    def handle_order_filled(self, event):
        # Handle order filled event
        self.processed_events += 1
        print(f"Order filled: {event.order_id}")
    
    def handle_risk_alert(self, event):
        # Handle risk alert event
        print(f"Risk alert: {event.message}")

# Register event handler
event_system.register_handler("order_filled", CustomEventHandler())
```

## 📁 Project Structure

```
core-trading-framework/
├── core/
│   ├── data/                   # Data management components
│   │   ├── providers.py         # Data provider interfaces
│   │   ├── processors.py        # Data processing logic
│   │   └── storage.py           # Data storage management
│   ├── execution/               # Trade execution components
│   │   ├── order_manager.py     # Order management
│   │   ├── broker_interface.py   # Broker integration
│   │   └── execution_engine.py   # Execution logic
│   ├── risk/                    # Risk management components
│   │   ├── risk_models.py       # Risk calculation models
│   │   ├── position_limits.py   # Position limit management
│   │   └── portfolio_risk.py     # Portfolio risk assessment
│   └── infrastructure/          # Infrastructure components
│       ├── events.py             # Event system
│       ├── config.py             # Configuration management
│       ├── logging.py            # Logging system
│       └── monitoring.py         # System monitoring
├── adapters/
│   ├── brokers/                  # Broker-specific adapters
│   │   ├── ibkr_adapter.py       # Interactive Brokers adapter
│   │   ├── alpaca_adapter.py     # Alpaca adapter
│   │   └── td_adapter.py         # TD Ameritrade adapter
│   └── data_providers/           # Data provider adapters
│       ├── yfinance_adapter.py   # Yahoo Finance adapter
│       ├── alpha_vantage_adapter.py # Alpha Vantage adapter
│       └── custom_adapter.py     # Custom data adapter
├── utils/
│   ├── database.py               # Database utilities
│   ├── validation.py             # Data validation utilities
│   ├── serialization.py          # Data serialization
│   └── helpers.py                # Helper functions
├── examples/
│   ├── basic_usage.py            # Basic usage examples
│   ├── data_management.py        # Data management examples
│   ├── trade_execution.py        # Trade execution examples
│   └── risk_management.py        # Risk management examples
├── tests/
│   ├── test_data.py              # Data layer tests
│   ├── test_execution.py         # Execution layer tests
│   ├── test_risk.py              # Risk layer tests
│   └── test_infrastructure.py    # Infrastructure tests
├── config.yaml                   # Configuration file
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## 🎯 Use Cases

### Trading System Developers
- Build custom trading systems
- Integrate multiple data sources
- Implement custom execution logic
- Add risk management features

### Quantitative Researchers
- Prototype trading strategies
- Test execution algorithms
- Validate risk models
- Analyze trading performance

### Financial Institutions
- Build institutional trading systems
- Implement compliance monitoring
- Manage risk across portfolios
- Scale trading operations

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Do not risk money you cannot afford to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.

## 📞 Contact

- Email: your.email@example.com
- GitHub: @your_username
- LinkedIn: your_username

## 🙏 Acknowledgments

Thanks to all developers and researchers who contributed to this project.

---

**⭐ If this project helps you, please give us a star!** 