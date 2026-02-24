#!/usr/bin/env python3
"""
Daily Open Line Fakeout Bot Runner
Main script to start the Daily Open Fakeout Bot
"""

import sys
import os
from pathlib import Path

def print_welcome():
    """Print welcome message and instructions"""
    print("🚀 Daily Open Line Fakeout Bot")
    print("=" * 60)
    print("🎯 Strategy: Daily Open Line + Fakeout Patterns")
    print("⏰ Timeframe: M5 (5-minute candles)")
    print("📊 Risk:Reward: 1:3")
    print("💰 Default: GBPJPY with 0.5 lot size")
    print("=" * 60)
    print("📋 Before starting, make sure:")
    print("✅ MT5 terminal is running")
    print("✅ Demo account is logged in")
    print("✅ Internet connection is stable")
    print("=" * 60)

def check_configuration():
    """Check if configuration exists"""
    config_file = Path("config/daily_open_bot_config.env")
    if not config_file.exists():
        print("❌ Configuration file not found!")
        print("💡 Run 'python configure_bot.py' to set up your bot first.")
        return False
    return True

def main():
    """Main function"""
    print_welcome()
    
    # Check configuration
    if not check_configuration():
        return 1
    
    # Ask user if they want to configure first
    print("\n🔧 Configuration Options:")
    print("1. 🚀 Start Bot (use current settings)")
    print("2. ⚙️ Configure Bot Settings")
    print("3. 📊 Generate Performance Report")
    print("4. 🚪 Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        print("\n🚀 Starting Daily Open Fakeout Bot...")
        print("💡 Press Ctrl+C to stop the bot")
        print("=" * 60)
        
        try:
            from src.daily_open_fakeout_bot import DailyOpenFakeoutBot
            bot = DailyOpenFakeoutBot()
            bot.run()
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
            print("👋 Thanks for using Daily Open Fakeout Bot!")
        except Exception as e:
            print(f"\n❌ Error starting bot: {e}")
            return 1
            
    elif choice == '2':
        print("\n🔧 Opening Configuration Manager...")
        try:
            import subprocess
            subprocess.run([sys.executable, "configure_bot.py"])
        except Exception as e:
            print(f"❌ Error opening configuration: {e}")
            return 1
            
    elif choice == '3':
        print("\n📊 Generating Performance Report...")
        try:
            import subprocess
            subprocess.run([sys.executable, "generate_report.py"])
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return 1
            
    elif choice == '4':
        print("\n👋 Goodbye!")
        return 0
        
    else:
        print("❌ Invalid option. Please select 1-4.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
