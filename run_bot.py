#!/usr/bin/env python3
"""
Smart Trading Bot Launcher
Launches the MT5 trading bot with support/resistance and candlestick pattern detection
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from smart_trading_bot import SmartTradingBot

def main():
    print("🚀 Starting Smart Trading Bot...")
    print("=" * 50)
    print("Features:")
    print("✅ Smart Support/Resistance Detection")
    print("✅ Strong Candlestick Pattern Recognition")
    print("✅ 1-Minute Timeframe Analysis")
    print("✅ Risk Management")
    print("✅ MT5 Integration")
    print("=" * 50)
    
    try:
        bot = SmartTradingBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
