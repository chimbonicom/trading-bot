#!/usr/bin/env python3
"""
Test MT5 Connection and Available Symbols
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.env')
load_dotenv(config_path)

def test_mt5_connection():
    print("🔍 Testing MT5 Connection...")
    print("=" * 50)
    
    # Initialize MT5
    if not mt5.initialize():
        print("❌ MT5 initialization failed!")
        return False
    
    print("✅ MT5 initialized successfully")
    
    # Login
    login = int(os.getenv('MT5_LOGIN'))
    password = os.getenv('MT5_PASSWORD')
    server = os.getenv('MT5_SERVER')
    
    if not mt5.login(login=login, password=password, server=server):
        print("❌ MT5 login failed!")
        return False
    
    print(f"✅ Logged in to {server}")
    
    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print(f"✅ Account: {account_info.login}")
        print(f"✅ Balance: {account_info.balance}")
        print(f"✅ Equity: {account_info.equity}")
    
    # Get available symbols
    symbols = mt5.symbols_get()
    if symbols:
        print(f"✅ Available symbols: {len(symbols)}")
        
        # Show first 10 symbols
        print("\n📊 First 10 symbols:")
        for i, symbol in enumerate(symbols[:10]):
            print(f"   {i+1}. {symbol.name}")
    
    # Test specific symbol
    test_symbol = os.getenv('SYMBOL', 'GBPJPY.s')
    print(f"\n🔍 Testing symbol: {test_symbol}")
    
    # Get symbol info
    symbol_info = mt5.symbol_info(test_symbol)
    if symbol_info:
        print(f"✅ Symbol {test_symbol} is available")
        print(f"   Bid: {symbol_info.bid}")
        print(f"   Ask: {symbol_info.ask}")
        print(f"   Spread: {symbol_info.spread}")
        print(f"   Trade mode: {symbol_info.trade_mode}")
    else:
        print(f"❌ Symbol {test_symbol} not available")
    
    # Test getting OHLC data
    print(f"\n📈 Testing OHLC data for {test_symbol}...")
    rates = mt5.copy_rates_from_pos(test_symbol, mt5.TIMEFRAME_M1, 0, 10)
    if rates is not None:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        print(f"✅ Got {len(df)} candles")
        print(f"   Latest candle: {df.iloc[-1]['time']}")
        print(f"   Latest close: {df.iloc[-1]['close']}")
    else:
        print("❌ Failed to get OHLC data")
    
    # Check if market is open
    print(f"\n🕐 Checking market status...")
    current_time = datetime.now()
    print(f"   Current time: {current_time}")
    
    if current_time.weekday() < 5:
        print("   ✅ Market should be open (weekday)")
    else:
        print("   ❌ Market is likely closed (weekend)")
    
    # Test placing a small trade
    print(f"\n🧪 Testing trade placement...")
    symbol = "GBPJPY.s"
    
    # Get current price
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        current_price = symbol_info.ask
        
        # Place a small buy order
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": current_price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Test trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Trade placed successfully!")
            print(f"   Order ticket: {result.order}")
            print(f"   Price: {result.price}")
            
            # Close the test trade immediately
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_SELL,
                "position": result.order,
                "price": symbol_info.bid,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close test trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            close_result = mt5.order_send(close_request)
            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Test trade closed successfully!")
            else:
                print(f"❌ Failed to close test trade: {close_result.comment}")
        else:
            print(f"❌ Trade failed: {result.comment}")
    else:
        print(f"❌ Cannot get symbol info for {symbol}")
    
    mt5.shutdown()
    return True

if __name__ == "__main__":
    test_mt5_connection()
