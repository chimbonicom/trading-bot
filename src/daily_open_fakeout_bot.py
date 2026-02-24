import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import os
from dotenv import load_dotenv

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'daily_open_bot_config.env')
load_dotenv(config_path)

class DailyOpenFakeoutBot:
    def __init__(self):
        # Load and validate configuration
        self.config = self.load_configuration()
        
        # Bot state for each symbol
        self.symbol_data = {}
        for symbol in self.symbols:
            self.symbol_data[symbol] = {
                'daily_open': None,
                'current_bias': "NEUTRAL",  # BULLISH, BEARISH, NEUTRAL
                'last_candle_time': None,
                'waiting_for_entry': True,
                'last_log_time': 0,
                'consecutive_logs': 0,
                'last_trade_time': None
            }
        
        # Performance tracking
        self.performance = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'current_streak': 0,
            'last_trade_time': None
        }
        
        # Daily trade tracking
        self.daily_trades = {
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'trades_today': 0,
            'last_reset_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Track logged trades to prevent duplicates
        self.logged_trades = set()
        
        # Setup logging
        self.setup_logging()
        
        # Initialize MT5 connection
        self.connect_mt5()
        
    def load_configuration(self) -> Dict:
        """Load and validate configuration"""
        config = {}
        
        # MT5 Configuration
        config['mt5_login'] = int(os.getenv('MT5_LOGIN'))
        config['mt5_password'] = os.getenv('MT5_PASSWORD')
        config['mt5_server'] = os.getenv('MT5_SERVER')
        
        # Trading Configuration
        symbols_str = os.getenv('SYMBOLS', 'GBPJPY.s')
        self.symbols = [s.strip() for s in symbols_str.split(',')]
        
        lot_sizes_str = os.getenv('LOT_SIZES', '0.5')
        lot_sizes = [float(s.strip()) for s in lot_sizes_str.split(',')]
        
        # Create symbol-lot mapping
        self.symbol_lots = {}
        for i, symbol in enumerate(self.symbols):
            if i < len(lot_sizes):
                self.symbol_lots[symbol] = lot_sizes[i]
            else:
                self.symbol_lots[symbol] = 0.5  # Default lot size
        
        config['timeframe'] = os.getenv('TIMEFRAME', 'M5')
        config['max_open_trades'] = int(os.getenv('MAX_OPEN_TRADES', '1'))
        config['max_daily_trades'] = int(os.getenv('MAX_DAILY_TRADES', '5'))
        config['risk_reward_ratio'] = float(os.getenv('RISK_REWARD_RATIO', '3.0'))
        
        # Convert pips to price values
        sweep_tolerance_pips = float(os.getenv('SWEEP_TOLERANCE_PIPS', '1'))
        config['sweep_tolerance'] = sweep_tolerance_pips * 0.0001  # Convert pips to price
        
        bias_confirmation_pips = float(os.getenv('BIAS_CONFIRMATION_PIPS', '10'))
        config['bias_confirmation_pips'] = bias_confirmation_pips * 0.0001
        
        # Bot Performance Settings
        config['main_loop_sleep'] = int(os.getenv('MAIN_LOOP_SLEEP', '5'))
        config['status_log_interval'] = int(os.getenv('STATUS_LOG_INTERVAL', '300'))
        
        # Bot Behavior
        config['auto_reports'] = os.getenv('AUTO_REPORTS', 'true').lower() == 'true'
        config['report_interval'] = int(os.getenv('REPORT_INTERVAL', '3600'))
        config['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
        
        # Daily Open Override
        daily_open_override = os.getenv('DAILY_OPEN_OVERRIDE', '0')
        if daily_open_override != '0':
            config['daily_open_override'] = float(daily_open_override)
        else:
            config['daily_open_override'] = None
        
        # Advanced Settings
        config['magic_number'] = int(os.getenv('MAGIC_NUMBER', '234002'))
        config['order_deviation'] = int(os.getenv('ORDER_DEVIATION', '20'))
        config['min_trade_interval'] = int(os.getenv('MIN_TRADE_INTERVAL', '60'))
        config['enable_smart_logging'] = os.getenv('ENABLE_SMART_LOGGING', 'true').lower() == 'true'
        config['enable_performance_tracking'] = os.getenv('ENABLE_PERFORMANCE_TRACKING', 'true').lower() == 'true'
        
        # Performance tracking
        self.last_report_time = time.time()
        
        return config
        
    def validate_configuration(self):
        """Validate configuration and print summary"""
        print("🔧 Configuration Summary:")
        print("=" * 50)
        print(f"📊 Symbols: {', '.join(self.symbols)}")
        print(f"💰 Lot Sizes: {', '.join([f'{symbol}: {lot}' for symbol, lot in self.symbol_lots.items()])}")
        print(f"⏰ Timeframe: {self.config['timeframe']}")
        print(f"🎯 Max Open Trades: {self.config['max_open_trades']}")
        print(f"📅 Max Daily Trades: {self.config['max_daily_trades']}")
        print(f"📈 Risk:Reward Ratio: 1:{self.config['risk_reward_ratio']}")
        print(f"🔄 Sweep Tolerance: {self.config['sweep_tolerance']:.5f} ({self.config['sweep_tolerance']/0.0001:.0f} pips)")
        print(f"📊 Bias Confirmation: {self.config['bias_confirmation_pips']:.5f} ({self.config['bias_confirmation_pips']/0.0001:.0f} pips)")
        print(f"📄 Auto Reports: {'Enabled' if self.config['auto_reports'] else 'Disabled'}")
        print(f"⏱️ Report Interval: {self.config['report_interval']} seconds")
        print(f"🔄 Main Loop Sleep: {self.config['main_loop_sleep']} seconds")
        print(f"📝 Status Log Interval: {self.config['status_log_interval']} seconds")
        print(f"🔢 Magic Number: {self.config['magic_number']}")
        print("=" * 50)
        
    def setup_logging(self):
        """Setup clean, professional logging"""
        logs_path = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(logs_path, exist_ok=True)
        
        # Force simple logging for Windows to avoid encoding issues
        use_simple_logging = False
        try:
            import sys
            if sys.platform == 'win32':
                use_simple_logging = True
        except:
            use_simple_logging = True
        
        # Create custom formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(logs_path, 'daily_open_bot.log'), encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config['log_level']))
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Store simple logging preference
        self.use_simple_logging = use_simple_logging
        
    def format_message(self, message):
        """Format message with or without emojis based on system compatibility"""
        if self.use_simple_logging:
            # Replace emojis with text equivalents
            replacements = {
                '✅': '[OK]',
                '❌': '[ERROR]',
                '🚀': '[START]',
                '📊': '[DATA]',
                '📅': '[DATE]',
                '🔄': '[CHANGE]',
                '⏳': '[WAIT]',
                '💰': '[MONEY]',
                '🎯': '[TARGET]',
                '📈': '[CHART]',
                '🔻': '[SELL]',
                '📄': '[REPORT]',
                '⏱️': '[TIME]',
                '🔢': '[NUMBER]'
            }
            for emoji, text in replacements.items():
                message = message.replace(emoji, text)
        return message
        
    def connect_mt5(self):
        """Connect to MT5 terminal"""
        if not mt5.initialize():
            self.logger.error(self.format_message("❌ MT5 initialization failed!"))
            return False
            
        # Login to account
        if not mt5.login(login=self.config['mt5_login'], 
                        password=self.config['mt5_password'], 
                        server=self.config['mt5_server']):
            self.logger.error(self.format_message("❌ MT5 login failed!"))
            return False
            
        self.logger.info(self.format_message(f"✅ Connected to MT5: {self.config['mt5_server']}"))
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
        
    def get_daily_open(self, symbol: str) -> float:
        """Get the current day's open price with multiple validation methods"""
        try:
            # Check for manual override first
            override_value = self.config.get('daily_open_override', 0)
            if override_value != 0:
                self.logger.info(f"[OVERRIDE] Using manual daily open: {override_value:.5f}")
                return override_value
            
            # Method 1: Get daily timeframe data (most reliable)
            rates_daily = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
            if rates_daily is not None and len(rates_daily) > 0:
                daily_open_d1 = rates_daily[0]['open']
                self.logger.info(f"[DEBUG] D1 Daily Open: {daily_open_d1:.5f}")
            else:
                daily_open_d1 = None
                self.logger.warning("[WARNING] Could not get D1 daily open")
            
            # Method 2: Get today's data starting from 00:00 UTC
            today_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            rates_utc = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, today_utc, 1440)
            if rates_utc is not None and len(rates_utc) > 0:
                df_utc = pd.DataFrame(rates_utc)
                df_utc['time'] = pd.to_datetime(df_utc['time'], unit='s')
                daily_open_utc = df_utc.iloc[0]['open']
                self.logger.info(f"[DEBUG] UTC Daily Open: {daily_open_utc:.5f}")
            else:
                daily_open_utc = None
                self.logger.warning("[WARNING] Could not get UTC daily open")
            
            # Method 3: Get today's data starting from 00:00 local time
            today_local = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            rates_local = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, today_local, 1440)
            if rates_local is not None and len(rates_local) > 0:
                df_local = pd.DataFrame(rates_local)
                df_local['time'] = pd.to_datetime(df_local['time'], unit='s')
                daily_open_local = df_local.iloc[0]['open']
                self.logger.info(f"[DEBUG] Local Daily Open: {daily_open_local:.5f}")
            else:
                daily_open_local = None
                self.logger.warning("[WARNING] Could not get Local daily open")
            
            # Method 4: Get the first M5 candle of the day (since we're using M5 timeframe)
            rates_m5 = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, today_utc, 288)  # 24 hours in M5
            if rates_m5 is not None and len(rates_m5) > 0:
                df_m5 = pd.DataFrame(rates_m5)
                df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
                daily_open_m5 = df_m5.iloc[0]['open']
                self.logger.info(f"[DEBUG] M5 Daily Open: {daily_open_m5:.5f}")
            else:
                daily_open_m5 = None
                self.logger.warning("[WARNING] Could not get M5 daily open")
            
            # Method 5: Fallback - get current price as daily open (emergency)
            current_price = mt5.symbol_info_tick(symbol)
            if current_price is not None:
                daily_open_fallback = current_price.bid
                self.logger.warning(f"[FALLBACK] Using current price as daily open: {daily_open_fallback:.5f}")
            else:
                daily_open_fallback = None
                self.logger.error("[ERROR] Cannot get current price for fallback")
            
            # Choose the most appropriate daily open
            # Priority: D1 > M5 > UTC > Local > Fallback
            if daily_open_d1 is not None:
                daily_open = daily_open_d1
                method = "D1"
            elif daily_open_m5 is not None:
                daily_open = daily_open_m5
                method = "M5"
            elif daily_open_utc is not None:
                daily_open = daily_open_utc
                method = "UTC"
            elif daily_open_local is not None:
                daily_open = daily_open_local
                method = "Local"
            elif daily_open_fallback is not None:
                daily_open = daily_open_fallback
                method = "Fallback"
            else:
                self.logger.error("[ERROR] Could not get daily open data from any method")
                return None
            
            # Log all available daily opens for comparison
            self.logger.info(f"[DEBUG] Available Daily Opens:")
            if daily_open_d1 is not None: 
                self.logger.info(f"  D1: {daily_open_d1:.5f}")
            if daily_open_m5 is not None: 
                self.logger.info(f"  M5: {daily_open_m5:.5f}")
            if daily_open_utc is not None: 
                self.logger.info(f"  UTC: {daily_open_utc:.5f}")
            if daily_open_local is not None: 
                self.logger.info(f"  Local: {daily_open_local:.5f}")
            if daily_open_fallback is not None: 
                self.logger.info(f"  Fallback: {daily_open_fallback:.5f}")
            
            self.logger.info(f"[DEBUG] Selected Daily Open: {daily_open:.5f} (Method: {method})")
            
            return daily_open
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error getting daily open: {e}")
            # Try fallback method
            try:
                current_price = mt5.symbol_info_tick(symbol)
                if current_price is not None:
                    fallback_open = current_price.bid
                    self.logger.warning(f"[EMERGENCY FALLBACK] Using current price: {fallback_open:.5f}")
                    return fallback_open
            except:
                pass
            return None
        
    def determine_bias(self, symbol: str, current_price: float) -> str:
        """Determine current bias based on price vs daily open"""
        daily_open = self.symbol_data[symbol]['daily_open']
        if daily_open is None:
            return "NEUTRAL"
            
        price_diff = current_price - daily_open
        bias_threshold = self.config['bias_confirmation_pips']
        
        self.logger.info(f"[DEBUG] Bias calculation:")
        self.logger.info(f"  Current price: {current_price:.5f}")
        self.logger.info(f"  Daily open: {daily_open:.5f}")
        self.logger.info(f"  Price difference: {price_diff:.5f}")
        self.logger.info(f"  Bias threshold: {bias_threshold:.5f}")
        
        if price_diff > bias_threshold:
            bias = "BULLISH"
        elif price_diff < -bias_threshold:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
            
        self.logger.info(f"  Determined bias: {bias}")
        return bias
            
    def detect_bullish_fakeout(self, df: pd.DataFrame) -> Tuple[bool, float, float]:
        """Detect bullish fakeout pattern with detailed logging"""
        if len(df) < 3:
            return False, 0.0, 0.0
            
        # Get last 3 candles
        candle1 = df.iloc[-3]  # First bullish candle
        candle2 = df.iloc[-2]  # Bearish candle that sweeps below
        candle3 = df.iloc[-1]  # Current bullish candle (reversal)
        
        # Debug logging
        self.logger.info(f"[DEBUG] Checking BULLISH fakeout pattern:")
        self.logger.info(f"  Candle 1: {candle1.name} O={candle1['open']:.5f} C={candle1['close']:.5f} H={candle1['high']:.5f}")
        self.logger.info(f"  Candle 2: {candle2.name} O={candle2['open']:.5f} C={candle2['close']:.5f} H={candle2['high']:.5f}")
        self.logger.info(f"  Candle 3: {candle3.name} O={candle3['open']:.5f} C={candle3['close']:.5f} H={candle3['high']:.5f}")
        
        # Check if candle 1 was bullish
        is_candle1_bullish = candle1['close'] > candle1['open']
        self.logger.info(f"  Candle 1 bullish: {is_candle1_bullish}")
        
        # Check if candle 2 was bearish
        is_candle2_bearish = candle2['close'] < candle2['open']
        self.logger.info(f"  Candle 2 bearish: {is_candle2_bearish}")
        
        # Check if candle 3 is bullish
        is_candle3_bullish = candle3['close'] > candle3['open']
        self.logger.info(f"  Candle 3 bullish: {is_candle3_bullish}")
        
        # Check if candle 2's low sweeps below candle 1's low
        sweep_detected = candle2['low'] < candle1['low']
        sweep_distance = candle1['low'] - candle2['low']
        self.logger.info(f"  Sweep detected: {sweep_detected} (distance: {sweep_distance:.5f})")
        
        if is_candle1_bullish and is_candle2_bearish and is_candle3_bullish and sweep_detected:
            self.logger.info(f"[DEBUG] ✅ BULLISH fakeout pattern CONFIRMED!")
            self.logger.info(f"  Entry price: {candle3['close']:.5f}")
            self.logger.info(f"  Sweep level: {candle2['low']:.5f}")
            return True, candle3['close'], candle2['low']
        else:
            self.logger.info(f"[DEBUG] ❌ BULLISH fakeout pattern NOT met")
            if not is_candle1_bullish:
                self.logger.info(f"  Reason: Candle 1 not bullish")
            if not is_candle2_bearish:
                self.logger.info(f"  Reason: Candle 2 not bearish")
            if not is_candle3_bullish:
                self.logger.info(f"  Reason: Candle 3 not bullish")
            if not sweep_detected:
                self.logger.info(f"  Reason: No sweep detected")
            return False, 0.0, 0.0
        
    def detect_bearish_fakeout(self, df: pd.DataFrame) -> Tuple[bool, float, float]:
        """Detect bearish fakeout pattern with detailed logging"""
        if len(df) < 3:
            return False, 0.0, 0.0
            
        # Get last 3 candles
        candle1 = df.iloc[-3]  # First bearish candle
        candle2 = df.iloc[-2]  # Bullish candle that sweeps above
        candle3 = df.iloc[-1]  # Current bearish candle (reversal)
        
        # Debug logging
        self.logger.info(f"[DEBUG] Checking for BEARISH fakeout (bias: {self.symbol_data[df.name]['current_bias']})")
        self.logger.info(f"  Candle 1: {candle1.name} O={candle1['open']:.5f} C={candle1['close']:.5f} L={candle1['low']:.5f}")
        self.logger.info(f"  Candle 2: {candle2.name} O={candle2['open']:.5f} C={candle2['close']:.5f} L={candle2['low']:.5f}")
        self.logger.info(f"  Candle 3: {candle3.name} O={candle3['open']:.5f} C={candle3['close']:.5f} L={candle3['low']:.5f}")
        
        # Check if candle 1 was bearish
        is_candle1_bearish = candle1['close'] < candle1['open']
        self.logger.info(f"  Candle 1 bearish: {is_candle1_bearish}")
        
        # Check if candle 2 was bullish
        is_candle2_bullish = candle2['close'] > candle2['open']
        self.logger.info(f"  Candle 2 bullish: {is_candle2_bullish}")
        
        # Check if candle 3 is bearish
        is_candle3_bearish = candle3['close'] < candle3['open']
        self.logger.info(f"  Candle 3 bearish: {is_candle3_bearish}")
        
        # Check if candle 2's high sweeps above candle 1's high
        sweep_detected = candle2['high'] > candle1['high']
        sweep_distance = candle2['high'] - candle1['high']
        self.logger.info(f"  Sweep detected: {sweep_detected} (distance: {sweep_distance:.5f})")
        
        if is_candle1_bearish and is_candle2_bullish and is_candle3_bearish and sweep_detected:
            self.logger.info(f"[DEBUG] ✅ BEARISH fakeout pattern CONFIRMED!")
            self.logger.info(f"  Entry price: {candle3['close']:.5f}")
            self.logger.info(f"  Sweep level: {candle2['high']:.5f}")
            return True, candle3['close'], candle2['high']
        else:
            self.logger.info(f"[DEBUG] ❌ BEARISH fakeout pattern NOT met")
            if not is_candle1_bearish:
                self.logger.info(f"  Reason: Candle 1 not bearish")
            if not is_candle2_bullish:
                self.logger.info(f"  Reason: Candle 2 not bullish")
            if not is_candle3_bearish:
                self.logger.info(f"  Reason: Candle 3 not bearish")
            if not sweep_detected:
                self.logger.info(f"  Reason: No sweep detected")
            return False, 0.0, 0.0
        
    def calculate_sl_tp(self, entry_price: float, sweep_level: float, is_buy: bool) -> Tuple[float, float]:
        """Calculate SL and TP based on sweep level with better risk management"""
        # Add minimum distance for breathing room (5 pips minimum)
        min_distance_pips = 5
        min_distance = min_distance_pips * 0.0001  # Convert pips to price
        
        if is_buy:
            # For buy orders
            # SL should be below the sweep level with some breathing room
            sl_distance = max(entry_price - sweep_level + self.config['sweep_tolerance'], min_distance)
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * self.config['risk_reward_ratio'])
        else:
            # For sell orders
            # SL should be above the sweep level with some breathing room
            sl_distance = max(sweep_level - entry_price + self.config['sweep_tolerance'], min_distance)
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * self.config['risk_reward_ratio'])
            
        self.logger.info(f"[DEBUG] SL/TP Calculation:")
        self.logger.info(f"  Entry: {entry_price:.5f}")
        self.logger.info(f"  Sweep Level: {sweep_level:.5f}")
        self.logger.info(f"  SL Distance: {sl_distance:.5f} ({sl_distance/0.0001:.1f} pips)")
        self.logger.info(f"  Stop Loss: {stop_loss:.5f}")
        self.logger.info(f"  Take Profit: {take_profit:.5f}")
        self.logger.info(f"  Risk:Reward: 1:{self.config['risk_reward_ratio']}")
            
        return stop_loss, take_profit
        
    def validate_sl_tp(self, entry_price: float, stop_loss: float, take_profit: float, is_buy: bool) -> bool:
        """Validate that SL and TP have enough room and are valid"""
        # Get current market info
        symbol_info = mt5.symbol_info(self.symbols[0])  # Use first symbol for now
        if not symbol_info:
            self.logger.error("❌ Cannot get symbol info for validation")
            return False
            
        # Check minimum distance requirements
        min_distance_pips = 5
        min_distance = min_distance_pips * 0.0001
        
        if is_buy:
            sl_distance = entry_price - stop_loss
            tp_distance = take_profit - entry_price
        else:
            sl_distance = stop_loss - entry_price
            tp_distance = entry_price - take_profit
            
        # Validate distances
        if sl_distance < min_distance:
            self.logger.warning(f"⚠️ Stop Loss too close: {sl_distance/0.0001:.1f} pips (min: {min_distance_pips})")
            return False
            
        if tp_distance < (sl_distance * self.config['risk_reward_ratio'] * 0.8):  # Allow 20% tolerance
            self.logger.warning(f"⚠️ Take Profit too close: {tp_distance/0.0001:.1f} pips")
            return False
            
        # Check against symbol limits
        if sl_distance < symbol_info.trade_stops_level * symbol_info.point:
            self.logger.warning(f"⚠️ Stop Loss below broker minimum: {sl_distance/0.0001:.1f} pips")
            return False
            
        self.logger.info(f"✅ SL/TP validation passed:")
        self.logger.info(f"  SL Distance: {sl_distance/0.0001:.1f} pips")
        self.logger.info(f"  TP Distance: {tp_distance/0.0001:.1f} pips")
        self.logger.info(f"  Risk:Reward: 1:{tp_distance/sl_distance:.1f}")
        
        return True
        
    def can_trade(self, symbol: str) -> bool:
        """Check if enough time has passed since last trade"""
        if not self.config['enable_performance_tracking']:
            return True
            
        last_trade_time = self.symbol_data[symbol]['last_trade_time']
        if last_trade_time is None:
            return True
            
        time_since_last_trade = (datetime.now() - last_trade_time).total_seconds()
        return time_since_last_trade >= self.config['min_trade_interval']
        
    def place_buy_order(self, symbol: str, entry_price: float, sweep_level: float):
        """Place a buy order"""
        if not self.can_trade(symbol):
            return False
            
        stop_loss, take_profit = self.calculate_sl_tp(entry_price, sweep_level, True)
        
        # Validate SL/TP before placing order
        if not self.validate_sl_tp(entry_price, stop_loss, take_profit, True):
            self.logger.error("❌ SL/TP validation failed - skipping order")
            return False
            
        lot_size = self.symbol_lots[symbol]
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": self.config['order_deviation'],
            "magic": self.config['magic_number'],
            "comment": f"DailyOpen_BullishFakeout",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(self.format_message(f"🚀 BULLISH ENTRY: {symbol} at {entry_price:.5f} | SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Lot: {lot_size}"))
            self.performance['total_trades'] += 1
            self.performance['last_trade_time'] = datetime.now()
            self.symbol_data[symbol]['last_trade_time'] = datetime.now()
            return True
        else:
            self.logger.error(self.format_message(f"❌ BUY order failed: {result.comment}"))
            return False
            
    def place_sell_order(self, symbol: str, entry_price: float, sweep_level: float):
        """Place a sell order"""
        if not self.can_trade(symbol):
            return False
            
        stop_loss, take_profit = self.calculate_sl_tp(entry_price, sweep_level, False)
        
        # Validate SL/TP before placing order
        if not self.validate_sl_tp(entry_price, stop_loss, take_profit, False):
            self.logger.error("❌ SL/TP validation failed - skipping order")
            return False
            
        lot_size = self.symbol_lots[symbol]
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": self.config['order_deviation'],
            "magic": self.config['magic_number'],
            "comment": f"DailyOpen_BearishFakeout",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(self.format_message(f"🔻 BEARISH ENTRY: {symbol} at {entry_price:.5f} | SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Lot: {lot_size}"))
            self.performance['total_trades'] += 1
            self.performance['last_trade_time'] = datetime.now()
            self.symbol_data[symbol]['last_trade_time'] = datetime.now()
            return True
        else:
            self.logger.error(self.format_message(f"❌ SELL order failed: {result.comment}"))
            return False
            
    def get_open_positions_count(self, symbol: str = None) -> int:
        """Get number of open positions for this bot"""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions:
            # Count only positions with this bot's magic number
            bot_positions = [pos for pos in positions if pos.magic == self.config['magic_number']]
            return len(bot_positions)
        return 0
        
    def check_for_closed_trades(self):
        """Check for recently closed trades and update performance"""
        if not self.config['enable_performance_tracking']:
            return
            
        # Get closed trades from last 24 hours
        from_date = datetime.now() - timedelta(hours=24)
        deals = mt5.history_deals_get(from_date, datetime.now())
        
        if deals:
            for deal in deals:
                if deal.magic == self.config['magic_number']:  # Our bot's trades
                    # Create unique trade identifier to prevent duplicate logging
                    trade_id = f"{deal.ticket}_{deal.time}"
                    
                    # Check if this is a new closed trade that hasn't been logged yet
                    if (hasattr(deal, 'profit') and deal.profit != 0 and 
                        trade_id not in self.logged_trades):
                        
                        # Add to logged trades set to prevent duplicate logging
                        self.logged_trades.add(trade_id)
                        
                        if deal.profit > 0:
                            self.performance['winning_trades'] += 1
                            self.logger.info(self.format_message(f"✅ TRADE CLOSED: +${deal.profit:.2f} (TP Hit)"))
                        else:
                            self.performance['losing_trades'] += 1
                            self.logger.info(self.format_message(f"❌ TRADE CLOSED: ${deal.profit:.2f} (SL Hit)"))
                            
                        # Update best/worst trade
                        if deal.profit > self.performance['best_trade']:
                            self.performance['best_trade'] = deal.profit
                        if deal.profit < self.performance['worst_trade']:
                            self.performance['worst_trade'] = deal.profit
                            
    def check_daily_trade_limit(self) -> bool:
        """Check if we can take more trades today"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Reset daily counter if it's a new day
        if current_date != self.daily_trades['current_date']:
            self.daily_trades['current_date'] = current_date
            self.daily_trades['trades_today'] = 0
            self.daily_trades['last_reset_date'] = current_date
            self.logger.info(f"[INFO] New trading day started: {current_date}")
        
        # Check if we've reached the daily limit
        if self.config['max_daily_trades'] > 0 and self.daily_trades['trades_today'] >= self.config['max_daily_trades']:
            return False
        
        return True
    
    def increment_daily_trades(self):
        """Increment the daily trade counter"""
        self.daily_trades['trades_today'] += 1
        self.logger.info(f"[INFO] Trade #{self.daily_trades['trades_today']} of {self.config['max_daily_trades']} today")
    
    def log_status_check(self):
        """Log a status check message instead of misleading TP HIT"""
        try:
            # Get current price for status
            symbol = self.symbols[0]  # Use first symbol for status
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                current_price = tick.bid
                bias = self.symbol_data[symbol]['current_bias']
                daily_trades_info = f" (Trades: {self.daily_trades['trades_today']}/{self.config['max_daily_trades']})"
                self.logger.info(f"[STATUS] MT5 Connected - Price: {current_price:.5f} - Bias: {bias}{daily_trades_info}")
            else:
                # Try alternative method to get price
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info and symbol_info.bid > 0:
                    current_price = symbol_info.bid
                    bias = self.symbol_data[symbol]['current_bias']
                    daily_trades_info = f" (Trades: {self.daily_trades['trades_today']}/{self.config['max_daily_trades']})"
                    self.logger.info(f"[STATUS] MT5 Connected - Price: {current_price:.5f} - Bias: {bias}{daily_trades_info}")
                else:
                    # Check if market is closed
                    current_time = datetime.now()
                    if current_time.weekday() >= 5:  # Weekend
                        self.logger.info("[STATUS] Market closed (Weekend) - Bot will resume on Monday")
                    elif current_time.hour < 5 or current_time.hour >= 23:  # Outside trading hours
                        self.logger.info("[STATUS] Market closed (Outside trading hours) - Bot will resume when market opens")
                    else:
                        self.logger.info("[STATUS] MT5 Connected - Waiting for market data...")
        except Exception as e:
            self.logger.info(f"[STATUS] Bot running - Checking market conditions... (Error: {e})")
                            
    def generate_auto_report(self):
        """Generate automatic performance report"""
        if not self.config['auto_reports']:
            return
            
        current_time = time.time()
        if current_time - self.last_report_time > self.config['report_interval']:
            try:
                # Import here to avoid circular imports
                from src.performance_analyzer import PerformanceAnalyzer
                
                self.logger.info(self.format_message("📊 Generating automatic performance report..."))
                analyzer = PerformanceAnalyzer()
                report_path = analyzer.generate_report(1)  # Last 24 hours
                
                if report_path:
                    self.logger.info(self.format_message(f"📄 Auto-report generated: {os.path.basename(report_path)}"))
                    
                self.last_report_time = current_time
                
            except Exception as e:
                self.logger.error(self.format_message(f"❌ Auto-report generation failed: {e}"))
                
    def smart_log(self, symbol: str, message: str, force_log: bool = False):
        """Smart logging to avoid spam"""
        if not self.config['enable_smart_logging']:
            if force_log:
                self.logger.info(f"{symbol}: {self.format_message(message)}")
            return
            
        current_time = time.time()
        
        # Always log important messages
        if force_log or "ENTRY" in message or "SL" in message or "TP" in message:
            self.logger.info(f"{symbol}: {self.format_message(message)}")
            self.symbol_data[symbol]['last_log_time'] = current_time
            self.symbol_data[symbol]['consecutive_logs'] = 0
        else:
            # Log status updates only every 5 minutes (300 seconds) to match M5 timeframe
            if current_time - self.symbol_data[symbol]['last_log_time'] > self.config['status_log_interval']:
                self.logger.info(f"{symbol}: {self.format_message(message)}")
                self.symbol_data[symbol]['last_log_time'] = current_time
                self.symbol_data[symbol]['consecutive_logs'] = 0
            else:
                self.symbol_data[symbol]['consecutive_logs'] += 1
                
    def run(self):
        """Main trading loop"""
        # Validate and display configuration
        self.validate_configuration()
        
        self.logger.info(self.format_message("🚀 Starting Daily Open Line Fakeout Bot"))
        self.logger.info("=" * 60)
        
        while True:
            try:
                # Check for closed trades and update performance
                self.check_for_closed_trades()
                
                # Generate automatic report if enabled
                self.generate_auto_report()
                
                # Log status check (replaces the misleading TP HIT messages)
                self.log_status_check()
                
                total_open_positions = self.get_open_positions_count()
                
                for symbol in self.symbols:
                    try:
                        # Check if we can take more trades
                        if total_open_positions >= self.config['max_open_trades']:
                            if self.symbol_data[symbol]['waiting_for_entry']:
                                self.smart_log(symbol, "⏳ Waiting for existing trade to close...", force_log=True)
                                self.symbol_data[symbol]['waiting_for_entry'] = False
                            continue
                            
                        # Check daily trade limit
                        if not self.check_daily_trade_limit():
                            if self.symbol_data[symbol]['waiting_for_entry']:
                                self.smart_log(symbol, f"⏳ Daily trade limit reached ({self.config['max_daily_trades']} trades today) - Waiting for tomorrow", force_log=True)
                                self.symbol_data[symbol]['waiting_for_entry'] = False
                            continue
                            
                        # Get current market data
                        df = self.get_ohlc_data(symbol, self.config['timeframe'], 50)
                        if df.empty:
                            continue
                            
                        # Update daily open if needed
                        if self.symbol_data[symbol]['daily_open'] is None:
                            daily_open = self.get_daily_open(symbol)
                            if daily_open:
                                self.symbol_data[symbol]['daily_open'] = daily_open
                                self.logger.info(self.format_message(f"📅 {symbol} Daily Open: {daily_open:.5f}"))
                            else:
                                continue
                                
                        # Get current price and determine bias
                        current_price = df.iloc[-1]['close']
                        current_bias = self.determine_bias(symbol, current_price)
                        
                        # Update bias if changed
                        if current_bias != self.symbol_data[symbol]['current_bias']:
                            old_bias = self.symbol_data[symbol]['current_bias']
                            self.symbol_data[symbol]['current_bias'] = current_bias
                            self.logger.info(f"[DEBUG] Bias changed from {old_bias} to {current_bias}")
                            self.smart_log(symbol, f"🔄 Bias changed to: {current_bias}", force_log=True)
                            
                        # Check for new candle
                        current_candle_time = df.iloc[-1]['time']
                        if current_candle_time != self.symbol_data[symbol]['last_candle_time']:
                            self.symbol_data[symbol]['last_candle_time'] = current_candle_time
                            self.logger.info(f"[DEBUG] New candle detected at {current_candle_time}")
                            
                            # Check for completed candle patterns (not the current forming candle)
                            # We need to check the previous completed candle against the one before it
                            if len(df) >= 4:  # Need at least 4 candles to check pattern
                                # Get the last 3 completed candles for pattern detection
                                candle_1 = df.iloc[-4]  # First candle in pattern
                                candle_2 = df.iloc[-3]  # Second candle in pattern  
                                candle_3 = df.iloc[-2]  # Third candle (completed, for entry)
                                
                                self.logger.info(f"[DEBUG] Checking pattern with completed candles:")
                                self.logger.info(f"  Candle 1: {candle_1['time']} O={candle_1['open']:.5f} C={candle_1['close']:.5f} L={candle_1['low']:.5f}")
                                self.logger.info(f"  Candle 2: {candle_2['time']} O={candle_2['open']:.5f} C={candle_2['close']:.5f} L={candle_2['low']:.5f}")
                                self.logger.info(f"  Candle 3: {candle_3['time']} O={candle_3['open']:.5f} C={candle_3['close']:.5f} L={candle_3['low']:.5f}")
                                
                                # Check for bullish fakeout pattern
                                if current_bias == "BULLISH":
                                    self.logger.info(f"[DEBUG] Checking for BULLISH fakeout (bias: {current_bias})")
                                    
                                    # Pattern: Bearish candle (candle_2) followed by Bullish candle (candle_3) with sweep
                                    is_candle_2_bearish = candle_2['close'] < candle_2['open']
                                    is_candle_3_bullish = candle_3['close'] > candle_3['open']
                                    has_sweep = candle_3['low'] < candle_2['low']
                                    
                                    self.logger.info(f"  Candle 2 bearish: {is_candle_2_bearish}")
                                    self.logger.info(f"  Candle 3 bullish: {is_candle_3_bullish}")
                                    self.logger.info(f"  Sweep detected: {has_sweep}")
                                    
                                    if is_candle_2_bearish and is_candle_3_bullish and has_sweep:
                                        self.logger.info(f"[DEBUG] ✅ BULLISH fakeout pattern CONFIRMED!")
                                        entry_price = candle_3['close']
                                        sweep_level = candle_3['low']
                                        self.logger.info(f"  Entry price: {entry_price:.5f}")
                                        self.logger.info(f"  Sweep level: {sweep_level:.5f}")
                                        
                                        # Check daily trade limit before placing order
                                        if not self.check_daily_trade_limit():
                                            self.logger.info(f"[INFO] Daily trade limit reached ({self.config['max_daily_trades']} trades today) - Skipping trade")
                                            continue
                                            
                                        if self.place_buy_order(symbol, entry_price, sweep_level):
                                            total_open_positions += 1
                                            self.symbol_data[symbol]['waiting_for_entry'] = False
                                            self.increment_daily_trades()  # Increment daily trade counter
                                        else:
                                            self.logger.info(f"[DEBUG] BULLISH order placement failed")
                                    else:
                                        self.logger.info(f"[DEBUG] ❌ BULLISH fakeout pattern NOT met")
                                        
                                # Check for bearish fakeout pattern
                                elif current_bias == "BEARISH":
                                    self.logger.info(f"[DEBUG] Checking for BEARISH fakeout (bias: {current_bias})")
                                    
                                    # Pattern: Bullish candle (candle_2) followed by Bearish candle (candle_3) with sweep
                                    is_candle_2_bullish = candle_2['close'] > candle_2['open']
                                    is_candle_3_bearish = candle_3['close'] < candle_3['open']
                                    has_sweep = candle_3['high'] > candle_2['high']
                                    
                                    self.logger.info(f"  Candle 2 bullish: {is_candle_2_bullish}")
                                    self.logger.info(f"  Candle 3 bearish: {is_candle_3_bearish}")
                                    self.logger.info(f"  Sweep detected: {has_sweep}")
                                    
                                    if is_candle_2_bullish and is_candle_3_bearish and has_sweep:
                                        self.logger.info(f"[DEBUG] ✅ BEARISH fakeout pattern CONFIRMED!")
                                        entry_price = candle_3['close']
                                        sweep_level = candle_3['high']
                                        self.logger.info(f"  Entry price: {entry_price:.5f}")
                                        self.logger.info(f"  Sweep level: {sweep_level:.5f}")
                                        
                                        # Check daily trade limit before placing order
                                        if not self.check_daily_trade_limit():
                                            self.logger.info(f"[INFO] Daily trade limit reached ({self.config['max_daily_trades']} trades today) - Skipping trade")
                                            continue
                                            
                                        if self.place_sell_order(symbol, entry_price, sweep_level):
                                            total_open_positions += 1
                                            self.symbol_data[symbol]['waiting_for_entry'] = False
                                            self.increment_daily_trades()  # Increment daily trade counter
                                        else:
                                            self.logger.info(f"[DEBUG] BEARISH order placement failed")
                                    else:
                                        self.logger.info(f"[DEBUG] ❌ BEARISH fakeout pattern NOT met")
                                        
                                # If bias is NEUTRAL, don't trade
                                else:
                                    self.logger.info(f"[DEBUG] Bias is NEUTRAL - no trading")
                                        
                        # Log status if waiting for entry
                        if self.symbol_data[symbol]['waiting_for_entry']:
                            self.smart_log(symbol, f"⏳ Waiting for {current_bias.lower()} fakeout pattern...")
                            
                    except Exception as e:
                        self.logger.error(self.format_message(f"❌ Error processing {symbol}: {e}"))
                        continue
                        
                # Wait before next analysis cycle
                time.sleep(self.config['main_loop_sleep'])  # Check every 5 seconds instead of every second
                
            except Exception as e:
                self.logger.error(self.format_message(f"❌ Error in main loop: {e}"))
                time.sleep(10)
                
    def __del__(self):
        """Cleanup on exit"""
        mt5.shutdown()

if __name__ == "__main__":
    bot = DailyOpenFakeoutBot()
    bot.run()
