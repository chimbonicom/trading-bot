#!/usr/bin/env python3
"""
Trend Following Bot Launcher
This bot uses EMA crossover + RSI + ATR for trend following strategy
"""

from src.trend_following_bot import TrendFollowingBot

def main():
    print("🚀 Starting Trend Following Bot...")
    print("=" * 50)
    print("Strategy: EMA Crossover + RSI + ATR")
    print("Features:")
    print("✅ EMA 9/21 Crossover")
    print("✅ RSI Momentum Confirmation")
    print("✅ ATR-based Dynamic SL/TP")
    print("✅ Multi-Symbol Trading")
    print("✅ Risk Management")
    print("✅ MT5 Integration")
    print("=" * 50)
    
    try:
        bot = TrendFollowingBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Trend Following Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
