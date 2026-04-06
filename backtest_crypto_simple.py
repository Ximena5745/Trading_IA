#!/usr/bin/env python3
"""
Script: backtest_crypto_simple.py
Simplified CRYPTO backtesting with direct signal generation and P&L calculation
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.technical_agent import TechnicalAgent
from core.features.feature_engineering import FeatureEngine
from core.models import FeatureSet
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("backtest_crypto_simple")

DATA_DIR = Path("data/raw")
MODELS_DIR = Path("data/models")
RESULTS_DIR = Path("backtest_results")
RESULTS_DIR.mkdir(exist_ok=True)

class SimpleBacktester:
    """Simple backtester that generates signals and calculates P&L"""
    
    def __init__(self, symbol: str, timeframe: str, model_path: Path):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_path = model_path
        self.df = None
        self.df_features = None
        self.agent = None
        self.trades = []
        self.results = {}
        
    def load_data(self):
        """Load parquet data"""
        data_path = DATA_DIR / f"{self.symbol}_{self.timeframe}.parquet"
        
        if not data_path.exists():
            print(f"  ERROR: Data not found at {data_path}")
            return False
        
        self.df = pd.read_parquet(data_path)
        print(f"  Loaded {len(self.df):,} candles")
        
        # Ensure proper column types
        if 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True)
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        
        return True
    
    def compute_features(self):
        """Compute features using FeatureEngine"""
        print(f"  Computing multi-timeframe features...")
        engine = FeatureEngine()
        
        try:
            self.df_features = engine.calculate_mtf_features(self.df, self.symbol)
            print(f"  Calculated {len(self.df_features.columns)} features from {len(self.df)} candles")
            return True
        except Exception as e:
            print(f"  ERROR in feature calculation: {e}")
            logger.error("feature_calc_failed", symbol=self.symbol, error=str(e))
            return False
    
    def load_model(self):
        """Load pre-trained model"""
        if not self.model_path.exists():
            print(f"  ERROR: Model not found at {self.model_path}")
            return False
        
        try:
            self.agent = TechnicalAgent(str(self.model_path))
            if not self.agent.is_ready():
                print(f"  ERROR: Model failed to load")
                return False
            print(f"  Model loaded: {self.model_path.name}")
            return True
        except Exception as e:
            print(f"  ERROR loading model: {e}")
            logger.error("model_load_failed", error=str(e))
            return False
    
    def generate_signals(self) -> bool:
        """Generate trading signals from model predictions"""
        print(f"  Generating trading signals...")
        
        signals = []
        failed_count = 0
        
        for idx, row in self.df_features.iterrows():
            try:
                # Create feature set from row data
                feature_dict = {}
                for col in self.df_features.columns:
                    if col not in ['timestamp', 'symbol', 'trend_direction_4h', 
                                  'volatility_regime_4h', 'trend_direction_1d', 
                                  'volatility_regime_1d', 'close', 'open', 'high', 'low', 'volume']:
                        val = row[col]
                        if pd.notna(val) and not np.isinf(val):
                            feature_dict[col] = float(val)
                
                # Manually add required fields
                feature_dict['close'] = float(row.get('close', 0))
                
                features = FeatureSet(**feature_dict)
                output = self.agent.predict(features)
                
                if output:
                    signal = {
                        'timestamp': self.df.iloc[idx]['timestamp'],
                        'close': row.get('close', 0),
                        'score': output.score,
                        'signal': 'BUY' if output.score > 0.52 else ('SELL' if output.score < 0.48 else 'HOLD'),
                    }
                    signals.append(signal)
                    
            except Exception as e:
                failed_count += 1
                continue
        
        print(f"  Generated {len(signals)} signals ({failed_count} failed)")
        
        if len(signals) < 10:
            print(f"  ERROR: Not enough signals for backtesting")
            return False
        
        self.df_signals = pd.DataFrame(signals)
        return True
    
    def backtest_signals(self, initial_capital: float = 10000.0):
        """Simple backtesting: track trades and calculate P&L"""
        print(f"  Running backtest...")
        
        capital = initial_capital
        position = None
        entry_price = 0
        trades = []
        
        for idx, row in self.df_signals.iterrows():
            signal = row['signal']
            close = row['close']
            
            # Enter BUY position
            if signal == 'BUY' and position is None:
                position = 'LONG'
                entry_price = close
                entry_time = row['timestamp']
            
            # Exit BUY position
            elif signal == 'SELL' and position == 'LONG':
                pnl = close - entry_price
                pnl_pct = (pnl / entry_price) * 100
                capital += pnl * (capital / 10000)  # Scale to current capital
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': row['timestamp'],
                    'exit_price': close,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'type': 'LONG',
                })
                
                position = None
            
            # Enter SELL position
            elif signal == 'SELL' and position is None:
                position = 'SHORT'
                entry_price = close
                entry_time = row['timestamp']
            
            # Exit SELL position
            elif signal == 'BUY' and position == 'SHORT':
                pnl = entry_price - close  # Reverse for short
                pnl_pct = (pnl / entry_price) * 100
                capital += pnl * (capital / 10000)
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': row['timestamp'],
                    'exit_price': close,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'type': 'SHORT',
                })
                
                position = None
        
        self.trades = trades
        
        # Calculate metrics
        if trades:
            pnls = np.array([t['pnl'] for t in trades])
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            losing_trades = sum(1 for t in trades if t['pnl'] < 0)
            
            self.results = {
                'total_trades': len(trades),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / len(trades) if trades else 0,
                'total_pnl': float(pnls.sum()),
                'avg_pnl': float(pnls.mean()),
                'max_win': float(pnls.max()) if len(pnls) > 0 else 0,
                'max_loss': float(pnls.min()) if len(pnls) > 0 else 0,
                'final_capital': capital,
                'initial_capital': initial_capital,
                'return_pct': ((capital - initial_capital) / initial_capital) * 100,
                'sharpe_ratio': float(np.mean(pnls) / np.std(pnls)) if np.std(pnls) > 0 else 0,
                'trades': trades,
            }
            
            return True
        
        print(f"  ERROR: No trades executed")
        return False
    
    def print_results(self):
        """Print backtest results"""
        if not self.results:
            print("  No results available")
            return
        
        print("\n" + "=" * 90)
        print(f"  BACKTEST RESULTS: {self.symbol} {self.timeframe}")
        print("=" * 90)
        
        print(f"\n  TRADE STATISTICS:")
        print("-" * 90)
        print(f"    Total Trades:      {self.results['total_trades']:>10}")
        print(f"    Winning Trades:    {self.results['winning_trades']:>10}")
        print(f"    Losing Trades:     {self.results['losing_trades']:>10}")
        print(f"    Win Rate:          {self.results['win_rate']*100:>10.2f}%")
        
        print(f"\n  PROFIT/LOSS:")
        print("-" * 90)
        print(f"    Total P&L:         ${self.results['total_pnl']:>10,.2f}")
        print(f"    Avg P&L per Trade: ${self.results['avg_pnl']:>10,.2f}")
        print(f"    Max Win:           ${self.results['max_win']:>10,.2f}")
        print(f"    Max Loss:          ${self.results['max_loss']:>10,.2f}")
        
        print(f"\n  CAPITAL:")
        print("-" * 90)
        print(f"    Initial Capital:   ${self.results['initial_capital']:>10,.2f}")
        print(f"    Final Capital:     ${self.results['final_capital']:>10,.2f}")
        print(f"    Total Return:      {self.results['return_pct']:>10.2f}%")
        
        print(f"\n  RISK METRICS:")
        print("-" * 90)
        print(f"    Sharpe Ratio:      {self.results['sharpe_ratio']:>10.4f}")
        
        # Sample trades
        if self.trades and len(self.trades) > 0:
            print(f"\n  SAMPLE TRADES (first 10):")
            print("-" * 90)
            print(f"  {'Type':<6} | {'Entry Price':<12} | {'Exit Price':<12} | {'P&L':<10} | {'%':<8}")
            print("-" * 90)
            
            for trade in self.trades[:10]:
                print(f"  {trade['type']:<6} | ${trade['entry_price']:>10.2f} | ${trade['exit_price']:>10.2f} | ${trade['pnl']:>8,.2f} | {trade['pnl_pct']:>6.2f}%")
        
        print("\n" + "=" * 90)
        
        # Status
        if self.results['sharpe_ratio'] > 1.0 and self.results['win_rate'] > 0.45:
            print(f"  STATUS: ✅ ACCEPTABLE (Sharpe={self.results['sharpe_ratio']:.2f}, WR={self.results['win_rate']*100:.1f}%)")
        else:
            print(f"  STATUS: ⚠️ NEEDS OPTIMIZATION (Sharpe={self.results['sharpe_ratio']:.2f}, WR={self.results['win_rate']*100:.1f}%)")
        
        print("=" * 90)
    
    def save_results(self):
        """Save results to JSON"""
        if not self.results:
            return
        
        output_file = RESULTS_DIR / f"backtest_{self.symbol}_{self.timeframe}_simple.json"
        
        results_to_save = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': datetime.utcnow().isoformat(),
            'model_path': str(self.model_path),
            **{k: v for k, v in self.results.items() if k != 'trades'},
            'sample_trades': self.trades[:20],  # Save first 20 trades
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_to_save, f, indent=2, default=str)
        
        print(f"\n  Results saved to {output_file}")

def main():
    print("=" * 90)
    print("[CRYPTO BACKTESTING] Simple Signal-based Analysis")
    print("=" * 90)
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    model_path = MODELS_DIR / "technical_crypto_mtf_v1.pkl"
    
    all_results = {}
    
    for symbol in symbols:
        print(f"\n\n[{symbol}] BACKTESTING {symbol}")
        print("-" * 90)
        
        backtester = SimpleBacktester(symbol, timeframe, model_path)
        
        # Load data
        print(f"  Loading data...")
        if not backtester.load_data():
            continue
        
        # Compute features
        print(f"  Preparing features...")
        if not backtester.compute_features():
            continue
        
        # Load model
        print(f"  Initializing model...")
        if not backtester.load_model():
            continue
        
        # Generate signals
        if not backtester.generate_signals():
            continue
        
        # Run backtest
        if not backtester.backtest_signals(initial_capital=10000.0):
            continue
        
        # Print and save results
        backtester.print_results()
        backtester.save_results()
        
        all_results[symbol] = backtester.results
    
    # Comparative summary
    if all_results:
        print("\n\n" + "=" * 90)
        print("[SUMMARY] CRYPTO MODELS PERFORMANCE")
        print("=" * 90)
        
        print(f"\n  {'Symbol':<12} | {'Trades':<8} | {'Win Rate':<8} | {'Total P&L':<12} | {'Return':<8} | {'Sharpe':<8}")
        print("-" * 90)
        
        for symbol in symbols:
            if symbol in all_results:
                r = all_results[symbol]
                print(f"  {symbol:<12} | {r['total_trades']:<8} | {r['win_rate']*100:<7.1f}% | ${r['total_pnl']:>10,.2f} | {r['return_pct']:>6.2f}% | {r['sharpe_ratio']:>7.2f}")
    
    print("\n" + "=" * 90)
    print("[DONE] Backtesting complete")
    print("=" * 90)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
