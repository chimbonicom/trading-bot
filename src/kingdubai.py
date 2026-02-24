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
                'last_trade_time': None,
                'processed_candles': set(),  # Track processed candles to prevent duplicates
                'last_daily_open_date': None  # Track when daily open was last set
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
        
        # Track processed trades to avoid duplicate reporting
        self.processed_trades = set()
        
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
        config['risk_reward_ratio'] = float(os.getenv('RISK_REWARD_RATIO', '3.0'))
        
        # Convert pips to price values
        sweep_tolerance_pips = float(os.getenv('SWEEP_TOLERANCE_PIPS', '1'))
        config['sweep_tolerance'] = sweep_tolerance_pips  # Store as pips, convert when needed
        
        bias_confirmation_pips = float(os.getenv('BIAS_CONFIRMATION_PIPS', '10'))
        config['bias_confirmation_pips'] = bias_confirmation_pips
        
        # Stop Loss Settings
        config['sl_breathing_room_pips'] = int(os.getenv('SL_BREATHING_ROOM_PIPS', '3'))
        config['sl_min_distance_pips'] = int(os.getenv('SL_MIN_DISTANCE_PIPS', '6'))
        
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
        
    def validate_symbols(self):
        """Validate that all symbols exist and are tradeable"""
        self.logger.info("🔍 Validating symbols...")
        valid_symbols = []
        
        for symbol in self.symbols:
            try:
                # Check if symbol exists
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    self.logger.error(f"❌ Symbol {symbol} not found in MT5")
                    continue
                
                # Check if symbol is tradeable
                if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    self.logger.error(f"❌ Symbol {symbol} is not tradeable (mode: {symbol_info.trade_mode})")
                    continue
                
                # Check if symbol is visible
                if not symbol_info.visible:
                    self.logger.warning(f"⚠️ Symbol {symbol} is not visible, attempting to add...")
                    if not mt5.symbol_select(symbol, True):
                        self.logger.error(f"❌ Failed to add symbol {symbol}")
                        continue
                
                valid_symbols.append(symbol)
                self.logger.info(f"✅ Symbol {symbol} validated successfully")
                
            except Exception as e:
                self.logger.error(f"❌ Error validating symbol {symbol}: {e}")
                continue
        
        if not valid_symbols:
            raise ValueError("No valid symbols found! Please check your configuration.")
        
        self.symbols = valid_symbols
        self.logger.info(f"🎯 Valid symbols: {', '.join(valid_symbols)}")
        
    def validate_configuration(self):
        """Validate configuration and print summary"""
        # Validate symbols first
        self.validate_symbols()
        
        self.logger.info("🔧 Configuration Summary:")
        self.logger.info("=" * 50)
        self.logger.info(f"📊 Symbols: {', '.join(self.symbols)}")
        self.logger.info(f"💰 Lot Sizes: {', '.join([f'{s}: {self.symbol_lots[s]}' for s in self.symbols])}")
        self.logger.info(f"⏰ Timeframe: {self.config['timeframe']}")
        self.logger.info(f"🎯 Max Open Trades: {self.config['max_open_trades']}")
        self.logger.info(f"📈 Risk:Reward Ratio: 1:{self.config['risk_reward_ratio']}")
        self.logger.info(f"🔄 Sweep Tolerance: {self.config['sweep_tolerance']} pips")
        self.logger.info(f"📊 Bias Confirmation: {self.config['bias_confirmation_pips']} pips")
        self.logger.info(f"📄 Auto Reports: {'Enabled' if self.config['auto_reports'] else 'Disabled'}")
        self.logger.info(f"⏱️ Report Interval: {self.config['report_interval']} seconds")
        self.logger.info(f"🔄 Main Loop Sleep: {self.config['main_loop_sleep']} seconds")
        self.logger.info(f"📝 Status Log Interval: {self.config['status_log_interval']} seconds")
        self.logger.info(f"🔢 Magic Number: {self.config['magic_number']}")
        self.logger.info("=" * 50)
        
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
        
    def get_daily_open_tanzania(self, symbol: str) -> float:
        """Get daily open for Tanzania timezone (UTC+3) - broker opens at midnight local time"""
        try:
            # Check for manual override first
            override_value = self.config.get('daily_open_override', 0)
            if override_value != 0:
                self.logger.info(f"[OVERRIDE] Using manual daily open: {override_value:.5f}")
                return override_value
            
            # Get today's midnight in Tanzania time (UTC+3)
            # Use UTC and add 3 hours to get Tanzania time
            from datetime import timezone, timedelta
            tanzania_tz = timezone(timedelta(hours=3))
            
            # Get current UTC time
            utc_now = datetime.now(timezone.utc)
            
            # Convert to Tanzania time
            tanzania_now = utc_now.astimezone(tanzania_tz)
            
            # Get today's midnight in Tanzania time
            today_tanzania = tanzania_now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Convert back to UTC for MT5
            today_utc = today_tanzania.astimezone(timezone.utc)
            
            # Get the first minute of today's session
            rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, today_utc, 1)
            
            if rates is not None and len(rates) > 0:
                daily_open = rates[0]['open']
                self.logger.info(f"[TANZANIA] Daily Open ({today_tanzania.strftime('%Y-%m-%d %H:%M:%S')}): {daily_open:.5f}")
                return daily_open
            else:
                self.logger.error("[ERROR] Could not get daily open for Tanzania timezone")
                return None
                
        except Exception as e:
            self.logger.error(f"[ERROR] Error getting Tanzania daily open: {e}")
            return None
        
    def determine_bias(self, symbol: str, current_price: float) -> str:
        """Determine current bias based on price vs daily open"""
        daily_open = self.symbol_data[symbol]['daily_open']
        if daily_open is None:
            return "NEUTRAL"
            
        price_diff = current_price - daily_open
        bias_threshold = self.pips_to_price(symbol, self.config['bias_confirmation_pips'])
        
        # Calculate new bias
        if price_diff > bias_threshold:
            new_bias = "BULLISH"
        elif price_diff < -bias_threshold:
            new_bias = "BEARISH"
        else:
            new_bias = "NEUTRAL"
        
        # Only log if bias changed
        current_bias = self.symbol_data[symbol]['current_bias']
        if new_bias != current_bias:
            self.logger.info(f"[DEBUG] Bias changed for {symbol}: {current_bias} → {new_bias}")
            self.logger.info(f"  Price: {current_price:.5f}, Daily Open: {daily_open:.5f}, Diff: {price_diff:.5f}")
            
        return new_bias
            
    def detect_bullish_fakeout(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, float, float]:
        """Detect bullish fakeout: Bearish candle followed by bullish candle that sweeps below"""
        if len(df) < 2:
            return False, 0.0, 0.0
            
        # Use the last completed candle and current forming candle
        bearish_candle = df.iloc[-2]  # Last completed candle
        current_candle = df.iloc[-1]  # Current forming candle
        
        # Check if current candle is bullish (close > open)
        is_current_bullish = current_candle['close'] > current_candle['open']
        
        # Check if previous candle was bearish
        is_prev_bearish = bearish_candle['close'] < bearish_candle['open']
        
        # Check if current candle's low sweeps below previous bearish candle's low
        sweep_detected = current_candle['low'] < bearish_candle['low']
        
        # Add minimum sweep distance requirement
        if sweep_detected:
            sweep_distance = bearish_candle['low'] - current_candle['low']
            min_sweep = self.pips_to_price(symbol, self.config['sweep_tolerance'])
            sweep_detected = sweep_distance >= min_sweep
        
        if is_prev_bearish and is_current_bullish and sweep_detected:
            self.logger.info(f"[DEBUG] BULLISH fakeout confirmed for {symbol}")
            return True, current_candle['close'], current_candle['low']
        
        return False, 0.0, 0.0

    def detect_bearish_fakeout(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, float, float]:
        """Detect bearish fakeout: Bullish candle followed by bearish candle that sweeps above"""
        if len(df) < 2:
            return False, 0.0, 0.0
            
        # Use the last completed candle and current forming candle
        bullish_candle = df.iloc[-2]  # Last completed candle
        current_candle = df.iloc[-1]  # Current forming candle
        
        # Check if current candle is bearish (close < open)
        is_current_bearish = current_candle['close'] < current_candle['open']
        
        # Check if previous candle was bullish
        is_prev_bullish = bullish_candle['close'] > bullish_candle['open']
        
        # Check if current candle's high sweeps above previous bullish candle's high
        sweep_detected = current_candle['high'] > bullish_candle['high']
        
        # Add minimum sweep distance requirement
        if sweep_detected:
            sweep_distance = current_candle['high'] - bullish_candle['high']
            min_sweep = self.pips_to_price(symbol, self.config['sweep_tolerance'])
            sweep_detected = sweep_distance >= min_sweep
        
        if is_prev_bullish and is_current_bearish and sweep_detected:
            self.logger.info(f"[DEBUG] BEARISH fakeout confirmed for {symbol}")
            return True, current_candle['close'], current_candle['high']
        
        return False, 0.0, 0.0
        
    def calculate_sl_tp(self, entry_price: float, sweep_level: float, is_buy: bool, symbol: str) -> Tuple[float, float]:
        """Calculate SL and TP with proper validation and breathing room"""
        
        # Use configurable breathing room and minimum distance
        breathing_room_pips = self.config.get('sl_breathing_room_pips', 3)
        breathing_room = self.pips_to_price(symbol, breathing_room_pips)
        
        min_distance_pips = self.config.get('sl_min_distance_pips', 6)
        min_distance = self.pips_to_price(symbol, min_distance_pips)
        
        if is_buy:
            # For buy orders: SL below sweep level with breathing room
            # Validate that sweep level makes sense (should be below entry)
            if sweep_level >= entry_price:
                self.logger.error(f"[ERROR] Invalid sweep level for BUY: sweep={sweep_level:.5f}, entry={entry_price:.5f}")
                return None, None
            
            sl_distance = entry_price - sweep_level + breathing_room
            sl_distance = max(sl_distance, min_distance)  # Ensure minimum distance
            
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * self.config['risk_reward_ratio'])
            
        else:
            # For sell orders: SL above sweep level with breathing room
            # Validate that sweep level makes sense (should be above entry)
            if sweep_level <= entry_price:
                self.logger.error(f"[ERROR] Invalid sweep level for SELL: sweep={sweep_level:.5f}, entry={entry_price:.5f}")
                return None, None
            
            sl_distance = sweep_level - entry_price + breathing_room
            sl_distance = max(sl_distance, min_distance)  # Ensure minimum distance
            
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * self.config['risk_reward_ratio'])
        
        self.logger.info(f"[DEBUG] SL/TP Calculation for {symbol}:")
        self.logger.info(f"  Entry: {entry_price:.5f}")
        self.logger.info(f"  Sweep: {sweep_level:.5f}")
        self.logger.info(f"  SL: {stop_loss:.5f} ({self.price_to_pips(symbol, sl_distance):.1f} pips)")
        self.logger.info(f"  TP: {take_profit:.5f} ({self.price_to_pips(symbol, sl_distance * self.config['risk_reward_ratio']):.1f} pips)")
        
        return stop_loss, take_profit
        
    def validate_sl_tp(self, entry_price: float, stop_loss: float, take_profit: float, is_buy: bool, symbol: str) -> bool:
        """Validate that SL and TP have enough room and are valid"""
        # Get current market info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            self.logger.error(f"❌ Cannot get symbol info for {symbol}")
            return False
            
        # Check minimum distance requirements
        min_distance_pips = 5
        min_distance = self.pips_to_price(symbol, min_distance_pips)
        
        if is_buy:
            sl_distance = entry_price - stop_loss
            tp_distance = take_profit - entry_price
        else:
            sl_distance = stop_loss - entry_price
            tp_distance = entry_price - take_profit
            
        # Validate distances
        if sl_distance < min_distance:
            self.logger.warning(f"⚠️ Stop Loss too close: {self.price_to_pips(symbol, sl_distance):.1f} pips (min: {min_distance_pips})")
            return False
            
        if tp_distance < (sl_distance * self.config['risk_reward_ratio'] * 0.8):  # Allow 20% tolerance
            self.logger.warning(f"⚠️ Take Profit too close: {self.price_to_pips(symbol, tp_distance):.1f} pips")
            return False
            
        # Check against symbol limits
        if sl_distance < symbol_info.trade_stops_level * symbol_info.point:
            self.logger.warning(f"⚠️ Stop Loss below broker minimum: {self.price_to_pips(symbol, sl_distance):.1f} pips")
            return False
            
        self.logger.info(f"✅ SL/TP validation passed:")
        self.logger.info(f"  SL Distance: {self.price_to_pips(symbol, sl_distance):.1f} pips")
        self.logger.info(f"  TP Distance: {self.price_to_pips(symbol, tp_distance):.1f} pips")
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
        """Place a buy order with current market prices"""
        if not self.can_trade(symbol):
            return False
            
        # Get current market prices
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            self.logger.error(f"❌ Cannot get current market prices for {symbol}")
            return False
            
        # Use current ask price for buy orders
        current_price = tick.ask
        
        stop_loss, take_profit = self.calculate_sl_tp(current_price, sweep_level, True, symbol)
        
        # Add this validation:
        if stop_loss is None or take_profit is None:
            self.logger.error(f"SL/TP calculation failed for {symbol} - skipping trade")
            return False
        
        # Validate SL/TP before placing order
        if not self.validate_sl_tp(current_price, stop_loss, take_profit, True, symbol):
            self.logger.error("❌ SL/TP validation failed - skipping order")
            return False
            
        lot_size = self.symbol_lots[symbol]
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": current_price,
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
            self.logger.info(self.format_message(f"🚀 BULLISH ENTRY: {symbol} at {current_price:.5f} | SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Lot: {lot_size}"))
            self.performance['total_trades'] += 1
            self.performance['last_trade_time'] = datetime.now()
            self.symbol_data[symbol]['last_trade_time'] = datetime.now()
            return True
        else:
            self.logger.error(self.format_message(f"❌ BUY order failed: {result.comment}"))
            return False
            
    def place_sell_order(self, symbol: str, entry_price: float, sweep_level: float):
        """Place a sell order with current market prices"""
        if not self.can_trade(symbol):
            return False
            
        # Get current market prices
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            self.logger.error(f"❌ Cannot get current market prices for {symbol}")
            return False
            
        # Use current bid price for sell orders
        current_price = tick.bid
        
        stop_loss, take_profit = self.calculate_sl_tp(current_price, sweep_level, False, symbol)
        
        # Add this validation:
        if stop_loss is None or take_profit is None:
            self.logger.error(f"SL/TP calculation failed for {symbol} - skipping trade")
            return False
        
        # Validate SL/TP before placing order
        if not self.validate_sl_tp(current_price, stop_loss, take_profit, False, symbol):
            self.logger.error("❌ SL/TP validation failed - skipping order")
            return False
            
        lot_size = self.symbol_lots[symbol]
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": current_price,
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
            self.logger.info(self.format_message(f"🔻 BEARISH ENTRY: {symbol} at {current_price:.5f} | SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Lot: {lot_size}"))
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
            
        # Only check for trades from the current session (since bot started)
        if not hasattr(self, 'session_start_time'):
            self.session_start_time = datetime.now()
            
        deals = mt5.history_deals_get(self.session_start_time, datetime.now())
        
        if deals:
            for deal in deals:
                if deal.magic == self.config['magic_number']:  # Our bot's trades
                    # Create unique trade ID to prevent duplicate processing
                    trade_id = f"{deal.ticket}_{deal.time}"
                    
                    # Check if we've already processed this trade
                    if trade_id not in self.processed_trades:
                        self.processed_trades.add(trade_id)
                        
                        # Check if this is a new closed trade
                        if hasattr(deal, 'profit') and deal.profit != 0:
                            if deal.profit > 0:
                                self.performance['winning_trades'] += 1
                                self.logger.info(self.format_message(f"✅ TP HIT: +${deal.profit:.2f}"))
                            else:
                                self.performance['losing_trades'] += 1
                                self.logger.info(self.format_message(f"❌ SL HIT: ${deal.profit:.2f}"))
                                
                            # Update best/worst trade
                            if deal.profit > self.performance['best_trade']:
                                self.performance['best_trade'] = deal.profit
                            if deal.profit < self.performance['worst_trade']:
                                self.performance['worst_trade'] = deal.profit
                
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
                
                total_positions = self.get_open_positions_count()
                
                for symbol in self.symbols:
                    try:
                        # Reset daily data if new trading day
                        self.reset_daily_data(symbol)
                        
                        # Check symbol-specific positions
                        symbol_positions = self.get_open_positions_count(symbol)
                        total_positions = self.get_open_positions_count()
                        
                        # Check if we can take more trades
                        if total_positions >= self.config['max_open_trades'] or symbol_positions > 0:
                            if self.symbol_data[symbol]['waiting_for_entry']:
                                self.smart_log(symbol, "Waiting for existing trade to close...", force_log=True)
                                self.symbol_data[symbol]['waiting_for_entry'] = False
                            continue
                            
                        # Get current market data
                        df = self.get_ohlc_data(symbol, self.config['timeframe'], 15)  # Reduced from 50 to 15
                        if df.empty:
                            continue
                            
                        # Update daily open if needed
                        if self.symbol_data[symbol]['daily_open'] is None:
                            daily_open = self.get_daily_open_tanzania(symbol)
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
                            
                            # Check for patterns on current forming candle
                            if len(df) >= 2:  # Need at least 2 candles (1 completed + 1 forming)
                                # Check for patterns on the current forming candle
                                if current_bias == "BULLISH":
                                    pattern_detected, entry_price, sweep_level = self.detect_bullish_fakeout(df, symbol)
                                    if pattern_detected:
                                        if self.place_buy_order(symbol, entry_price, sweep_level):
                                            self.symbol_data[symbol]['waiting_for_entry'] = False
                                        
                                elif current_bias == "BEARISH":
                                    pattern_detected, entry_price, sweep_level = self.detect_bearish_fakeout(df, symbol)
                                    if pattern_detected:
                                        if self.place_sell_order(symbol, entry_price, sweep_level):
                                            self.symbol_data[symbol]['waiting_for_entry'] = False
                                            
                        # Status logging
                        if self.symbol_data[symbol]['waiting_for_entry']:
                            if current_bias == "BULLISH":
                                self.smart_log(symbol, "[WAIT] Waiting for bullish fakeout pattern...")
                            elif current_bias == "BEARISH":
                                self.smart_log(symbol, "[WAIT] Waiting for bearish fakeout pattern...")
                            else:
                                self.smart_log(symbol, "[WAIT] Waiting for bias confirmation...")
                                
                    except Exception as e:
                        self.logger.error(f"❌ Error processing {symbol}: {e}")
                        continue
                        
                # Wait before next analysis cycle
                time.sleep(self.config['main_loop_sleep'])  # Check every 5 seconds instead of every second
                
            except Exception as e:
                self.logger.error(self.format_message(f"❌ Error in main loop: {e}"))
                time.sleep(10)
                
    def __del__(self):
        """Cleanup on exit"""
        mt5.shutdown()

    def get_pip_value(self, symbol: str) -> float:
        """Get the correct pip value for the symbol (0.01 for JPY pairs, 0.0001 for others)"""
        if 'JPY' in symbol:
            return 0.01  # JPY pairs have 2 decimal places
        else:
            return 0.0001  # Other pairs have 4 decimal places
            
    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price value for the given symbol"""
        pip_value = self.get_pip_value(symbol)
        return pips * pip_value
        
    def price_to_pips(self, symbol: str, price: float) -> float:
        """Convert price value to pips for the given symbol"""
        pip_value = self.get_pip_value(symbol)
        return price / pip_value

    def reset_daily_data(self, symbol: str):
        """Reset daily data for new trading day"""
        current_date = datetime.now().date()
        last_date = self.symbol_data[symbol]['last_daily_open_date']
        
        if last_date is None or current_date > last_date:
            self.logger.info(f"🔄 New trading day detected for {symbol}, resetting daily data")
            self.symbol_data[symbol]['daily_open'] = None
            self.symbol_data[symbol]['processed_candles'].clear()
            self.symbol_data[symbol]['last_daily_open_date'] = current_date
            self.symbol_data[symbol]['current_bias'] = "NEUTRAL"
            return True
        return False

if __name__ == "__main__":
    bot = DailyOpenFakeoutBot()
    bot.run()
