#!/usr/bin/env python3
"""
Script: report_crypto_trading.py
Generate CRYPTO trading report with model analysis and signal statistics
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json
import pickle

sys.path.insert(0, str(Path(__file__).parent))

from core.features.feature_engineering import FeatureEngine
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("report_crypto")

DATA_DIR = Path("data/raw")
MODELS_DIR = Path("data/models")
RESULTS_DIR = Path("backtest_results")
RESULTS_DIR.mkdir(exist_ok=True)

class CryptoTradingReport:
    """Generate comprehensive trading report for CRYPTO models"""
    
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = None
        self.df_features = None
        self.model = None
        self.report = {}
        
    def load_data(self):
        """Load market data"""
        data_path = DATA_DIR / f"{self.symbol}_{self.timeframe}.parquet"
        
        if not data_path.exists():
            print(f"  ERROR: Data not found")
            return False
        
        self.df = pd.read_parquet(data_path)
        print(f"  Loaded {len(self.df):,} candles")
        
        if 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True)
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        
        return True
    
    def compute_features(self):
        """Compute features"""
        print(f"  Computing features...")
        engine = FeatureEngine()
        
        try:
            self.df_features = engine.calculate_mtf_features(self.df, self.symbol)
            print(f"  Calculated {len(self.df_features.columns)} features")
            return True
        except Exception as e:
            print(f"  ERROR: {e}")
            return False
    
    def load_model(self):
        """Load trained model"""
        model_path = MODELS_DIR / "technical_crypto_mtf_v1.pkl"
        
        if not model_path.exists():
            print(f"  ERROR: Model not found")
            return False
        
        try:
            with open(model_path, 'rb') as f:
                payload = pickle.load(f)
                self.model = payload.get('model')
                if self.model is None:
                    print(f"  ERROR: No model in payload")
                    return False
            print(f"  Model loaded (LightGBM)")
            return True
        except Exception as e:
            print(f"  ERROR: {e}")
            return False
    
    def generate_signals(self, threshold: float = 0.5):
        """Generate trading signals using model predictions"""
        print(f"  Generating trading signals...")
        
        if self.model is None:
            print(f"  ERROR: Model not loaded")
            return False
        
        try:
            # Filter to only numeric columns
            numeric_cols = []
            for col in self.df_features.columns:
                if col not in ['timestamp', 'symbol', 'trend_direction_4h',
                             'volatility_regime_4h', 'trend_direction_1d',
                             'volatility_regime_1d', 'trend_direction', 'volatility_regime']:
                    if self.df_features[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                        numeric_cols.append(col)
            
            print(f"  Using {len(numeric_cols)} numeric features")
            
            X = self.df_features[numeric_cols].fillna(0).values.astype(np.float32)
            
            # Get model predictions
            predictions = self.model.predict_proba(X)  # Shape: (n_samples, 2)
            scores = predictions[:, 1]  # Probability of class 1 (BUY)
            
            # Generate signals
            signals = []
            for i, score in enumerate(scores):
                timestamp = self.df.iloc[i]['timestamp'] if i < len(self.df) else None
                close = self.df.iloc[i]['close'] if i < len(self.df) else 0
                
                if score > threshold + 0.02:
                    signal = 'BUY'
                elif score < threshold - 0.02:
                    signal = 'SELL'
                else:
                    signal = 'HOLD'
                
                signals.append({
                    'timestamp': timestamp,
                    'close': close,
                    'score': float(score),
                    'signal': signal,
                })
            
            self.df_signals = pd.DataFrame(signals)
            
            # Statistics
            buy_count = sum(1 for s in signals if s['signal'] == 'BUY')
            sell_count = sum(1 for s in signals if s['signal'] == 'SELL')
            hold_count = sum(1 for s in signals if s['signal'] == 'HOLD')
            
            print(f"  Generated {len(signals)} signals:")
            print(f"    - BUY:  {buy_count} ({buy_count/len(signals)*100:.1f}%)")
            print(f"    - SELL: {sell_count} ({sell_count/len(signals)*100:.1f}%)")
            print(f"    - HOLD: {hold_count} ({hold_count/len(signals)*100:.1f}%)")
            
            return True
            
        except Exception as e:
            print(f"  ERROR generating signals: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def backtest_simple(self, initial_capital: float = 10000.0):
        """Simple backtesting logic"""
        print(f"  Running simple backtest...")
        
        capital = initial_capital
        position = None
        entry_price = 0
        trades = []
        
        for idx, row in self.df_signals.iterrows():
            signal = row['signal']
            close = row['close']
            
            # BUY signal
            if signal == 'BUY' and position is None:
                position = 'LONG'
                entry_price = close
                entry_time = row['timestamp']
            
            # SELL signal exits LONG
            elif signal == 'SELL' and position == 'LONG':
                pnl = close - entry_price
                pnl_pct = (pnl / entry_price) * 100 if entry_price > 0 else 0
                capital += pnl
                
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
        
        # Calculate metrics
        if trades:
            pnls = np.array([t['pnl'] for t in trades])
            winning = sum(1 for p in pnls if p > 0)
            losing = sum(1 for p in pnls if p < 0)
            
            self.report['backtest'] = {
                'trades': len(trades),
                'winning': winning,
                'losing': losing,
                'win_rate': winning / len(trades) if trades else 0,
                'total_pnl': float(pnls.sum()),
                'avg_pnl': float(pnls.mean()),
                'max_win': float(pnls.max()),
                'max_loss': float(pnls.min()),
                'final_capital': capital,
                'return_pct': ((capital - initial_capital) / initial_capital) * 100,
                'sample_trades': trades[:5],
            }
            
            print(f"  Backtest: {len(trades)} trades, WR={winning/len(trades)*100:.1f}%, P&L=${pnls.sum():.2f}")
            return True
        else:
            print(f"  ERROR: No trades generated")
            return False
    
    def compile_report(self):
        """Compile all report data"""
        self.report['metadata'] = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': datetime.utcnow().isoformat(),
            'data_candles': len(self.df),
            'features_count': len(self.df_features.columns),
            'signals_count': len(self.df_signals),
        }
        
        # Signal statistics
        signals_series = self.df_signals['signal'].value_counts()
        self.report['signals'] = {
            'buy': int(signals_series.get('BUY', 0)),
            'sell': int(signals_series.get('SELL', 0)),
            'hold': int(signals_series.get('HOLD', 0)),
            'score_mean': float(self.df_signals['score'].mean()),
            'score_std': float(self.df_signals['score'].std()),
        }
        
        # Price statistics
        closes = self.df['close'].values
        self.report['price_data'] = {
            'price_min': float(closes.min()),
            'price_max': float(closes.max()),
            'price_mean': float(closes.mean()),
            'price_range': float(closes.max() - closes.min()),
            'volatility': float(np.std(np.diff(np.log(closes)))),  # Log returns volatility
        }
        
        return True
    
    def print_report(self):
        """Print formatted report"""
        print("\n" + "=" * 90)
        print(f"  CRYPTO TRADING REPORT: {self.symbol} {self.timeframe}")
        print("=" * 90)
        
        meta = self.report.get('metadata', {})
        print(f"\n  DATA SUMMARY:")
        print(f"    Symbol:          {meta.get('symbol')}")
        print(f"    Timeframe:       {meta.get('timeframe')}")
        print(f"    Candles:         {meta.get('data_candles'):,}")
        print(f"    Features:        {meta.get('features_count')}")
        print(f"    Signals:         {meta.get('signals_count')}")
        
        signals = self.report.get('signals', {})
        print(f"\n  SIGNAL DISTRIBUTION:")
        print(f"    BUY signals:     {signals.get('buy', 0):>6} ({signals.get('buy', 0)/meta.get('signals_count', 1)*100:>5.1f}%)")
        print(f"    SELL signals:    {signals.get('sell', 0):>6} ({signals.get('sell', 0)/meta.get('signals_count', 1)*100:>5.1f}%)")
        print(f"    HOLD signals:    {signals.get('hold', 0):>6} ({signals.get('hold', 0)/meta.get('signals_count', 1)*100:>5.1f}%)")
        print(f"    Avg Score:       {signals.get('score_mean', 0):>6.4f} (+/- {signals.get('score_std', 0):.4f})")
        
        prices = self.report.get('price_data', {})
        print(f"\n  PRICE ANALYSIS:")
        print(f"    Min Price:       ${prices.get('price_min', 0):>12,.2f}")
        print(f"    Max Price:       ${prices.get('price_max', 0):>12,.2f}")
        print(f"    Mean Price:      ${prices.get('price_mean', 0):>12,.2f}")
        print(f"    Volatility:      {prices.get('volatility', 0)*100:>12.2f}%")
        
        backtest = self.report.get('backtest', {})
        if backtest:
            print(f"\n  BACKTEST RESULTS:")
            print(f"    Total Trades:    {backtest.get('trades', 0):>10}")
            print(f"    Winning Trades:  {backtest.get('winning', 0):>10}")
            print(f"    Losing Trades:   {backtest.get('losing', 0):>10}")
            print(f"    Win Rate:        {backtest.get('win_rate', 0)*100:>10.1f}%")
            print(f"    Total P&L:       ${backtest.get('total_pnl', 0):>10,.2f}")
            print(f"    Avg P&L/Trade:   ${backtest.get('avg_pnl', 0):>10,.2f}")
            print(f"    Max Win:         ${backtest.get('max_win', 0):>10,.2f}")
            print(f"    Max Loss:        ${backtest.get('max_loss', 0):>10,.2f}")
            print(f"    Final Capital:   ${backtest.get('final_capital', 0):>10,.2f}")
            print(f"    Return:          {backtest.get('return_pct', 0):>10.2f}%")
        
        print("\n" + "=" * 90)
    
    def save_report(self):
        """Save report to JSON"""
        output_file = RESULTS_DIR / f"report_{self.symbol}_{self.timeframe}.json"
        
        with open(output_file, 'w') as f:
            # Make trades serializable
            report_copy = self.report.copy()
            if 'backtest' in report_copy and 'sample_trades' in report_copy['backtest']:
                report_copy['backtest']['sample_trades_count'] = len(report_copy['backtest']['sample_trades'])
                report_copy['backtest'].pop('sample_trades')
            
            json.dump(report_copy, f, indent=2, default=str)
        
        print(f"\n  Report saved to {output_file}")

def main():
    print("=" * 90)
    print("[CRYPTO TRADING REPORT] Analysis & Backtesting")
    print("=" * 90)
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    
    for symbol in symbols:
        print(f"\n\n[{symbol}] ANALYZING {symbol}")
        print("-" * 90)
        
        reporter = CryptoTradingReport(symbol, timeframe)
        
        # Load and process
        print(f"  Loading data...")
        if not reporter.load_data():
            continue
        
        print(f"  Processing features...")
        if not reporter.compute_features():
            continue
        
        print(f"  Loading model...")
        if not reporter.load_model():
            continue
        
        # Generate signals
        if not reporter.generate_signals(threshold=0.5):
            continue
        
        # Backtest
        if not reporter.backtest_simple(initial_capital=10000.0):
            continue
        
        # Report
        reporter.compile_report()
        reporter.print_report()
        reporter.save_report()
    
    print("\n\n" + "=" * 90)
    print("[DONE] Reports generated")
    print("=" * 90)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
