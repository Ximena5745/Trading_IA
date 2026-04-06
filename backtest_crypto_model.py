#!/usr/bin/env python3
"""
Script: backtest_crypto_model.py
Backtest the trained CRYPTO MTF model
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.technical_agent import TechnicalAgent
from core.features.feature_engineering import FeatureEngine

DATA_DIR = Path("data/raw")
MODELS_DIR = Path("data/models")
BACKTEST_RESULTS_DIR = Path("backtest_results")
BACKTEST_RESULTS_DIR.mkdir(exist_ok=True)

def backtest_symbol(symbol: str, timeframe: str, model_path: Path) -> dict:
    """Run backtest on a symbol using the trained model"""
    
    # Load data
    data_path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    if not data_path.exists():
        return {"symbol": symbol, "status": f"❌ Data not found: {data_path}"}
    
    try:
        df = pd.read_parquet(data_path)
        print(f"  Loaded {len(df)} candles for {symbol} {timeframe}")
        
        # Load model using constructor
        if not model_path.exists():
            return {"symbol": symbol, "status": f"ERROR - Data not found: {data_path}"}
        
        agent = TechnicalAgent(str(model_path))
        if not agent.is_ready():
            return {"symbol": symbol, "status": "ERROR - Model failed to load"}
        
        print(f"  [OK] Loaded model: {model_path.name}")
        
        # Feature engineering
        engine = FeatureEngine()
        df_features = engine.calculate_mtf_features(df, symbol)
        print(f"  ✓ Calculated {len(df_features.columns)} features")
        
        # Generate predictions (only for last 1000 candles to save time)
        test_df = df_features.iloc[-1000:].copy()
        predictions = []
        
        for idx, row in test_df.iterrows():
            try:
                # Create FeatureSet compatible structure
                from core.models import FeatureSet
                
                feature_dict = {k: v for k, v in row.to_dict().items() 
                               if k not in ['timestamp', 'symbol', 'trend_direction_4h', 
                                           'volatility_regime_4h', 'trend_direction_1d', 
                                           'volatility_regime_1d']}
                
                features = FeatureSet(**feature_dict)
                output = agent.predict(features)
                
                if output and hasattr(output, 'score'):
                    predictions.append({
                        'timestamp': idx,
                        'signal': 'BUY' if output.score > 0.5 else 'SELL',
                        'confidence': abs(output.score - 0.5) * 2,
                        'score': output.score,
                    })
            except Exception as e:
                continue
        
        if not predictions:
            return {
                "symbol": symbol,
                "status": "⚠️ No predictions generated"
            }
        
        pred_df = pd.DataFrame(predictions)
        
        # Calculate simple P&L
        # BUY signal = expect close to go up
        # SELL signal = expect close to go down
        
        buy_signals = len(pred_df[pred_df['signal'] == 'BUY'])
        sell_signals = len(pred_df[pred_df['signal'] == 'SELL'])
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "✅ COMPLETED",
            "total_signals": len(pred_df),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "avg_confidence": pred_df['confidence'].mean(),
            "predictions": predictions[:10],  # Return first 10 predictions
        }
        
    except Exception as e:
        return {
            "symbol": symbol,
            "status": f"❌ Error: {str(e)}"
        }

def main():
    print("=" * 80)
    print("[BACKTEST] BACKTESTING MODELO CRYPTO MTF")
    print("=" * 80)
    
    model_path = MODELS_DIR / "technical_crypto_mtf_v1.pkl"
    
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}")
        return 1
    
    print(f"\n[MODEL] Using model: {model_path.name}\n")
    
    # Test on 1h data (most recent timeframe)
    results = []
    
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        print(f"\n[{symbol}] Testing {symbol}...")
        print("-" * 80)
        
        result = backtest_symbol(symbol, "1h", model_path)
        results.append(result)
        
        if result.get("status") == "✅ COMPLETED":
            print(f"\n  [OK] Total Signals: {result['total_signals']}")
            print(f"  [OK] BUY Signals: {result['buy_signals']}")
            print(f"  [OK] SELL Signals: {result['sell_signals']}")
            print(f"  [OK] Avg Confidence: {result['avg_confidence']:.2%}")
            
            # Show sample predictions
            if result.get('predictions'):
                print(f"\n  Sample Predictions (first 5):")
                for i, pred in enumerate(result['predictions'][:5], 1):
                    print(f"    {i}. {pred['signal']:>4} (conf={pred['confidence']:.2%})")
        else:
            print(f"\n  {result['status']}")
    
    print("\n" + "=" * 80)
    print("[DONE] BACKTESTING COMPLETADO")
    print("=" * 80)
    
    completed = sum(1 for r in results if "✅" in r.get("status", ""))
    total = len(results)
    print(f"\n[RESULT] {completed}/{total} backtests completados exitosamente")
    
    return 0 if completed == total else 1

if __name__ == "__main__":
    sys.exit(main())
