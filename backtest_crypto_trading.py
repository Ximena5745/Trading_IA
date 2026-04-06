#!/usr/bin/env python3
"""
Script: backtest_crypto_trading.py
Complete CRYPTO backtesting with walk-forward analysis and P&L reporting
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.technical_agent import TechnicalAgent
from core.backtesting.engine import BacktestEngine
from core.backtesting.metrics import compute_all
from core.features.feature_engineering import FeatureEngine
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("backtest_crypto")

DATA_DIR = Path("data/raw")
MODELS_DIR = Path("data/models")
RESULTS_DIR = Path("backtest_results")
RESULTS_DIR.mkdir(exist_ok=True)

class CryptoBacktester:
    """Backtester for CRYPTO models"""
    
    def __init__(self, symbol: str, timeframe: str, model_path: Path):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_path = model_path
        self.df = None
        self.df_features = None
        self.engine = BacktestEngine()
        self.results = None
        
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
        print(f"  Computing features...")
        engine = FeatureEngine()
        
        try:
            self.df_features = engine.calculate_mtf_features(self.df, self.symbol)
            # Ensure symbol column exists for BacktestEngine
            if 'symbol' not in self.df_features.columns:
                self.df_features['symbol'] = self.symbol
            print(f"  Calculated {len(self.df_features.columns)} features")
            return True
        except Exception as e:
            print(f"  ERROR in feature calculation: {e}")
            logger.error("feature_calc_failed", symbol=self.symbol, error=str(e))
            return False
    
    def strategy_fn(self, features):
        """Generate trading signals from model predictions"""
        try:
            output = self._agent.predict(features)
            score = output.score
            
            # BUY if score > 0.52 (slightly bullish)
            if score > 0.52:
                return {
                    "action": "BUY",
                    "entry_price": features.close,
                    "stop_loss": features.close * 0.97,      # 3% SL
                    "take_profit": features.close * 1.04,    # 4% TP
                }
            
            # SELL if score < 0.48 (slightly bearish)
            elif score < 0.48:
                return {
                    "action": "SELL",
                    "entry_price": features.close,
                    "stop_loss": features.close * 1.03,      # 3% SL
                    "take_profit": features.close * 0.96,    # 4% TP (negative)
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Strategy prediction failed: {e}")
            return None
    
    def run_backtest(self, initial_capital: float = 10000.0) -> bool:
        """Run walk-forward backtest"""
        print(f"\n  Loading model: {self.model_path.name}...")
        
        if not self.model_path.exists():
            print(f"  ERROR: Model not found at {self.model_path}")
            return False
        
        self._agent = TechnicalAgent(str(self.model_path))
        if not self._agent.is_ready():
            print(f"  ERROR: Model failed to load")
            return False
        
        print(f"  Running walk-forward backtest...")
        print(f"    - Initial Capital: ${initial_capital:,.2f}")
        print(f"    - Data Points: {len(self.df_features):,}")
        
        try:
            self.results = self.engine.run_walk_forward(
                df=self.df_features,
                strategy_fn=self.strategy_fn,
                train_size=700,      # Train on 700 candles
                test_size=200,       # Test on 200 candles
                step_size=100,       # Roll forward by 100 candles
                initial_capital=initial_capital,
            )
            
            print(f"  Walk-forward complete ({len(self.results.get('windows', []))} windows)")
            return True
            
        except Exception as e:
            print(f"  ERROR in backtest: {e}")
            logger.error("backtest_failed", symbol=self.symbol, error=str(e))
            return False
    
    def print_results(self):
        """Print backtest results"""
        if not self.results:
            print("  No results available")
            return
        
        print("\n" + "=" * 90)
        print(f"  BACKTEST RESULTS: {self.symbol} {self.timeframe}")
        print("=" * 90)
        
        # Window-level metrics
        windows = self.results.get('windows', [])
        if windows:
            print(f"\n  WINDOW ANALYSIS ({len(windows)} total):")
            print("-" * 90)
            print(f"  {'Win':<4} | {'Status':<6} | {'Sharpe':<8} | {'Sortino':<8} | {'MaxDD':<8} | {'WR':<7} | {'Trades':<7} | {'RoR':<8}")
            print("-" * 90)
            
            for w in windows:
                w_num = w.get('window', 0)
                sharpe = w.get('sharpe_ratio', 0)
                sortino = w.get('sortino_ratio', 0)
                maxdd = w.get('max_drawdown', 0)
                wr = w.get('win_rate', 0)
                trades = w.get('trades', 0)
                ror = w.get('return_on_risk', 0)
                status = "PASS" if w.get('passes_thresholds', False) else "FAIL"
                
                print(f"  {w_num:<4d} | {status:<6} | {sharpe:>7.2f} | {sortino:>7.2f} | {maxdd:>6.1f}% | {wr:>5.1f}% | {trades:>6d} | {ror:>7.2f}")
        
        # Overall metrics
        print("\n  OVERALL METRICS:")
        print("-" * 90)
        
        metrics_to_show = [
            ('Total Trades', 'total_trades', 'int'),
            ('Winning Trades', 'winning_trades', 'int'),
            ('Losing Trades', 'losing_trades', 'int'),
            ('Win Rate', 'win_rate', 'pct'),
            ('Sharpe Ratio', 'sharpe_ratio', 'float'),
            ('Sortino Ratio', 'sortino_ratio', 'float'),
            ('Math Expectancy', 'math_expectancy', 'float'),
            ('Max Drawdown', 'max_drawdown', 'pct'),
            ('Return on Risk', 'return_on_risk', 'float'),
            ('Initial Capital', 'initial_capital', 'money'),
            ('Final Capital', 'final_capital', 'money'),
            ('Total Return', 'total_return', 'pct'),
            ('Annual Return', 'annual_return', 'pct'),
        ]
        
        for label, key, fmt in metrics_to_show:
            if key in self.results:
                val = self.results[key]
                
                if fmt == 'pct':
                    print(f"    {label:<25}: {val*100:>10.2f}%")
                elif fmt == 'money':
                    print(f"    {label:<25}: ${val:>10,.2f}")
                elif fmt == 'int':
                    print(f"    {label:<25}: {val:>10,d}")
                else:
                    print(f"    {label:<25}: {val:>10.4f}")
        
        # Pass/Fail summary
        passed_windows = sum(1 for w in windows if w.get('passes_thresholds', False))
        total_windows = len(windows)
        pass_rate = (passed_windows / total_windows * 100) if total_windows > 0 else 0
        
        print(f"\n  GATE ANALYSIS:")
        print("-" * 90)
        print(f"    Windows Passed: {passed_windows}/{total_windows} ({pass_rate:.1f}%)")
        
        if passed_windows / total_windows >= 0.7:
            print(f"    Status: ✅ APPROVED FOR TRADING (>70% pass rate)")
        else:
            print(f"    Status: ❌ REQUIRES OPTIMIZATION (<70% pass rate)")
        
        print("\n" + "=" * 90)
    
    def save_results(self):
        """Save detailed results to JSON"""
        if not self.results:
            return
        
        output_file = RESULTS_DIR / f"backtest_{self.symbol}_{self.timeframe}.json"
        
        # Prepare results for JSON serialization
        results_to_save = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "model_path": str(self.model_path),
            "overall_metrics": {
                k: v for k, v in self.results.items() 
                if k not in ['windows']
            },
            "windows": self.results.get('windows', [])
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_to_save, f, indent=2, default=str)
        
        print(f"\n  Results saved to {output_file}")
        return output_file

def main():
    print("=" * 90)
    print("[CRYPTO BACKTESTING] Complete Integration Testing")
    print("=" * 90)
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    model_path = MODELS_DIR / "technical_crypto_mtf_v1.pkl"
    
    all_results = {}
    
    for symbol in symbols:
        print(f"\n\n[{symbol}] BACKTESTING {symbol}")
        print("-" * 90)
        
        backtester = CryptoBacktester(symbol, timeframe, model_path)
        
        # Load data
        print(f"  Loading data...")
        if not backtester.load_data():
            continue
        
        # Compute features
        print(f"  Preparing features...")
        if not backtester.compute_features():
            continue
        
        # Run backtest
        print(f"  Running backtest...")
        if not backtester.run_backtest(initial_capital=10000.0):
            continue
        
        # Print results
        backtester.print_results()
        
        # Save results
        backtester.save_results()
        
        all_results[symbol] = backtester.results
    
    # Comparative summary
    print("\n\n" + "=" * 90)
    print("[SUMMARY] COMPARATIVE ANALYSIS")
    print("=" * 90)
    
    if all_results:
        print(f"\n  {'Symbol':<12} | {'Sharpe':<8} | {'Win Rate':<8} | {'Max DD':<8} | {'Total $':<12} | {'Status':<8}")
        print("-" * 90)
        
        for symbol in symbols:
            if symbol in all_results:
                r = all_results[symbol]
                sharpe = r.get('sharpe_ratio', 0)
                wr = r.get('win_rate', 0)
                maxdd = r.get('max_drawdown', 0)
                final = r.get('final_capital', 0)
                status = "APPROVED" if (sharpe > 1.0 and r.get('max_drawdown', 1) < 0.3) else "REVIEW"
                
                print(f"  {symbol:<12} | {sharpe:>7.2f} | {wr*100:>6.1f}% | {maxdd*100:>6.1f}% | ${final:>10,.2f} | {status:<8}")
    
    print("\n" + "=" * 90)
    print("[DONE] Backtesting complete")
    print("=" * 90)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
