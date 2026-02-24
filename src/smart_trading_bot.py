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

# Pattern reliability weights (stronger patterns = higher score)
PATTERN_WEIGHTS = {
    'BULLISH_ENGULFING': 4, 'BEARISH_ENGULFING': 4,
    'MORNING_STAR': 4, 'EVENING_STAR': 4,
    'THREE_WHITE_SOLDIERS': 3, 'THREE_BLACK_CROWS': 3,
    'PIERCING_LINE': 3, 'DARK_CLOUD_COVER': 3,
    'HAMMER': 2, 'INVERTED_HAMMER': 2, 'SHOOTING_STAR': 2, 'HANGING_MAN': 2,
    'BULLISH_HARAMI': 2, 'BEARISH_HARAMI': 2,
    'TWEEZERS_BOTTOM': 1, 'TWEEZERS_TOP': 1,
}

class SmartTradingBot:
    def __init__(self):
        # Parse multiple symbols
        symbols_str = os.getenv('SYMBOLS', 'GBPJPY.s')
        self.symbols = [s.strip() for s in symbols_str.split(',')]
        self.timeframe = os.getenv('TIMEFRAME', 'M1')
        self.lot_size = float(os.getenv('LOT_SIZE', '0.01'))
        self.stop_loss_pips = int(os.getenv('STOP_LOSS_PIPS', '20'))
        self.take_profit_pips = int(os.getenv('TAKE_PROFIT_PIPS', '40'))
        self.max_risk_percent = float(os.getenv('MAX_RISK_PERCENT', '2'))
        self.max_open_trades = int(os.getenv('MAX_OPEN_TRADES', '3'))
        self.sr_lookback = int(os.getenv('SR_LOOKBACK_PERIODS', '200'))
        self.sr_touch_threshold = int(os.getenv('SR_TOUCH_THRESHOLD', '2'))
        self.sr_zone_buffer = int(os.getenv('SR_ZONE_BUFFER_PIPS', '3'))
        self.pattern_confirmation = int(os.getenv('PATTERN_CONFIRMATION_CANDLES', '2'))
        self.min_pattern_strength = int(os.getenv('MIN_PATTERN_STRENGTH', '4'))
        self.risk_reward_ratio = float(os.getenv('RISK_REWARD_RATIO', '2.5'))
        self.sl_breathing_room = int(os.getenv('SL_BREATHING_ROOM_PIPS', '3'))
        
        # Enhanced parameters
        self.higher_tf = os.getenv('HIGHER_TIMEFRAME', 'H1')  # Multi-TF confirmation
        self.atr_period = int(os.getenv('ATR_PERIOD', '14'))
        self.trade_cooldown_mins = int(os.getenv('TRADE_COOLDOWN_MINS', '15'))
        self.max_broken_levels = int(os.getenv('MAX_BROKEN_LEVELS', '5'))
        self.enable_trailing_stop = os.getenv('ENABLE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_activation_pips = int(os.getenv('TRAILING_ACTIVATION_PIPS', '15'))
        self.trailing_distance_pips = int(os.getenv('TRAILING_DISTANCE_PIPS', '10'))
        self.enable_session_filter = os.getenv('ENABLE_SESSION_FILTER', 'true').lower() == 'true'
        
        # Trade cooldown tracking: {symbol: last_trade_timestamp}
        self.last_trade_time: Dict[str, float] = {}
        
        # Setup logging
        self.setup_logging()
        
        # Initialize MT5 connection
        self.connect_mt5()
        
        # Support/Resistance levels with role reversal tracking for each symbol
        self.symbol_data = {}
        for symbol in self.symbols:
            self.symbol_data[symbol] = {
                'support_levels': [],
                'resistance_levels': [],
                'broken_support_levels': [],
                'broken_resistance_levels': [],
                'trend_direction': "NEUTRAL",
                'last_analysis_time': 0
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
                logging.FileHandler(os.path.join(logs_path, 'trading_bot.log')),
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
        
    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol (JPY pairs use 0.01, others 0.0001)"""
        symbol_upper = symbol.upper()
        if 'JPY' in symbol_upper:
            return 0.01
        return 0.0001
    
    def pips_to_price(self, symbol: str, pips: int) -> float:
        """Convert pips to price distance"""
        return pips * self.get_pip_value(symbol)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = None) -> pd.Series:
        """Calculate Average True Range for volatility-based sizing"""
        period = period or self.atr_period
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def is_session_active(self) -> bool:
        """Check if we're in a liquid trading session (London/NY overlap preferred)"""
        if not self.enable_session_filter:
            return True
        hour = datetime.now().hour
        # London: 8-16, NY: 13-21 UTC. Overlap 13-16 is best. Avoid 0-6 (Asian only)
        return 7 <= hour <= 22  # 6 hours of overlap + buffer
    
    def is_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol is on trade cooldown"""
        if symbol not in self.last_trade_time:
            return False
        elapsed = (time.time() - self.last_trade_time[symbol]) / 60
        return elapsed < self.trade_cooldown_mins
    
    def prune_broken_levels(self, symbol: str, current_price: float):
        """Keep only recent broken levels within max_broken_levels"""
        symbol_info = self.symbol_data[symbol]
        pip = self.get_pip_value(symbol)
        
        # Remove broken supports far below price (no longer relevant)
        symbol_info['broken_support_levels'] = [
            lvl for lvl in symbol_info['broken_support_levels']
            if current_price - lvl < 50 * pip  # Within 50 pips
        ][-self.max_broken_levels:]
        
        # Remove broken resistances far above price
        symbol_info['broken_resistance_levels'] = [
            lvl for lvl in symbol_info['broken_resistance_levels']
            if lvl - current_price < 50 * pip
        ][-self.max_broken_levels:]
    
    def get_higher_tf_trend(self, symbol: str) -> str:
        """Get trend from higher timeframe for confirmation"""
        df = self.get_ohlc_data(symbol, self.higher_tf, 50)
        if len(df) < 20:
            return "NEUTRAL"
        return self.detect_trend_direction(df)
    
    def get_ohlc_data(self, symbol: str, timeframe: str, periods: int) -> pd.DataFrame:
        """Get OHLC data from MT5"""
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1,
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, periods)
        if rates is None:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
        
    def detect_trend_direction(self, df: pd.DataFrame) -> str:
        """Detect overall trend direction"""
        if len(df) < 20:
            return "NEUTRAL"
            
        # Use 20-period SMA for trend
        sma_20 = df['close'].rolling(20).mean()
        current_price = df.iloc[-1]['close']
        sma_value = sma_20.iloc[-1]
        
        # Also check recent price action
        recent_highs = df['high'].tail(10).max()
        recent_lows = df['low'].tail(10).min()
        
        if current_price > sma_value and current_price > recent_highs * 0.995:
            return "BULLISH"
        elif current_price < sma_value and current_price < recent_lows * 1.005:
            return "BEARISH"
        else:
            return "NEUTRAL"
            
    def detect_support_resistance_with_role_reversal(self, symbol: str, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """Enhanced Support and Resistance detection with role reversal"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        support_levels = []
        resistance_levels = []
        
        # Find swing highs and lows with more sensitivity
        for i in range(3, len(df) - 3):
            # Resistance (swing high) - more sensitive
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append(highs[i])
                
            # Support (swing low) - more sensitive
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append(lows[i])
        
        # Add price action support/resistance detection
        pip = self.get_pip_value(symbol)
        support_levels.extend(self.detect_price_action_support(df, pip))
        resistance_levels.extend(self.detect_price_action_resistance(df, pip))
        
        # ATR-based tolerance for clustering (adapts to volatility)
        atr = self.calculate_atr(df)
        atr_tolerance = atr.iloc[-1] * 0.3 if len(atr) > 0 else 0.0003
        atr_tolerance = max(atr_tolerance, self.get_pip_value(symbol) * 2)  # Min 2 pips
        
        # Cluster nearby levels
        support_levels = self.cluster_levels(support_levels, tolerance=atr_tolerance)
        resistance_levels = self.cluster_levels(resistance_levels, tolerance=atr_tolerance)
        
        # Filter by touch count (reduced threshold)
        touch_tolerance = self.get_pip_value(symbol) * 2
        support_levels = self.filter_by_touches(df, support_levels, 'support', touch_tolerance)
        resistance_levels = self.filter_by_touches(df, resistance_levels, 'resistance', touch_tolerance)
        
        # Check for role reversals
        self.check_role_reversals(symbol, df, support_levels, resistance_levels)
        
        return support_levels, resistance_levels
        
    def check_role_reversals(self, symbol: str, df: pd.DataFrame, support_levels: List[float], resistance_levels: List[float]):
        """Check for support/resistance role reversals"""
        current_price = df.iloc[-1]['close']
        symbol_info = self.symbol_data[symbol]
        break_threshold = self.get_pip_value(symbol) * 5  # 5 pips beyond level
        
        # Check if support levels have been broken (now resistance)
        for support in support_levels[:]:
            if current_price < support - break_threshold:  # Broken support
                if support not in symbol_info['broken_support_levels']:
                    symbol_info['broken_support_levels'].append(support)
                    self.logger.info(f"{symbol}: Support {support:.5f} broken - now resistance")
                    
        # Check if resistance levels have been broken (now support)
        for resistance in resistance_levels[:]:
            if current_price > resistance + break_threshold:  # Broken resistance
                if resistance not in symbol_info['broken_resistance_levels']:
                    symbol_info['broken_resistance_levels'].append(resistance)
                    self.logger.info(f"{symbol}: Resistance {resistance:.5f} broken - now support")
                    
    def cluster_levels(self, levels: List[float], tolerance: float) -> List[float]:
        """Cluster nearby levels together"""
        if not levels:
            return []
            
        levels = sorted(levels)
        clustered = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) <= tolerance:
                current_cluster.append(level)
            else:
                # Average the cluster
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]
                
        # Add last cluster
        if current_cluster:
            clustered.append(sum(current_cluster) / len(current_cluster))
            
        return clustered
        
    def filter_by_touches(self, df: pd.DataFrame, levels: List[float], level_type: str, tolerance: float = None) -> List[float]:
        """Filter levels by number of touches (reduced threshold)"""
        filtered_levels = []
        if tolerance is None:
            tolerance = 0.0002  # Default 2 pips
        
        for level in levels:
            touches = 0
            
            for i in range(len(df)):
                if level_type == 'support':
                    if abs(df.iloc[i]['low'] - level) <= tolerance:
                        touches += 1
                else:  # resistance
                    if abs(df.iloc[i]['high'] - level) <= tolerance:
                        touches += 1
                        
            if touches >= self.sr_touch_threshold:
                filtered_levels.append(level)
                
        return filtered_levels
        
    def is_near_support(self, symbol: str, current_price: float) -> bool:
        """Check if price is near support level (including broken resistance)"""
        symbol_info = self.symbol_data[symbol]
        zone_buffer = self.pips_to_price(symbol, self.sr_zone_buffer)
        
        # Check current support levels - price within zone
        for support in symbol_info['support_levels']:
            if abs(current_price - support) <= zone_buffer:
                return True
                
        # Check broken resistance levels (now support)
        for broken_resistance in symbol_info['broken_resistance_levels']:
            if abs(current_price - broken_resistance) <= zone_buffer:
                return True
                
        return False
        
    def is_near_resistance(self, symbol: str, current_price: float) -> bool:
        """Check if price is near resistance level (including broken support)"""
        symbol_info = self.symbol_data[symbol]
        zone_buffer = self.pips_to_price(symbol, self.sr_zone_buffer)
        
        # Check current resistance levels - price within zone
        for resistance in symbol_info['resistance_levels']:
            if abs(current_price - resistance) <= zone_buffer:
                return True
                
        # Check broken support levels (now resistance)
        for broken_support in symbol_info['broken_support_levels']:
            if abs(current_price - broken_support) <= zone_buffer:
                return True
                
        return False
        
    def get_spread(self, symbol: str) -> float:
        """Get current spread for a specific symbol (in price terms)"""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info and hasattr(symbol_info, 'spread') and hasattr(symbol_info, 'point'):
            return symbol_info.spread * symbol_info.point
        return self.get_pip_value(symbol) * 2  # Default 2 pips
        
    def calculate_dynamic_sl_tp(self, symbol: str, entry_price: float, entry_candle: pd.Series, is_buy: bool) -> Tuple[float, float]:
        """Calculate dynamic SL and TP based on S/R zones and recent volatility"""
        spread = self.get_spread(symbol)
        symbol_info = self.symbol_data[symbol]
        
        if is_buy:
            # For buy orders - SL below support
            sl_distance = self.calculate_buy_sl_distance(symbol, entry_price, entry_candle, spread)
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * self.risk_reward_ratio)
            
        else:
            # For sell orders - SL above resistance
            sl_distance = self.calculate_sell_sl_distance(symbol, entry_price, entry_candle, spread)
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * self.risk_reward_ratio)
            
        return stop_loss, take_profit
        
    def calculate_buy_sl_distance(self, symbol: str, entry_price: float, entry_candle: pd.Series, spread: float) -> float:
        """Calculate SL distance for buy orders based on nearest support"""
        symbol_info = self.symbol_data[symbol]
        
        # Find the nearest support level below entry
        nearest_support = None
        for support in symbol_info['support_levels']:
            if support < entry_price and (nearest_support is None or support > nearest_support):
                nearest_support = support
                
        # Also check broken resistance levels (now support)
        for broken_resistance in symbol_info['broken_resistance_levels']:
            if broken_resistance < entry_price and (nearest_support is None or broken_resistance > nearest_support):
                nearest_support = broken_resistance
        
        pip = self.get_pip_value(symbol)
        if nearest_support:
            # SL just below the support level
            sl_distance = entry_price - nearest_support + spread + pip
        else:
            # Fallback to candle-based SL (but tighter)
            candle_low = entry_candle['low']
            sl_distance = max(entry_price - candle_low + spread + pip, self.pips_to_price(symbol, 8))
            
        # Ensure reasonable SL distance (not too tight, not too wide)
        sl_distance = max(sl_distance, self.pips_to_price(symbol, 8))
        sl_distance = min(sl_distance, self.pips_to_price(symbol, self.stop_loss_pips))
        
        return sl_distance
        
    def calculate_sell_sl_distance(self, symbol: str, entry_price: float, entry_candle: pd.Series, spread: float) -> float:
        """Calculate SL distance for sell orders based on nearest resistance"""
        symbol_info = self.symbol_data[symbol]
        
        # Find the nearest resistance level above entry
        nearest_resistance = None
        for resistance in symbol_info['resistance_levels']:
            if resistance > entry_price and (nearest_resistance is None or resistance < nearest_resistance):
                nearest_resistance = resistance
                
        # Also check broken support levels (now resistance)
        for broken_support in symbol_info['broken_support_levels']:
            if broken_support > entry_price and (nearest_resistance is None or broken_support < nearest_resistance):
                nearest_resistance = broken_support
        
        pip = self.get_pip_value(symbol)
        if nearest_resistance:
            # SL just above the resistance level
            sl_distance = nearest_resistance - entry_price + spread + pip
        else:
            # Fallback to candle-based SL (but tighter)
            candle_high = entry_candle['high']
            sl_distance = max(candle_high - entry_price + spread + pip, self.pips_to_price(symbol, 8))
            
        # Ensure reasonable SL distance (not too tight, not too wide)
        sl_distance = max(sl_distance, self.pips_to_price(symbol, 8))
        sl_distance = min(sl_distance, self.pips_to_price(symbol, self.stop_loss_pips))
        
        return sl_distance
        
    def detect_price_action_support(self, df: pd.DataFrame, pip: float = 0.0001) -> List[float]:
        """Detect support levels from price action (like your red line)"""
        support_levels = []
        tolerance = pip * 2  # 2 pips tolerance
        
        if len(df) < 10:
            return support_levels
            
        # Look for areas where price bounced multiple times
        for i in range(5, len(df) - 5):
            current_low = df.iloc[i]['low']
            
            # Check if this level has been tested multiple times
            touches = 0
            
            for j in range(max(0, i-20), min(len(df), i+20)):
                if abs(df.iloc[j]['low'] - current_low) <= tolerance:
                    touches += 1
                    
            # If level has been touched 2+ times, it's a potential support
            if touches >= 2:
                support_levels.append(current_low)
                
        return support_levels
        
    def detect_price_action_resistance(self, df: pd.DataFrame, pip: float = 0.0001) -> List[float]:
        """Detect resistance levels from price action"""
        resistance_levels = []
        tolerance = pip * 2  # 2 pips tolerance
        
        if len(df) < 10:
            return resistance_levels
            
        # Look for areas where price was rejected multiple times
        for i in range(5, len(df) - 5):
            current_high = df.iloc[i]['high']
            
            # Check if this level has been tested multiple times
            touches = 0
            
            for j in range(max(0, i-20), min(len(df), i+20)):
                if abs(df.iloc[j]['high'] - current_high) <= tolerance:
                    touches += 1
                    
            # If level has been touched 2+ times, it's a potential resistance
            if touches >= 2:
                resistance_levels.append(current_high)
                
        return resistance_levels
        
    def calculate_buy_confluence(self, symbol: str, df: pd.DataFrame, current_price: float, patterns: List[str]) -> int:
        """Calculate confluence score for buy signals"""
        confluence_score = 0
        symbol_info = self.symbol_data[symbol]
        
        # Higher timeframe trend alignment (multi-TF confirmation)
        higher_tf_trend = self.get_higher_tf_trend(symbol)
        if higher_tf_trend == "BULLISH":
            confluence_score += 2
        elif higher_tf_trend == "NEUTRAL":
            confluence_score += 1
        elif higher_tf_trend == "BEARISH":
            confluence_score -= 1  # Counter-trend trades are riskier
        
        # M1 trend alignment bonus
        if symbol_info['trend_direction'] == "BULLISH":
            confluence_score += 2
        elif symbol_info['trend_direction'] == "NEUTRAL":
            confluence_score += 1
            
        # Volume confirmation
        if len(df) > 0:
            current_volume = df.iloc[-1]['tick_volume']
            avg_volume = df['tick_volume'].tail(20).mean()
            if current_volume > avg_volume * 1.5:
                confluence_score += 2
            elif current_volume > avg_volume * 1.2:
                confluence_score += 1
                
        # Support level strength
        support_count = len(symbol_info['support_levels'])
        if support_count >= 3:
            confluence_score += 2
        elif support_count >= 1:
            confluence_score += 1
            
        # Price action confirmation (last few candles)
        if len(df) >= 3:
            recent_candles = df.tail(3)
            bullish_candles = sum(1 for _, candle in recent_candles.iterrows() if candle['close'] > candle['open'])
            if bullish_candles >= 2:
                confluence_score += 1
                
        return confluence_score
        
    def calculate_sell_confluence(self, symbol: str, df: pd.DataFrame, current_price: float, patterns: List[str]) -> int:
        """Calculate confluence score for sell signals"""
        confluence_score = 0
        symbol_info = self.symbol_data[symbol]
        
        # Higher timeframe trend alignment (multi-TF confirmation)
        higher_tf_trend = self.get_higher_tf_trend(symbol)
        if higher_tf_trend == "BEARISH":
            confluence_score += 2
        elif higher_tf_trend == "NEUTRAL":
            confluence_score += 1
        elif higher_tf_trend == "BULLISH":
            confluence_score -= 1  # Counter-trend trades are riskier
        
        # M1 trend alignment bonus
        if symbol_info['trend_direction'] == "BEARISH":
            confluence_score += 2
        elif symbol_info['trend_direction'] == "NEUTRAL":
            confluence_score += 1
            
        # Volume confirmation
        if len(df) > 0:
            current_volume = df.iloc[-1]['tick_volume']
            avg_volume = df['tick_volume'].tail(20).mean()
            if current_volume > avg_volume * 1.5:
                confluence_score += 2
            elif current_volume > avg_volume * 1.2:
                confluence_score += 1
                
        # Resistance level strength
        resistance_count = len(symbol_info['resistance_levels'])
        if resistance_count >= 3:
            confluence_score += 2
        elif resistance_count >= 1:
            confluence_score += 1
            
        # Price action confirmation (last few candles)
        if len(df) >= 3:
            recent_candles = df.tail(3)
            bearish_candles = sum(1 for _, candle in recent_candles.iterrows() if candle['close'] < candle['open'])
            if bearish_candles >= 2:
                confluence_score += 1
                
        return confluence_score
        
    # STRONG BULLISH CANDLESTICK PATTERNS
    def detect_bullish_engulfing(self, df: pd.DataFrame) -> bool:
        """Detect Bullish Engulfing pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        return (prev['close'] < prev['open'] and  # Previous bearish
                curr['close'] > curr['open'] and  # Current bullish
                curr['open'] < prev['close'] and  # Current opens below prev close
                curr['close'] > prev['open'])     # Current closes above prev open
                
    def detect_hammer(self, df: pd.DataFrame) -> bool:
        """Detect Hammer pattern (more sensitive)"""
        if len(df) < 1:
            return False
            
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        # More sensitive detection
        return (body < lower_shadow * 0.5 and  # Small body (increased from 0.3)
                upper_shadow < body * 0.8 and  # Small upper shadow (increased from 0.5)
                lower_shadow > body * 1.5)     # Long lower shadow
                
    def detect_inverted_hammer(self, df: pd.DataFrame) -> bool:
        """Detect Inverted Hammer pattern"""
        if len(df) < 1:
            return False
            
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        return (body < upper_shadow * 0.3 and  # Small body
                lower_shadow < body * 0.5)     # Small lower shadow
                
    def detect_morning_star(self, df: pd.DataFrame) -> bool:
        """Detect Morning Star pattern"""
        if len(df) < 3:
            return False
            
        first = df.iloc[-3]   # Bearish
        second = df.iloc[-2]  # Small
        third = df.iloc[-1]   # Bullish
        
        first_bearish = first['close'] < first['open']
        second_small = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bullish = third['close'] > third['open']
        
        return first_bearish and second_small and third_bullish
        
    def detect_three_white_soldiers(self, df: pd.DataFrame) -> bool:
        """Detect Three White Soldiers pattern"""
        if len(df) < 3:
            return False
            
        for i in range(1, 4):
            candle = df.iloc[-i]
            if candle['close'] <= candle['open']:  # Must be bullish
                return False
                
        return True
        
    def detect_piercing_line(self, df: pd.DataFrame) -> bool:
        """Detect Piercing Line pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']
        curr_opens_below = curr['open'] < prev['close']
        curr_closes_above_mid = curr['close'] > (prev['open'] + prev['close']) / 2
        
        return prev_bearish and curr_bullish and curr_opens_below and curr_closes_above_mid
        
    def detect_bullish_harami(self, df: pd.DataFrame) -> bool:
        """Detect Bullish Harami pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']
        curr_inside = (curr['high'] < prev['high'] and curr['low'] > prev['low'])
        
        return prev_bearish and curr_bullish and curr_inside
        
    def detect_tweezers_bottom(self, df: pd.DataFrame) -> bool:
        """Detect Tweezers Bottom pattern"""
        if len(df) < 2:
            return False
            
        first = df.iloc[-2]
        second = df.iloc[-1]
        
        tolerance = 0.0001  # 1 pip tolerance
        same_low = abs(first['low'] - second['low']) <= tolerance
        
        return same_low
        
    # STRONG BEARISH CANDLESTICK PATTERNS
    def detect_bearish_engulfing(self, df: pd.DataFrame) -> bool:
        """Detect Bearish Engulfing pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        return (prev['close'] > prev['open'] and  # Previous bullish
                curr['close'] < curr['open'] and  # Current bearish
                curr['open'] > prev['close'] and  # Current opens above prev close
                curr['close'] < prev['open'])     # Current closes below prev open
                
    def detect_shooting_star(self, df: pd.DataFrame) -> bool:
        """Detect Shooting Star pattern"""
        if len(df) < 1:
            return False
            
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        return (body < upper_shadow * 0.3 and  # Small body
                lower_shadow < body * 0.5)     # Small lower shadow
                
    def detect_hanging_man(self, df: pd.DataFrame) -> bool:
        """Detect Hanging Man pattern"""
        if len(df) < 1:
            return False
            
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        return (body < lower_shadow * 0.3 and  # Small body
                upper_shadow < body * 0.5)     # Small upper shadow
                
    def detect_evening_star(self, df: pd.DataFrame) -> bool:
        """Detect Evening Star pattern"""
        if len(df) < 3:
            return False
            
        first = df.iloc[-3]   # Bullish
        second = df.iloc[-2]  # Small
        third = df.iloc[-1]   # Bearish
        
        first_bullish = first['close'] > first['open']
        second_small = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bearish = third['close'] < third['open']
        
        return first_bullish and second_small and third_bearish
        
    def detect_three_black_crows(self, df: pd.DataFrame) -> bool:
        """Detect Three Black Crows pattern"""
        if len(df) < 3:
            return False
            
        for i in range(1, 4):
            candle = df.iloc[-i]
            if candle['close'] >= candle['open']:  # Must be bearish
                return False
                
        return True
        
    def detect_dark_cloud_cover(self, df: pd.DataFrame) -> bool:
        """Detect Dark Cloud Cover pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        prev_bullish = prev['close'] > prev['open']
        curr_bearish = curr['close'] < curr['open']
        curr_opens_above = curr['open'] > prev['high']
        curr_closes_below_mid = curr['close'] < (prev['open'] + prev['close']) / 2
        
        return prev_bullish and curr_bearish and curr_opens_above and curr_closes_below_mid
        
    def detect_bearish_harami(self, df: pd.DataFrame) -> bool:
        """Detect Bearish Harami pattern"""
        if len(df) < 2:
            return False
            
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        prev_bullish = prev['close'] > prev['open']
        curr_bearish = curr['close'] < curr['open']
        curr_inside = (curr['high'] < prev['high'] and curr['low'] > prev['low'])
        
        return prev_bullish and curr_bearish and curr_inside
        
    def detect_tweezers_top(self, df: pd.DataFrame) -> bool:
        """Detect Tweezers Top pattern"""
        if len(df) < 2:
            return False
            
        first = df.iloc[-2]
        second = df.iloc[-1]
        
        tolerance = 0.0001  # 1 pip tolerance
        same_high = abs(first['high'] - second['high']) <= tolerance
        
        return same_high
        
    def scan_bullish_patterns(self, df: pd.DataFrame) -> List[str]:
        """Scan for all bullish patterns"""
        patterns = []
        
        if self.detect_bullish_engulfing(df):
            patterns.append("BULLISH_ENGULFING")
        if self.detect_hammer(df):
            patterns.append("HAMMER")
        if self.detect_inverted_hammer(df):
            patterns.append("INVERTED_HAMMER")
        if self.detect_morning_star(df):
            patterns.append("MORNING_STAR")
        if self.detect_three_white_soldiers(df):
            patterns.append("THREE_WHITE_SOLDIERS")
        if self.detect_piercing_line(df):
            patterns.append("PIERCING_LINE")
        if self.detect_bullish_harami(df):
            patterns.append("BULLISH_HARAMI")
        if self.detect_tweezers_bottom(df):
            patterns.append("TWEEZERS_BOTTOM")
            
        return patterns
        
    def scan_bearish_patterns(self, df: pd.DataFrame) -> List[str]:
        """Scan for all bearish patterns"""
        patterns = []
        
        if self.detect_bearish_engulfing(df):
            patterns.append("BEARISH_ENGULFING")
        if self.detect_shooting_star(df):
            patterns.append("SHOOTING_STAR")
        if self.detect_hanging_man(df):
            patterns.append("HANGING_MAN")
        if self.detect_evening_star(df):
            patterns.append("EVENING_STAR")
        if self.detect_three_black_crows(df):
            patterns.append("THREE_BLACK_CROWS")
        if self.detect_dark_cloud_cover(df):
            patterns.append("DARK_CLOUD_COVER")
        if self.detect_bearish_harami(df):
            patterns.append("BEARISH_HARAMI")
        if self.detect_tweezers_top(df):
            patterns.append("TWEEZERS_TOP")
            
        return patterns
        
    def calculate_pattern_strength(self, symbol: str, patterns: List[str], df: pd.DataFrame) -> int:
        """Calculate pattern strength using weighted pattern scores + confluence"""
        # Use pattern weights (stronger patterns = higher score)
        strength = sum(PATTERN_WEIGHTS.get(p, 1) for p in patterns)
        
        # Volume confirmation
        if len(df) > 0:
            current_volume = df.iloc[-1]['tick_volume']
            avg_volume = df['tick_volume'].mean()
            if current_volume > avg_volume * 1.5:
                strength += 2
            elif current_volume > avg_volume * 1.2:
                strength += 1
                
        # Trend alignment
        trend_direction = self.symbol_data[symbol]['trend_direction']
        if trend_direction in ("BULLISH", "BEARISH"):
            strength += 2
        elif trend_direction == "NEUTRAL":
            strength += 1
                
        return strength
        
    def should_buy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Tuple[bool, List[str], int]:
        """Determine if we should buy with enhanced confluence"""
        # Check if near support
        if not self.is_near_support(symbol, current_price):
            return False, [], 0
            
        # Scan for bullish patterns
        bullish_patterns = self.scan_bullish_patterns(df)
        if not bullish_patterns:
            return False, [], 0
            
        # Calculate pattern strength
        strength = self.calculate_pattern_strength(symbol, bullish_patterns, df)
        
        # Enhanced confluence check
        confluence_score = self.calculate_buy_confluence(symbol, df, current_price, bullish_patterns)
        
        # Combined strength (pattern + confluence)
        total_strength = strength + confluence_score
        
        # Check if total strength meets minimum requirement
        if total_strength >= self.min_pattern_strength:
            return True, bullish_patterns, total_strength
            
        return False, [], 0
        
    def should_sell(self, symbol: str, df: pd.DataFrame, current_price: float) -> Tuple[bool, List[str], int]:
        """Determine if we should sell with enhanced confluence"""
        # Check if near resistance
        if not self.is_near_resistance(symbol, current_price):
            return False, [], 0
            
        # Scan for bearish patterns
        bearish_patterns = self.scan_bearish_patterns(df)
        if not bearish_patterns:
            return False, [], 0
            
        # Calculate pattern strength
        strength = self.calculate_pattern_strength(symbol, bearish_patterns, df)
        
        # Enhanced confluence check
        confluence_score = self.calculate_sell_confluence(symbol, df, current_price, bearish_patterns)
        
        # Combined strength (pattern + confluence)
        total_strength = strength + confluence_score
        
        # Check if total strength meets minimum requirement
        if total_strength >= self.min_pattern_strength:
            return True, bearish_patterns, total_strength
            
        return False, [], 0
        
    def place_buy_order(self, symbol: str, current_price: float, patterns: List[str], strength: int, entry_candle: pd.Series):
        """Place a buy order with dynamic SL/TP"""
        stop_loss, take_profit = self.calculate_dynamic_sl_tp(symbol, current_price, entry_candle, True)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": current_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": f"SmartBot_Buy_{patterns[0]}_Str{strength}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"BUY order placed: {patterns}, Strength: {strength}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            return True
        else:
            self.logger.error(f"BUY order failed: {result.comment}")
            return False
            
    def place_sell_order(self, symbol: str, current_price: float, patterns: List[str], strength: int, entry_candle: pd.Series):
        """Place a sell order with dynamic SL/TP"""
        stop_loss, take_profit = self.calculate_dynamic_sl_tp(symbol, current_price, entry_candle, False)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": current_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": f"SmartBot_Sell_{patterns[0]}_Str{strength}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"SELL order placed: {patterns}, Strength: {strength}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            return True
        else:
            self.logger.error(f"SELL order failed: {result.comment}")
            return False
            
    def get_open_positions_count(self, symbol: str = None) -> int:
        """Get number of open positions for a specific symbol or all symbols"""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        return len(positions) if positions else 0
    
    def update_trailing_stops(self):
        """Update trailing stops for open positions in profit"""
        if not self.enable_trailing_stop:
            return
        positions = mt5.positions_get()
        if not positions:
            return
        for pos in positions:
            if pos.magic != 234000:
                continue
            symbol = pos.symbol
            pip = self.get_pip_value(symbol)
            trail_dist = self.pips_to_price(symbol, self.trailing_distance_pips)
            if pos.type == mt5.ORDER_TYPE_BUY:
                profit_pips = (mt5.symbol_info_tick(symbol).ask - pos.price_open) / pip
                if profit_pips >= self.trailing_activation_pips:
                    new_sl = mt5.symbol_info_tick(symbol).ask - trail_dist
                    if new_sl > pos.sl and new_sl < mt5.symbol_info_tick(symbol).ask:
                        self._modify_position_sl(pos, new_sl)
            else:  # SELL
                profit_pips = (pos.price_open - mt5.symbol_info_tick(symbol).bid) / pip
                if profit_pips >= self.trailing_activation_pips:
                    new_sl = mt5.symbol_info_tick(symbol).bid + trail_dist
                    if (pos.sl == 0 or new_sl < pos.sl) and new_sl > mt5.symbol_info_tick(symbol).bid:
                        self._modify_position_sl(pos, new_sl)
    
    def _modify_position_sl(self, position, new_sl: float):
        """Modify position stop loss"""
        symbol_info = mt5.symbol_info(position.symbol)
        digits = symbol_info.digits if symbol_info else 5
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position.ticket,
            "sl": round(new_sl, digits),
            "tp": position.tp,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"Trailing stop updated: {position.symbol} SL={new_sl:.5f}")
        
    def run(self):
        """Main trading loop for multiple symbols"""
        self.logger.info(f"Starting Enhanced Smart Trading Bot for symbols: {', '.join(self.symbols)}")
        self.logger.info(f"Features: Multi-TF({self.higher_tf}), ATR zones, Pattern weights, Trailing stop: {self.enable_trailing_stop}")
        
        while True:
            try:
                # Update trailing stops first
                self.update_trailing_stops()
                
                # Session filter - skip analysis during low liquidity
                if not self.is_session_active():
                    self.logger.debug("Outside trading session - waiting")
                    time.sleep(60)
                    continue
                
                total_open_positions = self.get_open_positions_count()
                
                for symbol in self.symbols:
                    try:
                        # Check if we can take more trades
                        if total_open_positions >= self.max_open_trades:
                            self.logger.info(f"Maximum open trades reached: {total_open_positions}")
                            break
                        
                        # Trade cooldown - avoid overtrading same symbol
                        if self.is_on_cooldown(symbol):
                            continue
                            
                        # Get current market data for this symbol
                        df = self.get_ohlc_data(symbol, self.timeframe, self.sr_lookback)
                        if df.empty:
                            self.logger.warning(f"Failed to get market data for {symbol}")
                            continue
                            
                        # Update trend direction for this symbol
                        self.symbol_data[symbol]['trend_direction'] = self.detect_trend_direction(df)
                        
                        # Update support/resistance levels with role reversal for this symbol
                        support_levels, resistance_levels = self.detect_support_resistance_with_role_reversal(symbol, df)
                        self.symbol_data[symbol]['support_levels'] = support_levels
                        self.symbol_data[symbol]['resistance_levels'] = resistance_levels
                        
                        # Get current price and entry candle
                        current_price = df.iloc[-1]['close']
                        entry_candle = df.iloc[-1]
                        
                        # Prune old broken levels to keep analysis relevant
                        self.prune_broken_levels(symbol, current_price)
                        
                        # Check for buy signal
                        should_buy, buy_patterns, buy_strength = self.should_buy(symbol, df, current_price)
                        if should_buy:
                            if self.place_buy_order(symbol, current_price, buy_patterns, buy_strength, entry_candle):
                                total_open_positions += 1
                                self.last_trade_time[symbol] = time.time()
                                self.logger.info(f"BUY signal for {symbol}: {buy_patterns}, Strength: {buy_strength}")
                                
                        # Check for sell signal
                        should_sell, sell_patterns, sell_strength = self.should_sell(symbol, df, current_price)
                        if should_sell:
                            if self.place_sell_order(symbol, current_price, sell_patterns, sell_strength, entry_candle):
                                total_open_positions += 1
                                self.last_trade_time[symbol] = time.time()
                                self.logger.info(f"SELL signal for {symbol}: {sell_patterns}, Strength: {sell_strength}")
                                
                        # Log current status for this symbol
                        symbol_info = self.symbol_data[symbol]
                        self.logger.info(f"{symbol}: Price: {current_price:.5f}, Trend: {symbol_info['trend_direction']}, Support: {len(symbol_info['support_levels'])}, Resistance: {len(symbol_info['resistance_levels'])}, Broken S: {len(symbol_info['broken_support_levels'])}, Broken R: {len(symbol_info['broken_resistance_levels'])}")
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {symbol}: {e}")
                        continue
                        
                # Wait before next analysis cycle
                time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(10)
                
    def __del__(self):
        """Cleanup on exit"""
        mt5.shutdown()

if __name__ == "__main__":
    bot = SmartTradingBot()
    bot.run()
