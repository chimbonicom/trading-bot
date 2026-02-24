import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import os
import json
from dotenv import load_dotenv

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.env')
load_dotenv(config_path)

class PerformanceAnalyzer:
    def __init__(self):
        self.magic_number = 234002  # Daily Open Bot magic number
        self.reports_path = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(self.reports_path, exist_ok=True)
        
        # Initialize MT5 connection
        self.connect_mt5()
        
        # Performance data structure
        self.performance_data = {
            'trades': [],
            'daily_stats': {},
            'summary': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'total_days': 0
            }
        }
        
    def connect_mt5(self):
        """Connect to MT5 terminal"""
        if not mt5.initialize():
            print("❌ MT5 initialization failed!")
            return False
            
        # Login to account
        login = int(os.getenv('MT5_LOGIN'))
        password = os.getenv('MT5_PASSWORD')
        server = os.getenv('MT5_SERVER')
        
        if not mt5.login(login=login, password=password, server=server):
            print("❌ MT5 login failed!")
            return False
            
        print(f"✅ Connected to MT5: {server}")
        return True
        
    def get_closed_trades(self, days_back: int = 30) -> List:
        """Get closed trades from MT5"""
        # Get trades from the last N days
        from_date = datetime.now() - timedelta(days=days_back)
        
        # Get history deals
        deals = mt5.history_deals_get(from_date, datetime.now())
        if deals is None:
            return []
            
        # Filter for our bot's trades and organize by position_id
        bot_deals = {}
        for deal in deals:
            if deal.magic == self.magic_number:
                position_id = deal.position_id
                if position_id not in bot_deals:
                    bot_deals[position_id] = {'entry': None, 'exit': None}
                
                if deal.entry == 0:  # Entry deal
                    bot_deals[position_id]['entry'] = deal
                elif deal.entry == 1:  # Exit deal
                    bot_deals[position_id]['exit'] = deal
        
        # Create trade records from entry/exit pairs
        bot_trades = []
        for position_id, deal_pair in bot_deals.items():
            entry_deal = deal_pair['entry']
            exit_deal = deal_pair['exit']
            
            # Only include complete trades (both entry and exit)
            if entry_deal and exit_deal:
                bot_trades.append({
                    'ticket': entry_deal.ticket,
                    'symbol': entry_deal.symbol,
                    'type': 'BUY' if entry_deal.type == 0 else 'SELL',
                    'volume': entry_deal.volume,
                    'open_time': datetime.fromtimestamp(entry_deal.time),
                    'close_time': datetime.fromtimestamp(exit_deal.time),
                    'open_price': entry_deal.price,
                    'close_price': exit_deal.price,
                    'profit': exit_deal.profit,
                    'swap': exit_deal.swap,
                    'commission': exit_deal.commission,
                    'comment': entry_deal.comment
                })
                
        return bot_trades
        
    def analyze_trades(self, trades: List) -> Dict:
        """Analyze trade performance"""
        if not trades:
            return self.performance_data['summary']
            
        # Calculate basic stats
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] < 0]
        
        total_pnl = sum(t['profit'] for t in trades)
        total_wins = sum(t['profit'] for t in winning_trades)
        total_losses = sum(t['profit'] for t in losing_trades)
        
        # Calculate averages
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0
        
        # Calculate win rate
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        # Find best and worst trades
        best_trade = max(trades, key=lambda x: x['profit'])['profit'] if trades else 0
        worst_trade = min(trades, key=lambda x: x['profit'])['profit'] if trades else 0
        
        # Calculate profit factor
        profit_factor = abs(total_wins / total_losses) if total_losses != 0 else float('inf')
        
        # Calculate max drawdown
        max_drawdown = self.calculate_max_drawdown(trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'total_days': (datetime.now() - min(t['open_time'] for t in trades)).days if trades else 0
        }
        
    def calculate_max_drawdown(self, trades: List) -> float:
        """Calculate maximum drawdown"""
        if not trades:
            return 0.0
            
        # Sort trades by open time
        sorted_trades = sorted(trades, key=lambda x: x['open_time'])
        
        peak = 0.0
        max_dd = 0.0
        running_pnl = 0.0
        
        for trade in sorted_trades:
            running_pnl += trade['profit']
            
            if running_pnl > peak:
                peak = running_pnl
                
            drawdown = peak - running_pnl
            if drawdown > max_dd:
                max_dd = drawdown
                
        return max_dd
        
    def generate_daily_stats(self, trades: List) -> Dict:
        """Generate daily performance statistics"""
        daily_stats = {}
        
        for trade in trades:
            date = trade['open_time'].strftime('%Y-%m-%d')
            
            if date not in daily_stats:
                daily_stats[date] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'pnl': 0.0,
                    'win_rate': 0.0
                }
                
            daily_stats[date]['trades'] += 1
            daily_stats[date]['pnl'] += trade['profit']
            
            if trade['profit'] > 0:
                daily_stats[date]['wins'] += 1
            else:
                daily_stats[date]['losses'] += 1
                
        # Calculate daily win rates
        for date in daily_stats:
            daily_stats[date]['win_rate'] = (
                daily_stats[date]['wins'] / daily_stats[date]['trades'] * 100
            )
            
        return daily_stats
        
    def generate_html_report(self, trades: List, summary: Dict, daily_stats: Dict):
        """Generate professional HTML performance report"""
        
        # Create HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Open Bot Performance Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            border-left: 4px solid #3498db;
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #f39c12; }}
        .trades-section {{
            padding: 30px;
            border-top: 1px solid #ecf0f1;
        }}
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .trades-table th {{
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 500;
        }}
        .trades-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .trades-table tr:hover {{
            background: #f8f9fa;
        }}
        .trade-profit {{
            font-weight: bold;
        }}
        .trade-profit.positive {{ color: #27ae60; }}
        .trade-profit.negative {{ color: #e74c3c; }}
        .daily-chart {{
            padding: 30px;
            border-top: 1px solid #ecf0f1;
        }}
        .chart-container {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        .summary-row {{
            background: #ecf0f1;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Daily Open Bot Performance</h1>
            <p>Professional Trading Analysis Report</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{summary['total_trades']}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value positive">{summary['win_rate']:.1f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {'positive' if summary['total_pnl'] > 0 else 'negative'}">
                    ${summary['total_pnl']:.2f}
                </div>
                <div class="stat-label">Total P&L</div>
            </div>
            <div class="stat-card">
                <div class="stat-value positive">{summary['profit_factor']:.2f}</div>
                <div class="stat-label">Profit Factor</div>
            </div>
            <div class="stat-card">
                <div class="stat-value positive">${summary['avg_win']:.2f}</div>
                <div class="stat-label">Average Win</div>
            </div>
            <div class="stat-card">
                <div class="stat-value negative">${summary['avg_loss']:.2f}</div>
                <div class="stat-label">Average Loss</div>
            </div>
            <div class="stat-card">
                <div class="stat-value positive">${summary['best_trade']:.2f}</div>
                <div class="stat-label">Best Trade</div>
            </div>
            <div class="stat-card">
                <div class="stat-value negative">${summary['worst_trade']:.2f}</div>
                <div class="stat-label">Worst Trade</div>
            </div>
            <div class="stat-card">
                <div class="stat-value negative">${summary['max_drawdown']:.2f}</div>
                <div class="stat-label">Max Drawdown</div>
            </div>
            <div class="stat-card">
                <div class="stat-value neutral">{summary['total_days']}</div>
                <div class="stat-label">Trading Days</div>
            </div>
        </div>
        
        <div class="trades-section">
            <h2>📊 Recent Trades</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Volume</th>
                        <th>P&L</th>
                        <th>Comment</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add trade rows
        for trade in trades[-20:]:  # Show last 20 trades
            profit_class = 'positive' if trade['profit'] > 0 else 'negative'
            html_content += f"""
                    <tr>
                        <td>{trade['open_time'].strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade['symbol']}</td>
                        <td>{trade['type']}</td>
                        <td>{trade['open_price']:.5f}</td>
                        <td>{trade['close_price']:.5f}</td>
                        <td>{trade['volume']}</td>
                        <td class="trade-profit {profit_class}">${trade['profit']:.2f}</td>
                        <td>{trade['comment']}</td>
                    </tr>
            """
            
        html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="daily-chart">
            <h2>📈 Daily Performance</h2>
            <div class="chart-container">
                <table class="trades-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Trades</th>
                            <th>Wins</th>
                            <th>Losses</th>
                            <th>Win Rate</th>
                            <th>Daily P&L</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Add daily stats
        for date, stats in sorted(daily_stats.items(), reverse=True):
            pnl_class = 'positive' if stats['pnl'] > 0 else 'negative'
            html_content += f"""
                        <tr>
                            <td>{date}</td>
                            <td>{stats['trades']}</td>
                            <td>{stats['wins']}</td>
                            <td>{stats['losses']}</td>
                            <td>{stats['win_rate']:.1f}%</td>
                            <td class="trade-profit {pnl_class}">${stats['pnl']:.2f}</td>
                        </tr>
            """
            
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Daily Open Line Fakeout Bot - Professional Trading Analysis</p>
            <p>Strategy: Daily Open Line + Fakeout Patterns | Timeframe: M5 | Risk:Reward 1:3</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Save HTML file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"performance_report_{timestamp}.html"
        filepath = os.path.join(self.reports_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return filepath
        
    def generate_report(self, days_back: int = 30):
        """Generate complete performance report"""
        print("📊 Generating Performance Report...")
        
        # Get trades
        trades = self.get_closed_trades(days_back)
        if not trades:
            print("❌ No trades found for analysis")
            return
            
        print(f"✅ Found {len(trades)} trades for analysis")
        
        # Analyze performance
        summary = self.analyze_trades(trades)
        daily_stats = self.generate_daily_stats(trades)
        
        # Generate HTML report
        report_path = self.generate_html_report(trades, summary, daily_stats)
        
        # Print summary
        print("\n" + "="*60)
        print("📈 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print(f"Total P&L: ${summary['total_pnl']:.2f}")
        print(f"Profit Factor: {summary['profit_factor']:.2f}")
        print(f"Average Win: ${summary['avg_win']:.2f}")
        print(f"Average Loss: ${summary['avg_loss']:.2f}")
        print(f"Best Trade: ${summary['best_trade']:.2f}")
        print(f"Worst Trade: ${summary['worst_trade']:.2f}")
        print(f"Max Drawdown: ${summary['max_drawdown']:.2f}")
        print(f"Trading Days: {summary['total_days']}")
        print("="*60)
        
        print(f"\n📄 HTML Report generated: {report_path}")
        print("🌐 Open the HTML file in your browser to view the full report")
        
        return report_path
        
    def __del__(self):
        """Cleanup on exit"""
        mt5.shutdown()

if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.generate_report()
