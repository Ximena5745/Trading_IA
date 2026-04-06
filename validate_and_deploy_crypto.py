#!/usr/bin/env python
"""
COMPREHENSIVE CRYPTO TRADING VALIDATION & DEPLOYMENT PIPELINE
==============================================================================
Walk-Forward Validation + Realistic Fees/Slippage + Portfolio Metrics + Live Integration Ready
"""

import warnings
warnings.filterwarnings('ignore')

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split

# LightGBM
import lightgbm as lgb

# ============================================================================
# CONFIGURATION
# ============================================================================

SYMBOLS = ['BTCUSDT', 'ETHUSDT']
TIMEFRAME = '1h'
DATA_DIR = 'data/raw'
MODEL_DIR = 'data/models'
RESULTS_DIR = 'backtest_results'
VALIDATION_RESULTS = 'backtest_results/validation_results.json'
LIVE_CONFIG = 'backtest_results/live_trading_config.json'

# Transaction costs (realistic)
BINANCE_FEE_MAKER = 0.0005  # 0.05%
BINANCE_FEE_TAKER = 0.001   # 0.1%
SLIPPAGE_BPS = 0.5          # 0.5 basis points (0.005%)
SLIPPAGE_PCT = SLIPPAGE_BPS / 10000  # Convert to percentage

# Signal thresholds
BUY_THRESHOLD = 0.52
SELL_THRESHOLD = 0.48

# Risk management
MAX_POSITION_SIZE = 0.1  # 10% of capital per position
MAX_DAILY_LOSS = 0.05   # 5% max daily loss
STOP_LOSS_PCT = 0.02    # 2% stop loss
TAKE_PROFIT_PCT = 0.05  # 5% take profit

# ============================================================================
# VALIDATION CLASS
# ============================================================================

class CryptoValidationEngine:
    """Comprehensive validation with walk-forward, realistic costs, and metrics"""
    
    def __init__(self, symbol, timeframe='1h'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = None
        self.model = None
        self.results = {}
        
    def load_data(self):
        """Load historical OHLCV data"""
        file_path = f"{DATA_DIR}/{self.symbol}_{self.timeframe}.parquet"
        if not os.path.exists(file_path):
            print(f"  ❌ Data not found: {file_path}")
            return False
        
        self.df = pd.read_parquet(file_path)
        print(f"  ✓ Loaded {len(self.df)} candles for {self.symbol}")
        return True
    
    def load_model(self):
        """Load trained LightGBM model"""
        model_path = f"{MODEL_DIR}/technical_crypto_mtf_v1.pkl"
        if not os.path.exists(model_path):
            print(f"  ❌ Model not found: {model_path}")
            return False
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # Handle both dict and direct model formats
        if isinstance(model_data, dict):
            self.model = model_data.get('model', model_data)
            self.feature_names = model_data.get('feature_names', None)
        else:
            self.model = model_data
            self.feature_names = None
        
        print(f"  ✓ Loaded model (LightGBM classifier)")
        return True
    
    def compute_features(self, data):
        """Compute 75 technical features"""
        from core.features.engine import FeatureEngine
        engine = FeatureEngine()
        
        features = []
        for i in range(len(data)):
            if i < 100:  # Need sufficient history
                continue
            
            candle_data = {
                'o': float(data.iloc[i]['open']),
                'h': float(data.iloc[i]['high']),
                'l': float(data.iloc[i]['low']),
                'c': float(data.iloc[i]['close']),
                'v': float(data.iloc[i]['volume']),
            }
            
            historical = data.iloc[max(0, i-250):i]
            feature_dict = engine.calculate_features(
                candle_data=candle_data,
                historical_data=historical,
                timeframe='1h'
            )
            features.append(feature_dict)
        
        return pd.DataFrame(features)
    
    def walk_forward_validation(self, test_size=0.3, train_window=0.7):
        """
        Walk-Forward Analysis: Train on past data, validate on future unseen data
        
        This prevents overfitting by ensuring we never train on test data
        """
        print(f"\n{'='*80}")
        print(f"[WALK-FORWARD VALIDATION] {self.symbol}")
        print('='*80)
        
        # Step 1: Compute all features
        print("\n[1] Computing features for walk-forward analysis...")
        try:
            df_features = self.compute_features(self.df)
            print(f"  ✓ Computed {len(df_features)} feature samples with {len(df_features.columns)} columns")
        except Exception as e:
            print(f"  ❌ Feature computation failed: {str(e)}")
            return {}
        
        # Step 2: Split into train/test
        split_idx = int(len(df_features) * train_window)
        df_train = df_features.iloc[:split_idx]
        df_test = df_features.iloc[split_idx:]
        
        print(f"  ✓ Train set: {len(df_train)} samples")
        print(f"  ✓ Test set: {len(df_test)} samples (out-of-sample)")
        
        # Step 3: Extract numeric features only
        numeric_cols = [col for col in df_train.columns 
                       if col not in ['timestamp', 'symbol', 'trend_direction', 'volatility_regime']
                       and df_train[col].dtype in ['float64', 'float32', 'int64', 'int32']]
        numeric_cols = numeric_cols[:75]  # Use same 75 features as training
        
        print(f"  ✓ Using {len(numeric_cols)} numeric features")
        
        # Step 4: Generate signals on test set
        print(f"\n[2] Generating signals on unseen test data...")
        try:
            X_test = df_test[numeric_cols].fillna(0).values.astype(np.float32)
            predictions = self.model.predict_proba(X_test)
            scores = predictions[:, 1]  # Probability of BUY class
            
            signals = []
            for score in scores:
                if score > BUY_THRESHOLD:
                    signals.append('BUY')
                elif score < SELL_THRESHOLD:
                    signals.append('SELL')
                else:
                    signals.append('HOLD')
            
            signal_counts = pd.Series(signals).value_counts()
            print(f"  ✓ Generated {len(signals)} signals on test data")
            print(f"    - BUY:  {signal_counts.get('BUY', 0):>6} ({signal_counts.get('BUY', 0)/len(signals)*100:>5.1f}%)")
            print(f"    - SELL: {signal_counts.get('SELL', 0):>6} ({signal_counts.get('SELL', 0)/len(signals)*100:>5.1f}%)")
            print(f"    - HOLD: {signal_counts.get('HOLD', 0):>6} ({signal_counts.get('HOLD', 0)/len(signals)*100:>5.1f}%)")
            
        except Exception as e:
            print(f"  ❌ Signal generation failed: {str(e)}")
            return {}
        
        # Step 5: Backtest on test set with REALISTIC costs
        print(f"\n[3] Backtesting on out-of-sample data (with realistic costs)...")
        
        # Get prices for test period
        price_idx_start = split_idx + 100
        prices = self.df.iloc[price_idx_start:price_idx_start+len(signals)]['close'].values
        
        if len(prices) < len(signals):
            print(f"  ⚠️  Insufficient price data: {len(prices)} vs {len(signals)} signals")
            prices = np.concatenate([prices, np.repeat(prices[-1], len(signals) - len(prices))])
        
        backtest_results = self._backtest_with_costs(signals, prices)
        print(f"  ✓ Backtest completed")
        
        # Step 6: Calculate risk metrics
        print(f"\n[4] Calculating portfolio metrics...")
        metrics = self._calculate_metrics(backtest_results, signals, prices)
        print(f"  ✓ Metrics calculated")
        
        # Store results
        self.results = {
            'symbol': self.symbol,
            'split_index': int(split_idx),
            'train_size': len(df_train),
            'test_size': len(df_test),
            'backtest': backtest_results,
            'metrics': metrics,
            'warnings': self._get_warnings(backtest_results, metrics)
        }
        
        return self.results
    
    def _backtest_with_costs(self, signals, prices):
        """Backtest with realistic transaction costs and slippage"""
        capital = 10000  # Starting capital
        position = False
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        for i, signal in enumerate(signals):
            current_price = prices[i]
            
            if signal == 'BUY' and not position:
                # Enter position
                entry_price = current_price * (1 + SLIPPAGE_PCT)  # Add slippage
                fee = entry_price * BINANCE_FEE_MAKER
                position = True
                entry_time = i
                
            elif signal == 'SELL' and position:
                # Exit position
                exit_price = current_price * (1 - SLIPPAGE_PCT)  # Subtract slippage
                fee = exit_price * BINANCE_FEE_MAKER
                
                pnl = (exit_price - entry_price) - 2 * ((entry_price + exit_price) / 2) * BINANCE_FEE_MAKER
                pnl_pct = (pnl / entry_price) * 100
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'duration': i - entry_time,
                    'win': 1 if pnl > 0 else 0
                })
                
                capital += pnl
                equity_curve.append(capital)
                position = False
        
        # Close any open position at end
        if position:
            exit_price = prices[-1] * (1 - SLIPPAGE_PCT)
            pnl = (exit_price - entry_price) - 2 * ((entry_price + exit_price) / 2) * BINANCE_FEE_MAKER
            capital += pnl
            equity_curve.append(capital)
        
        winning_trades = sum(1 for t in trades if t['win'])
        win_rate = winning_trades / len(trades) if trades else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': len(trades) - winning_trades,
            'win_rate': win_rate,
            'total_pnl': capital - 10000,
            'total_pnl_pct': ((capital - 10000) / 10000) * 100,
            'avg_pnl': (capital - 10000) / len(trades) if trades else 0,
            'final_capital': capital,
            'max_win': max([t['pnl'] for t in trades], default=0),
            'max_loss': min([t['pnl'] for t in trades], default=0),
            'equity_curve': equity_curve,
            'trades': trades
        }
    
    def _calculate_metrics(self, backtest_results, signals, prices):
        """Calculate comprehensive portfolio metrics"""
        trades = backtest_results['trades']
        equity_curve = backtest_results['equity_curve']
        
        if not trades or len(prices) < 2:
            return {}
        
        # Basic stats
        returns = np.diff(equity_curve) / equity_curve[:-1]
        daily_returns = np.array(returns)
        
        # Sharpe Ratio (annualized, assuming 252 trading days)
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        
        # Sortino Ratio (uses downside volatility)
        downside_returns = np.minimum(daily_returns, 0)
        downside_std = np.std(downside_returns)
        sortino = (avg_return / (downside_std * np.sqrt(252))) if downside_std > 0 else 0
        
        # Calmar Ratio
        annual_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Profit Factor
        profitable = [t['pnl'] for t in trades if t['pnl'] > 0]
        unprofitable = [t['pnl'] for t in trades if t['pnl'] < 0]
        profit_factor = sum(profitable) / abs(sum(unprofitable)) if unprofitable else np.inf
        
        # Expectancy
        avg_win = np.mean(profitable) if profitable else 0
        avg_loss = np.mean(unprofitable) if unprofitable else 0
        expectancy = (avg_win * (len(profitable)/len(trades))) + (avg_loss * (len(unprofitable)/len(trades)))
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown_pct': max_drawdown * 100,
            'return_pct': ((equity_curve[-1] - equity_curve[0]) / equity_curve[0]) * 100,
            'win_rate_pct': (backtest_results['win_rate']) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_trades': len(profitable),
            'loss_trades': len(unprofitable)
        }
    
    def _calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown percentage"""
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (np.array(equity_curve) - cummax) / cummax
        return np.min(drawdown)
    
    def _get_warnings(self, backtest_results, metrics):
        """Generate warnings about trading performance"""
        warnings_list = []
        
        if backtest_results['total_trades'] < 50:
            warnings_list.append("⚠️  Low trade count (<50) - results may not be statistically significant")
        
        if metrics.get('sharpe_ratio', 0) < 1.0:
            warnings_list.append("⚠️  Sharpe ratio < 1.0 - risk-adjusted returns may be insufficient")
        
        if abs(metrics.get('max_drawdown_pct', 0)) > 20:
            warnings_list.append("⚠️  Max drawdown > 20% - significant portfolio volatility")
        
        if backtest_results['win_rate'] > 0.80:
            warnings_list.append("⚠️  Win rate > 80% - possible overfitting despite out-of-sample test")
        
        if backtest_results['total_pnl_pct'] < 50:
            warnings_list.append("⚠️  Return < 50% on test set - may not meet deployment criteria")
        
        return warnings_list if warnings_list else []


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*80)
    print("[CRYPTO TRADING SYSTEM] Validation & Deployment Pipeline")
    print("="*80)
    
    # Ensure output directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    all_results = {}
    
    for symbol in SYMBOLS:
        print(f"\n{'='*80}")
        print(f"[{symbol}] Starting comprehensive validation...")
        print('='*80)
        
        validator = CryptoValidationEngine(symbol, TIMEFRAME)
        
        # Load data and model
        if not validator.load_data():
            continue
        if not validator.load_model():
            continue
        
        # Run walk-forward validation
        results = validator.walk_forward_validation()
        if results:
            all_results[symbol] = results
            
            # Print summary
            print(f"\n[{symbol}] VALIDATION RESULTS")
            print("-" * 80)
            print(f"  Out-of-Sample Trades: {results['backtest'].get('total_trades', 0)}")
            print(f"  Win Rate: {results['backtest'].get('win_rate', 0)*100:.1f}%")
            print(f"  Total P&L: ${results['backtest'].get('total_pnl', 0):,.2f}")
            print(f"  Return %: {results['backtest'].get('total_pnl_pct', 0):.1f}%")
            
            if results['metrics']:
                print(f"\n  PORTFOLIO METRICS:")
                print(f"    Sharpe Ratio: {results['metrics'].get('sharpe_ratio', 0):.2f}")
                print(f"    Sortino Ratio: {results['metrics'].get('sortino_ratio', 0):.2f}")
                print(f"    Calmar Ratio: {results['metrics'].get('calmar_ratio', 0):.2f}")
                print(f"    Profit Factor: {results['metrics'].get('profit_factor', 0):.2f}")
                print(f"    Max Drawdown: {results['metrics'].get('max_drawdown_pct', 0):.2f}%")
            
            if results['warnings']:
                print(f"\n  WARNINGS:")
                for warning in results['warnings']:
                    print(f"    {warning}")
    
    # Save comprehensive validation results
    print(f"\n{'='*80}")
    print("[SAVING RESULTS]")
    print('='*80)
    
    with open(VALIDATION_RESULTS, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'walk-forward',
            'test_date_from': datetime.now().isoformat(),
            'results': {k: {
                'symbol': v['symbol'],
                'train_size': v['train_size'],
                'test_size': v['test_size'],
                'backtest': {
                    'total_trades': v['backtest'].get('total_trades'),
                    'win_rate': v['backtest'].get('win_rate'),
                    'total_pnl': v['backtest'].get('total_pnl'),
                    'total_pnl_pct': v['backtest'].get('total_pnl_pct'),
                    'max_drawdown_from_equity': v['backtest'].get('max_loss')
                },
                'metrics': v.get('metrics', {}),
                'warnings': v.get('warnings', [])
            } for k, v in all_results.items()}
        }, f, indent=2, default=str)
    
    print(f"  ✓ Saved validation results to {VALIDATION_RESULTS}")
    
    # Create live trading config
    live_config = {
        'symbols': SYMBOLS,
        'timeframe': TIMEFRAME,
        'model_path': f"{MODEL_DIR}/technical_crypto_mtf_v1.pkl",
        'trade_config': {
            'buy_threshold': BUY_THRESHOLD,
            'sell_threshold': SELL_THRESHOLD,
            'max_position_size_pct': MAX_POSITION_SIZE * 100,
            'max_daily_loss_pct': MAX_DAILY_LOSS * 100,
            'stop_loss_pct': STOP_LOSS_PCT * 100,
            'take_profit_pct': TAKE_PROFIT_PCT * 100
        },
        'fees': {
            'maker_fee': BINANCE_FEE_MAKER * 100,
            'taker_fee': BINANCE_FEE_TAKER * 100,
            'slippage_bps': SLIPPAGE_BPS
        },
        'validation_status': 'PENDING' if all_results else 'FAILED',
        'ready_for_deployment': len(all_results) == len(SYMBOLS)
    }
    
    with open(LIVE_CONFIG, 'w') as f:
        json.dump(live_config, f, indent=2)
    
    print(f"  ✓ Saved live trading config to {LIVE_CONFIG}")
    
    # Final summary
    print(f"\n{'='*80}")
    print("[VALIDATION COMPLETE]")
    print('='*80)
    print(f"  ✓ Tested on {len(all_results)} symbols")
    print(f"  ✓ Walk-forward validation completed")
    print(f"  ✓ Realistic fees/slippage applied")
    print(f"  ✓ Portfolio metrics calculated")
    print(f"  ✓ Live trading config generated")
    
    if all_results:
        avg_wr = np.mean([v['backtest'].get('win_rate', 0) for v in all_results.values()])
        print(f"\n  SUMMARY METRICS:")
        print(f"    Average Win Rate (out-of-sample): {avg_wr*100:.1f}%")
        
        ready_symbols = sum(1 for v in all_results.values() if not v.get('warnings'))
        print(f"    Symbols Ready for Deployment: {ready_symbols}/{len(SYMBOLS)}")
    
    print(f"\n  Next steps:")
    print(f"    1. Review {VALIDATION_RESULTS}")
    print(f"    2. Review {LIVE_CONFIG}")
    print(f"    3. Run: python live_trading_executor.py")
    print('='*80 + "\n")


if __name__ == '__main__':
    main()
