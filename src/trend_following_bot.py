import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import os
from dotenv import load_dotenv

# Load configuration
import os
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.env')
load_dotenv(config_path)

class TrendFollowingBot:
    def __init__(self):
        # Parse multiple symbols
        symbols_str = os.getenv('SYMBOLS', 'GBPJPY.s')
        self.symbols = [s.strip() for s in symbols_str.split(',')]
        self.timeframe = os.getenv('TIMEFRAME', 'M1')
        self.lot_size = float(os.getenv('LOT_SIZE', '0.01'))
        self.max_risk_percent = float(os.getenv('MAX_RISK_PERCENT', '2'))
        self.max_open_trades = int(os.getenv('MAX_OPEN_TRADES', '3'))
        self.risk_reward_ratio = float(os.getenv('RISK_REWARD_RATIO', '2.5'))
        
        # Trend Following Specific Parameters
        self.fast_ema = 9
        self.slow_ema = 21
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.atr_period = 14
        self.min_atr_multiplier = 1.5
        
        # Setup logging
        self.setup_logging()
        
        # Initialize MT5 connection
        self.connect_mt5()
        
        # Bot data for each symbol
        self.symbol_data = {}
        for symbol in self.symbols:
            self.symbol_data[symbol] = {
                'trend_direction': "NEUTRAL",
                'last_signal_time': 0,
                'consecutive_wins': 0,
                'consecutive_losses': 0
            }
        
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        import os
        logs_path = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(logs_path, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(logs_path, 'trend_following_bot.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_mt5(self):
        """Connect to MT5 terminal"""
        if not mt5.initialize():
            self.logger.error("MT5 initialization failed!")
            return False
            
        # Login to account
        login = int(os.getenv('MT5_LOGIN'))
        password = os.getenv('MT5_PASSWORD')
        server = os.getenv('MT5_SERVER')
        
        if not mt5.login(login=login, password=password, server=server):
            self.logger.error("MT5 login failed!")
            return False
            
        self.logger.info(f"Connected to MT5: {server}")
        return True
        
    def get_ohlc_data(self, symbol: str, timeframe: str, periods: int) -> pd.DataFrame:
        """Get OHLC data from MT5"""
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        
        rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, periods)
        if rates is None:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
        
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period).mean()
        
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
        
    def detect_trend_strength(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Detect trend direction and strength using EMAs"""
        if len(df) < self.slow_ema:
            return "NEUTRAL", 0.0
            
        # Calculate EMAs
        fast_ema = self.calculate_ema(df, self.fast_ema)
        slow_ema = self.calculate_ema(df, self.slow_ema)
        
        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]
        
        # Calculate trend strength
        ema_distance = abs(current_fast - current_slow) / current_slow * 100
        
        # Determine trend direction
        if current_fast > current_slow and prev_fast > prev_slow:
            if ema_distance > 0.1:  # Strong trend threshold
                return "STRONG_BULLISH", ema_distance
            else:
                return "BULLISH", ema_distance
        elif current_fast < current_slow and prev_fast < prev_slow:
            if ema_distance > 0.1:  # Strong trend threshold
                return "STRONG_BEARISH", ema_distance
            else:
                return "BEARISH", ema_distance
        else:
            return "NEUTRAL", ema_distance
            
    def check_momentum_confirmation(self, df: pd.DataFrame) -> Tuple[bool, bool]:
        """Check RSI momentum for buy/sell confirmation"""
        if len(df) < self.rsi_period:
            return False, False
            
        rsi = self.calculate_rsi(df, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        
        buy_signal = current_rsi < self.rsi_oversold and current_rsi > 20  # Oversold but not extreme
        sell_signal = current_rsi > self.rsi_overbought and current_rsi < 80  # Overbought but not extreme
        
        return buy_signal, sell_signal
        
    def calculate_dynamic_sl_tp(self, symbol: str, entry_price: float, df: pd.DataFrame, is_buy: bool) -> Tuple[float, float]:
        """Calculate dynamic SL and TP based on ATR"""
        atr = self.calculate_atr(df, self.atr_period)
        current_atr = atr.iloc[-1]
        
        # Use ATR for SL distance
        sl_distance = current_atr * self.min_atr_multiplier
        
        # Ensure minimum SL distance
        min_sl_distance = 0.0010  # 10 pips minimum
        sl_distance = max(sl_distance, min_sl_distance)
        
        if is_buy:
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * self.risk_reward_ratio)
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * self.risk_reward_ratio)
            
        return stop_loss, take_profit
        
    def should_buy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Tuple[bool, str, float]:
        """Determine if we should buy based on trend following logic"""
        if len(df) < self.slow_ema:
            return False, "", 0.0
            
        # Check trend direction
        trend_direction, trend_strength = self.detect_trend_strength(df)
        
        # Check momentum
        buy_momentum, sell_momentum = self.check_momentum_confirmation(df)
        
        # Buy conditions
        if (trend_direction in ["BULLISH", "STRONG_BULLISH"] and 
            buy_momentum and 
            trend_strength > 0.05):  # Minimum trend strength
            
            return True, trend_direction, trend_strength
            
        return False, "", 0.0
        
    def should_sell(self, symbol: str, df: pd.DataFrame, current_price: float) -> Tuple[bool, str, float]:
        """Determine if we should sell based on trend following logic"""
        if len(df) < self.slow_ema:
            return False, "", 0.0
            
        # Check trend direction
        trend_direction, trend_strength = self.detect_trend_strength(df)
        
        # Check momentum
        buy_momentum, sell_momentum = self.check_momentum_confirmation(df)
        
        # Sell conditions
        if (trend_direction in ["BEARISH", "STRONG_BEARISH"] and 
            sell_momentum and 
            trend_strength > 0.05):  # Minimum trend strength
            
            return True, trend_direction, trend_strength
            
        return False, "", 0.0
        
    def place_buy_order(self, symbol: str, current_price: float, trend_info: str, strength: float, df: pd.DataFrame):
        """Place a buy order with dynamic SL/TP"""
        stop_loss, take_profit = self.calculate_dynamic_sl_tp(symbol, current_price, df, True)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": current_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234001,  # Different magic number for this bot
            "comment": f"TrendBot_Buy_{trend_info}_Str{strength:.2f}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"BUY order placed: {trend_info}, Strength: {strength:.2f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            return True
        else:
            self.logger.error(f"BUY order failed: {result.comment}")
            return False
            
    def place_sell_order(self, symbol: str, current_price: float, trend_info: str, strength: float, df: pd.DataFrame):
        """Place a sell order with dynamic SL/TP"""
        stop_loss, take_profit = self.calculate_dynamic_sl_tp(symbol, current_price, df, False)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": current_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234001,  # Different magic number for this bot
            "comment": f"TrendBot_Sell_{trend_info}_Str{strength:.2f}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"SELL order placed: {trend_info}, Strength: {strength:.2f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            return True
        else:
            self.logger.error(f"SELL order failed: {result.comment}")
            return False
            
    def get_open_positions_count(self, symbol: str = None) -> int:
        """Get number of open positions for this bot (using magic number)"""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions:
            # Count only positions with this bot's magic number
            bot_positions = [pos for pos in positions if pos.magic == 234001]
            return len(bot_positions)
        return 0
        
    def run(self):
        """Main trading loop for trend following strategy"""
        self.logger.info(f"Starting Trend Following Bot for symbols: {', '.join(self.symbols)}")
        
        while True:
            try:
                total_open_positions = self.get_open_positions_count()
                
                for symbol in self.symbols:
                    try:
                        # Check if we can take more trades
                        if total_open_positions >= self.max_open_trades:
                            self.logger.info(f"Maximum open trades reached: {total_open_positions}")
                            break
                            
                        # Get current market data for this symbol
                        df = self.get_ohlc_data(symbol, self.timeframe, 100)  # Need more data for indicators
                        if df.empty:
                            self.logger.warning(f"Failed to get market data for {symbol}")
                            continue
                            
                        # Get current price
                        current_price = df.iloc[-1]['close']
                        
                        # Check for buy signal
                        should_buy, trend_info, strength = self.should_buy(symbol, df, current_price)
                        if should_buy:
                            if self.place_buy_order(symbol, current_price, trend_info, strength, df):
                                total_open_positions += 1
                                self.logger.info(f"BUY signal for {symbol}: {trend_info}, Strength: {strength:.2f}")
                                
                        # Check for sell signal
                        should_sell, trend_info, strength = self.should_sell(symbol, df, current_price)
                        if should_sell:
                            if self.place_sell_order(symbol, current_price, trend_info, strength, df):
                                total_open_positions += 1
                                self.logger.info(f"SELL signal for {symbol}: {trend_info}, Strength: {strength:.2f}")
                                
                        # Log current status for this symbol
                        trend_direction, trend_strength = self.detect_trend_strength(df)
                        buy_momentum, sell_momentum = self.check_momentum_confirmation(df)
                        self.logger.info(f"{symbol}: Price: {current_price:.5f}, Trend: {trend_direction}, Strength: {trend_strength:.2f}, RSI Buy: {buy_momentum}, RSI Sell: {sell_momentum}")
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {symbol}: {e}")
                        continue
                        
                # Wait before next analysis cycle
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(10)
                
    def __del__(self):
        """Cleanup on exit"""
        mt5.shutdown()

if __name__ == "__main__":
    bot = TrendFollowingBot()
    bot.run()
