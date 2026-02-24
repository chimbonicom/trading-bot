#!/usr/bin/env python3
"""
Daily Open Fakeout Bot Configuration Manager
Easy way to configure bot settings without editing files manually
"""

import os
import sys
from pathlib import Path

def print_header():
    """Print the configuration header"""
    print("🔧 Daily Open Fakeout Bot Configuration Manager")
    print("=" * 60)
    print("🎯 Configure your trading bot settings easily")
    print("✅ No manual file editing required")
    print("📊 Professional and user-friendly interface")
    print("=" * 60)

def get_config_path():
    """Get the configuration file path"""
    config_dir = Path(__file__).parent / "config"
    config_file = config_dir / "daily_open_bot_config.env"
    return config_file

def read_current_config():
    """Read current configuration"""
    config_file = get_config_path()
    config = {}
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

def write_config(config):
    """Write configuration to file"""
    config_file = get_config_path()
    config_file.parent.mkdir(exist_ok=True)
    
    # Read the original file to preserve comments and structure
    original_lines = []
    if config_file.exists():
        with open(config_file, 'r') as f:
            original_lines = f.readlines()
    
    # Create new content
    new_content = []
    in_trading_section = False
    in_risk_section = False
    in_behavior_section = False
    in_advanced_section = False
    
    for line in original_lines:
        stripped = line.strip()
        
        # Check section headers
        if "Trading Configuration" in line:
            in_trading_section = True
            in_risk_section = False
            in_behavior_section = False
            in_advanced_section = False
        elif "Risk Management" in line:
            in_trading_section = False
            in_risk_section = True
            in_behavior_section = False
            in_advanced_section = False
        elif "Bot Behavior" in line:
            in_trading_section = False
            in_risk_section = False
            in_behavior_section = True
            in_advanced_section = False
        elif "Advanced Settings" in line:
            in_trading_section = False
            in_risk_section = False
            in_behavior_section = False
            in_advanced_section = True
        
        # Replace configuration values
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=')[0].strip()
            if key in config:
                new_content.append(f"{key}={config[key]}\n")
            else:
                new_content.append(line)
        else:
            new_content.append(line)
    
    # Write the new configuration
    with open(config_file, 'w') as f:
        f.writelines(new_content)

def get_user_input(prompt, default_value, input_type=str):
    """Get user input with default value"""
    try:
        user_input = input(f"{prompt} (default: {default_value}): ").strip()
        if not user_input:
            return default_value
        return input_type(user_input)
    except ValueError:
        print(f"❌ Invalid input. Using default: {default_value}")
        return default_value

def configure_trading_settings(config):
    """Configure trading settings"""
    print("\n📊 Trading Configuration")
    print("-" * 30)
    
    # Symbols
    current_symbols = config.get('SYMBOLS', 'GBPJPY.s')
    print(f"\nAvailable symbols: GBPJPY.s, EURUSD.s, USDJPY.s, GBPUSD.s, etc.")
    symbols = get_user_input("Enter symbols to trade (comma-separated)", current_symbols)
    config['SYMBOLS'] = symbols
    
    # Lot sizes
    symbols_list = [s.strip() for s in symbols.split(',')]
    current_lot_sizes = config.get('LOT_SIZES', '0.5')
    lot_sizes_list = current_lot_sizes.split(',')
    
    new_lot_sizes = []
    for i, symbol in enumerate(symbols_list):
        default_lot = lot_sizes_list[i] if i < len(lot_sizes_list) else '0.5'
        lot_size = get_user_input(f"Lot size for {symbol}", default_lot, float)
        new_lot_sizes.append(str(lot_size))
    
    config['LOT_SIZES'] = ','.join(new_lot_sizes)
    
    # Timeframe
    current_timeframe = config.get('TIMEFRAME', 'M5')
    timeframe = get_user_input("Timeframe (M1, M5, M15, H1, H4, D1)", current_timeframe)
    config['TIMEFRAME'] = timeframe

def configure_risk_settings(config):
    """Configure risk management settings"""
    print("\n🎯 Risk Management")
    print("-" * 30)
    
    # Max open trades
    current_max_trades = config.get('MAX_OPEN_TRADES', '1')
    max_trades = get_user_input("Maximum open trades at once", current_max_trades, int)
    config['MAX_OPEN_TRADES'] = str(max_trades)
    
    # Risk:Reward ratio
    current_rr = config.get('RISK_REWARD_RATIO', '3.0')
    rr_ratio = get_user_input("Risk:Reward ratio (e.g., 3.0 for 1:3)", current_rr, float)
    config['RISK_REWARD_RATIO'] = str(rr_ratio)
    
    # Sweep tolerance
    current_sweep = config.get('SWEEP_TOLERANCE_PIPS', '1')
    sweep_tolerance = get_user_input("Sweep tolerance in pips", current_sweep, float)
    config['SWEEP_TOLERANCE_PIPS'] = str(sweep_tolerance)
    
    # Bias confirmation
    current_bias = config.get('BIAS_CONFIRMATION_PIPS', '10')
    bias_confirmation = get_user_input("Bias confirmation in pips", current_bias, float)
    config['BIAS_CONFIRMATION_PIPS'] = str(bias_confirmation)

def configure_behavior_settings(config):
    """Configure bot behavior settings"""
    print("\n🤖 Bot Behavior")
    print("-" * 30)
    
    # Auto reports
    current_auto_reports = config.get('AUTO_REPORTS', 'true')
    auto_reports = get_user_input("Enable automatic reports (true/false)", current_auto_reports)
    config['AUTO_REPORTS'] = auto_reports.lower()
    
    # Report interval
    current_interval = config.get('REPORT_INTERVAL', '3600')
    interval = get_user_input("Report interval in seconds (3600 = 1 hour)", current_interval, int)
    config['REPORT_INTERVAL'] = str(interval)
    
    # Log level
    current_log_level = config.get('LOG_LEVEL', 'INFO')
    log_level = get_user_input("Log level (INFO, DEBUG, WARNING, ERROR)", current_log_level)
    config['LOG_LEVEL'] = log_level.upper()

def configure_advanced_settings(config):
    """Configure advanced settings"""
    print("\n⚙️ Advanced Settings")
    print("-" * 30)
    
    # Magic number
    current_magic = config.get('MAGIC_NUMBER', '234002')
    magic_number = get_user_input("Magic number for trade identification", current_magic, int)
    config['MAGIC_NUMBER'] = str(magic_number)
    
    # Order deviation
    current_deviation = config.get('ORDER_DEVIATION', '20')
    deviation = get_user_input("Order deviation in points", current_deviation, int)
    config['ORDER_DEVIATION'] = str(deviation)
    
    # Min trade interval
    current_interval = config.get('MIN_TRADE_INTERVAL', '60')
    min_interval = get_user_input("Minimum time between trades in seconds", current_interval, int)
    config['MIN_TRADE_INTERVAL'] = str(min_interval)
    
    # Smart logging
    current_smart_log = config.get('ENABLE_SMART_LOGGING', 'true')
    smart_log = get_user_input("Enable smart logging (true/false)", current_smart_log)
    config['ENABLE_SMART_LOGGING'] = smart_log.lower()
    
    # Performance tracking
    current_perf_track = config.get('ENABLE_PERFORMANCE_TRACKING', 'true')
    perf_track = get_user_input("Enable performance tracking (true/false)", current_perf_track)
    config['ENABLE_PERFORMANCE_TRACKING'] = perf_track.lower()

def show_configuration_summary(config):
    """Show configuration summary"""
    print("\n📋 Configuration Summary")
    print("=" * 50)
    
    symbols = config.get('SYMBOLS', 'GBPJPY.s')
    lot_sizes = config.get('LOT_SIZES', '0.5')
    symbols_list = [s.strip() for s in symbols.split(',')]
    lot_sizes_list = lot_sizes.split(',')
    
    print(f"📊 Symbols: {symbols}")
    print(f"💰 Lot Sizes: {', '.join([f'{symbol}: {lot_sizes_list[i] if i < len(lot_sizes_list) else '0.5'}' for i, symbol in enumerate(symbols_list)])}")
    print(f"⏰ Timeframe: {config.get('TIMEFRAME', 'M5')}")
    print(f"🎯 Max Open Trades: {config.get('MAX_OPEN_TRADES', '1')}")
    print(f"📈 Risk:Reward Ratio: 1:{config.get('RISK_REWARD_RATIO', '3.0')}")
    print(f"🔄 Sweep Tolerance: {config.get('SWEEP_TOLERANCE_PIPS', '1')} pips")
    print(f"📊 Bias Confirmation: {config.get('BIAS_CONFIRMATION_PIPS', '10')} pips")
    print(f"📄 Auto Reports: {config.get('AUTO_REPORTS', 'true')}")
    print(f"⏱️ Report Interval: {config.get('REPORT_INTERVAL', '3600')} seconds")
    print(f"🔢 Magic Number: {config.get('MAGIC_NUMBER', '234002')}")
    print("=" * 50)

def main():
    """Main configuration function"""
    print_header()
    
    # Read current configuration
    config = read_current_config()
    
    while True:
        print("\n🔧 Configuration Options:")
        print("1. 📊 Trading Settings (Symbols, Lot Sizes, Timeframe)")
        print("2. 🎯 Risk Management (Max Trades, RR Ratio, Tolerances)")
        print("3. 🤖 Bot Behavior (Reports, Logging)")
        print("4. ⚙️ Advanced Settings (Magic Number, Intervals)")
        print("5. 📋 Show Current Configuration")
        print("6. 💾 Save Configuration")
        print("7. 🚪 Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            configure_trading_settings(config)
        elif choice == '2':
            configure_risk_settings(config)
        elif choice == '3':
            configure_behavior_settings(config)
        elif choice == '4':
            configure_advanced_settings(config)
        elif choice == '5':
            show_configuration_summary(config)
        elif choice == '6':
            write_config(config)
            print("\n✅ Configuration saved successfully!")
            print(f"📁 Location: {get_config_path()}")
        elif choice == '7':
            print("\n👋 Configuration manager closed.")
            print("💡 Run 'python run_daily_open_bot.py' to start your bot!")
            break
        else:
            print("❌ Invalid option. Please select 1-7.")

if __name__ == "__main__":
    main()
