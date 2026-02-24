# 🚀 Daily Open Line Fakeout Bot

A professional MT5 trading bot that implements the **Daily Open Line + Fakeout Pattern** strategy with advanced configuration options and performance tracking.

## 📊 Strategy Overview

**Core Concept**: The bot draws a horizontal line at the current day's open price and waits for fakeout patterns to occur.

### 🎯 Entry Conditions

**Bullish Entry**:
- Price is **above** daily open line (bullish bias)
- A **bearish candle** appears (attempting reversal)
- Followed by a **bullish candle** that sweeps below the previous bearish candle
- **Entry**: When the bullish candle closes

**Bearish Entry**:
- Price is **below** daily open line (bearish bias)
- A **bullish candle** appears (attempting reversal)
- Followed by a **bearish candle** that sweeps above the previous bullish candle
- **Entry**: When the bearish candle closes

### 📈 Risk Management
- **Stop Loss**: Tight, placed just beyond the sweep level
- **Take Profit**: 1:3 Risk:Reward ratio
- **Max Trades**: One trade at a time (configurable)
- **Timeframe**: M5 (5-minute candles)

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.8+
- MetaTrader 5 terminal
- Demo account credentials

### 2. Install Dependencies
```bash
pip install MetaTrader5 pandas numpy python-dotenv
```

### 3. Configure Your Bot
```bash
python configure_bot.py
```

This opens the **Configuration Manager** where you can easily set:
- **Symbols to trade** (default: GBPJPY.s)
- **Lot sizes** for each symbol
- **Risk management** parameters
- **Bot behavior** settings
- **Advanced options**

## 🚀 Quick Start

### Option 1: Use Configuration Manager (Recommended)
```bash
python run_daily_open_bot.py
```
Then select:
1. **Configure Bot Settings** (first time)
2. **Start Bot** (after configuration)

### Option 2: Direct Configuration
1. Edit `config/daily_open_bot_config.env`
2. Run: `python run_daily_open_bot.py`

## ⚙️ Configuration Options

### 📊 Trading Settings
- **SYMBOLS**: Comma-separated list (e.g., `GBPJPY.s,EURUSD.s`)
- **LOT_SIZES**: Lot sizes for each symbol (e.g., `0.5,0.3`)
- **TIMEFRAME**: M1, M5, M15, H1, H4, D1

### 🎯 Risk Management
- **MAX_OPEN_TRADES**: Maximum concurrent trades
- **RISK_REWARD_RATIO**: Profit target multiplier (default: 3.0)
- **SWEEP_TOLERANCE_PIPS**: Minimum sweep distance
- **BIAS_CONFIRMATION_PIPS**: Distance from daily open for bias

### 🤖 Bot Behavior
- **AUTO_REPORTS**: Enable automatic performance reports
- **REPORT_INTERVAL**: How often to generate reports (seconds)
- **LOG_LEVEL**: INFO, DEBUG, WARNING, ERROR

### ⚙️ Advanced Settings
- **MAGIC_NUMBER**: Unique trade identifier
- **ORDER_DEVIATION**: Slippage tolerance
- **MIN_TRADE_INTERVAL**: Minimum time between trades
- **ENABLE_SMART_LOGGING**: Reduce log spam
- **ENABLE_PERFORMANCE_TRACKING**: Track trade performance

## 📈 Performance Analysis

### Generate Reports
```bash
python generate_report.py
```

### Automatic Reports
The bot generates reports automatically every hour (configurable) with:
- **Win/Loss ratio**
- **Total P&L**
- **Best/Worst trades**
- **Daily performance breakdown**
- **Professional HTML dashboard**

## 📁 Project Structure

```
Tradingbot/
├── src/
│   ├── daily_open_fakeout_bot.py    # Main bot logic
│   └── performance_analyzer.py      # Performance analysis
├── config/
│   ├── config.env                   # Smart Bot config
│   └── daily_open_bot_config.env    # Daily Open Bot config
├── logs/                            # Bot logs
├── reports/                         # Performance reports
├── configure_bot.py                 # Configuration manager
├── run_daily_open_bot.py           # Main runner
└── generate_report.py              # Report generator
```

## 🔧 Configuration Examples

### Example 1: Single Symbol (Default)
```env
SYMBOLS=GBPJPY.s
LOT_SIZES=0.5
MAX_OPEN_TRADES=1
RISK_REWARD_RATIO=3.0
```

### Example 2: Multiple Symbols
```env
SYMBOLS=GBPJPY.s,EURUSD.s,USDJPY.s
LOT_SIZES=0.5,0.3,0.4
MAX_OPEN_TRADES=3
RISK_REWARD_RATIO=3.0
```

### Example 3: Conservative Settings
```env
SYMBOLS=GBPJPY.s
LOT_SIZES=0.1
MAX_OPEN_TRADES=1
RISK_REWARD_RATIO=2.5
SWEEP_TOLERANCE_PIPS=2
BIAS_CONFIRMATION_PIPS=15
```

## 📊 Monitoring & Logs

### Real-time Monitoring
The bot provides clean, professional logging:
- **Entry/Exit notifications**
- **SL/TP hits**
- **Bias changes**
- **Performance updates**

### Log Files
- Location: `logs/daily_open_bot.log`
- Format: Timestamp, Level, Message
- Smart logging to avoid spam

## 🎯 Best Practices

### 1. Start Small
- Begin with 0.1 lot size
- Test on demo account first
- Monitor performance closely

### 2. Optimize Settings
- Adjust sweep tolerance based on volatility
- Fine-tune bias confirmation distance
- Test different timeframes

### 3. Risk Management
- Never risk more than 2% per trade
- Use appropriate lot sizes
- Monitor drawdown

### 4. Performance Review
- Generate reports regularly
- Analyze win/loss patterns
- Adjust strategy based on results

## 🚨 Important Notes

### ⚠️ Risk Warning
- This is a **demo/educational tool**
- Past performance doesn't guarantee future results
- Always test thoroughly before live trading
- Use proper risk management

### 🔧 Technical Requirements
- MT5 terminal must be running
- Stable internet connection
- Sufficient account balance for lot sizes

### 📊 Performance Expectations
- Strategy works best in trending markets
- May have periods of no trades
- Requires patience and discipline

## 🆘 Troubleshooting

### Common Issues

**1. MT5 Connection Failed**
- Ensure MT5 terminal is running
- Check login credentials
- Verify server connection

**2. No Trades Being Taken**
- Check if bias conditions are met
- Verify sweep tolerance settings
- Ensure sufficient price movement

**3. Configuration Errors**
- Run `python configure_bot.py`
- Check file permissions
- Verify symbol names

### Getting Help
1. Check the logs in `logs/daily_open_bot.log`
2. Verify configuration settings
3. Test with different parameters
4. Generate performance reports for analysis

## 🎉 Success Tips

1. **Patience**: This strategy requires waiting for proper setups
2. **Consistency**: Stick to your configuration
3. **Monitoring**: Regularly check performance
4. **Optimization**: Adjust settings based on results
5. **Risk Management**: Never compromise on safety

---

**Happy Trading! 🚀📈**

*Remember: The best trader is the one who manages risk properly and stays disciplined.*
