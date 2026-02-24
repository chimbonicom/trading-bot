import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pytz

def test_daily_open_detection():
    # Connect to MT5
    if not mt5.initialize():
        print("❌ Failed to initialize MT5")
        return
    
    print("✅ Connected to MT5")
    
    symbol = "GBPJPY.s"
    
    # Method 1: D1 timeframe
    try:
        d1_data = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
        if d1_data is not None and len(d1_data) > 0:
            d1_open = d1_data[0]['open']
            print(f"📊 D1 Daily Open: {d1_open:.5f}")
        else:
            print("❌ D1 data not available")
    except Exception as e:
        print(f"❌ D1 error: {e}")
    
    # Method 2: UTC M1
    try:
        today_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        utc_data = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, today_utc, 1440)
        if utc_data is not None and len(utc_data) > 0:
            utc_open = utc_data[0]['open']
            print(f"📊 UTC M1 Daily Open: {utc_open:.5f}")
        else:
            print("❌ UTC M1 data not available")
    except Exception as e:
        print(f"❌ UTC M1 error: {e}")
    
    # Method 3: Local M1
    try:
        today_local = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        local_data = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, today_local, 1440)
        if local_data is not None and len(local_data) > 0:
            local_open = local_data[0]['open']
            print(f"📊 Local M1 Daily Open: {local_open:.5f}")
        else:
            print("❌ Local M1 data not available")
    except Exception as e:
        print(f"❌ Local M1 error: {e}")
    
    # Method 4: M5 timeframe
    try:
        m5_data = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, today_utc, 288)
        if m5_data is not None and len(m5_data) > 0:
            m5_open = m5_data[0]['open']
            print(f"📊 M5 Daily Open: {m5_open:.5f}")
        else:
            print("❌ M5 data not available")
    except Exception as e:
        print(f"❌ M5 error: {e}")
    
    # Current price
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            current_price = tick.ask
            print(f"📊 Current Price: {current_price:.5f}")
        else:
            print("❌ Current price not available")
    except Exception as e:
        print(f"❌ Current price error: {e}")
    
    mt5.shutdown()

if __name__ == "__main__":
    test_daily_open_detection()
