# Smart Trading Bot for MT5

A sophisticated trading bot that combines **smart support/resistance detection** with **strong candlestick pattern recognition** for MetaTrader 5.

## 🚀 Features

### Smart Support/Resistance Detection
- **Swing High/Low Analysis**: Identifies key reversal points
- **Level Clustering**: Groups nearby levels for accuracy
- **Touch Count Filtering**: Only uses levels tested multiple times
- **Dynamic Updates**: Continuously updates levels in real-time

### Strong Candlestick Patterns
**Bullish Patterns (for Support Zone):**
- ✅ Bullish Engulfing
- ✅ Hammer
- ✅ Inverted Hammer
- ✅ Morning Star
- ✅ Three White Soldiers
- ✅ Piercing Line
- ✅ Bullish Harami
- ✅ Tweezers Bottom

**Bearish Patterns (for Resistance Zone):**
- ✅ Bearish Engulfing
- ✅ Shooting Star
- ✅ Hanging Man
- ✅ Evening Star
- ✅ Three Black Crows
- ✅ Dark Cloud Cover
- ✅ Bearish Harami
- ✅ Tweezers Top

### Trading Strategy
1. **Detects Support/Resistance zones**
2. **Waits for price to approach these zones**
3. **Scans for strong candlestick patterns**
4. **Calculates pattern strength**
5. **Places trades with proper risk management**

## 📋 Requirements

- Python 3.8+
- MetaTrader 5 terminal installed
- Demo or live MT5 account
- Windows OS (MT5 Python API requirement)

## 🛠️ Installation

1. **Clone/Download the project**
2. **Activate virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install MetaTrader5 pandas numpy python-dotenv
   ```

## ⚙️ Configuration

Edit `config/config.env` with your settings:

```env
# MT5 Account
MT5_LOGIN=2001258379
MT5_PASSWORD=MA1@ANGaaa
MT5_SERVER=JustMarkets-Demo

# Trading Parameters
SYMBOL=EURUSD
TIMEFRAME=M1
LOT_SIZE=0.01
STOP_LOSS_PIPS=20
TAKE_PROFIT_PIPS=40

# Risk Management
MAX_RISK_PERCENT=2
MAX_OPEN_TRADES=3

# Support/Resistance Parameters
SR_LOOKBACK_PERIODS=100
SR_TOUCH_THRESHOLD=3
SR_ZONE_BUFFER_PIPS=5

# Pattern Parameters
PATTERN_CONFIRMATION_CANDLES=3
MIN_PATTERN_STRENGTH=7
```

## 🚀 Usage

1. **Make sure MT5 is running and logged in**
2. **Run the bot:**
   ```bash
   python run_bot.py
   ```

## 📊 How It Works

### Support/Resistance Detection
1. Analyzes last 100 candles for swing highs/lows
2. Clusters nearby levels together
3. Filters by minimum touch count (3 touches)
4. Creates zones with buffer for entry

### Pattern Recognition
1. Scans for all strong candlestick patterns
2. Calculates pattern strength based on:
   - Number of patterns found
   - Volume confirmation
   - Trend alignment
3. Only trades if strength ≥ 7

### Trading Logic
- **BUY**: Price near support + strong bullish pattern
- **SELL**: Price near resistance + strong bearish pattern
- **Risk Management**: Fixed stop loss and take profit
- **Position Management**: Maximum 3 open trades

## 📈 Performance Monitoring

The bot logs all activities to:
- Console output
- `logs/trading_bot.log`

Monitor:
- Pattern detection
- Trade entries/exits
- Support/resistance levels
- Error messages

## ⚠️ Important Notes

1. **Demo Testing**: Always test on demo account first
2. **Risk Management**: Never risk more than you can afford to lose
3. **Market Conditions**: Bot works best in trending markets
4. **Timeframes**: Currently optimized for 1-minute timeframe
5. **Symbols**: Tested with EURUSD, may need adjustments for other pairs

## 🔧 Customization

### Adding New Patterns
Edit `src/smart_trading_bot.py`:
1. Add new pattern detection method
2. Include in `scan_bullish_patterns()` or `scan_bearish_patterns()`
3. Test thoroughly

### Adjusting Parameters
Modify `config/config.env`:
- Increase `MIN_PATTERN_STRENGTH` for fewer trades
- Decrease `SR_TOUCH_THRESHOLD` for more levels
- Adjust `STOP_LOSS_PIPS` and `TAKE_PROFIT_PIPS`

## 🆘 Troubleshooting

### Common Issues:
1. **MT5 Connection Failed**: Check if MT5 is running and logged in
2. **No Trades**: Increase pattern sensitivity or decrease strength requirement
3. **Too Many Trades**: Increase `MIN_PATTERN_STRENGTH`
4. **Poor Performance**: Check market conditions and adjust parameters

### Logs Location:
- `logs/trading_bot.log` - Detailed trading logs
- Console output - Real-time status

## 📞 Support

For issues or questions:
1. Check the logs for error messages
2. Verify MT5 connection and account status
3. Test with different parameters
4. Ensure market is open and liquid

## ⚖️ Disclaimer

This bot is for educational purposes. Trading involves risk of loss. Always:
- Test thoroughly on demo accounts
- Understand the strategy before live trading
- Never risk more than you can afford to lose
- Monitor the bot's performance regularly

---

**Happy Trading! 🎯**
