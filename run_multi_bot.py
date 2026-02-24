#!/usr/bin/env python3
"""
Multi-Bot Manager
Runs multiple trading bots simultaneously with different strategies
"""

import threading
import time
from src.smart_trading_bot import SmartTradingBot
from src.trend_following_bot import TrendFollowingBot

def run_smart_bot():
    """Run the Smart Trading Bot (S/R + Candlestick Patterns)"""
    print("🤖 Starting Smart Trading Bot...")
    try:
        bot = SmartTradingBot()
        bot.run()
    except Exception as e:
        print(f"❌ Smart Bot Error: {e}")

def run_trend_bot():
    """Run the Trend Following Bot (EMA + RSI + ATR)"""
    print("📈 Starting Trend Following Bot...")
    try:
        bot = TrendFollowingBot()
        bot.run()
    except Exception as e:
        print(f"❌ Trend Bot Error: {e}")

def main():
    print("🚀 Multi-Bot Trading System")
    print("=" * 60)
    print("🤖 Bot 1: Smart Trading Bot (S/R + Candlestick Patterns)")
    print("   - Support/Resistance Detection")
    print("   - Strong Candlestick Patterns")
    print("   - Role Reversal Logic")
    print("   - Dynamic SL/TP")
    print()
    print("📈 Bot 2: Trend Following Bot (EMA + RSI + ATR)")
    print("   - EMA 9/21 Crossover")
    print("   - RSI Momentum Confirmation")
    print("   - ATR-based Dynamic SL/TP")
    print("   - Trend Strength Analysis")
    print("=" * 60)
    
    choice = input("Choose option:\n1. Run Smart Bot Only\n2. Run Trend Bot Only\n3. Run Both Bots\nEnter choice (1-3): ")
    
    if choice == "1":
        print("\n🤖 Running Smart Trading Bot only...")
        run_smart_bot()
    elif choice == "2":
        print("\n📈 Running Trend Following Bot only...")
        run_trend_bot()
    elif choice == "3":
        print("\n🚀 Running Both Bots Simultaneously...")
        
        # Create threads for each bot
        smart_thread = threading.Thread(target=run_smart_bot, daemon=True)
        trend_thread = threading.Thread(target=run_trend_bot, daemon=True)
        
        # Start both bots
        smart_thread.start()
        time.sleep(2)  # Small delay to avoid conflicts
        trend_thread.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping all bots...")
    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    main()
