"""
Script: Complexity Analysis para LightGBM
M3.1: Curvas de complejidad (n_estimators vs Sharpe OOS)

Objetivo: Encontrar el punto óptimo de n_estimators donde el modelo deja de mejorar.

Usage:
    python scripts/complexity_analysis.py --symbol BTCUSDT
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lightgbm as lgb
from core.ml.validation import PurgedKFold


def calculate_sharpe_oos(y_true: np.ndarray, y_pred: np.ndarray, periods_per_year: int = 365 * 24) -> float:
    """Calculate Sharpe ratio from predictions."""
    if len(y_pred) == 0:
        return 0.0
    returns = y_true * y_pred
    if np.std(returns) == 0:
        return 0.0
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(periods_per_year)
    return sharpe


def load_training_data(symbol: str, data_dir: Path = None) -> tuple[np.ndarray, np.ndarray]:
    """Load training data from parquet files."""
    if data_dir is None:
        data_dir = PROJECT_ROOT / "data" / "features"

    feature_file = data_dir / f"{symbol}_features.parquet"
    target_file = data_dir / f"{symbol}_target.parquet"

    if not feature_file.exists() or not target_file.exists():
        raise FileNotFoundError(f"Training data not found for {symbol}")

    df_features = pd.read_parquet(feature_file)
    df_target = pd.read_parquet(target_file)

    common_idx = df_features.index.intersection(df_target.index)
    df_features = df_features.loc[common_idx]
    df_target = df_target.loc[common_idx]

    feature_cols = [c for c in df_features.columns if c not in ('timestamp', 'symbol')]
    X = df_features[feature_cols].values
    y = df_target['target'].values

    return X, y


def run_complexity_analysis(
    symbol: str,
    n_estimators_values: list[int] = None,
    n_splits: int = 5,
    embargo_bars: int = 5,
    output_dir: Path = None,
) -> dict:
    """Run complexity analysis to find optimal n_estimators."""
    if n_estimators_values is None:
        n_estimators_values = [50, 100, 200, 300, 500, 700]

    print(f"Loading training data for {symbol}...")
    X, y = load_training_data(symbol)
    print(f"Loaded {len(X)} samples with {X.shape[1]} features")

    default_params = {
        'max_depth': 7,
        'learning_rate': 0.03,
        'num_leaves': 31,
        'min_child_samples': 30,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'random_state': 42,
        'n_jobs': -1,
        'verbose': -1,
    }

    purged_kfold = PurgedKFold(n_splits=n_splits, embargo_bars=embargo_bars)

    results = {
        'n_estimators': [],
        'sharpe_oos_mean': [],
        'sharpe_oos_std': [],
        'training_time': [],
    }

    print(f"\nTesting n_estimators: {n_estimators_values}")

    for n_est in n_estimators_values:
        print(f"\n  Testing n_estimators={n_est}...", end=" ")
        import time
        start_time = time.time()

        params = {**default_params, 'n_estimators': n_est}
        oos_sharpes = []

        for fold_idx, (train_idx, test_idx) in enumerate(purged_kfold.split(X)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                callbacks=[lgb.early_stopping(20, verbose=False)],
            )

            y_pred_proba = model.predict_proba(X_test)
            if y_pred_proba.shape[1] == 2:
                y_pred = y_pred_proba[:, 1] - y_pred_proba[:, 0]
            else:
                y_pred = y_pred_proba[:, 2] - y_pred_proba[:, 0]

            sharpe = calculate_sharpe_oos(y_test, y_pred)
            oos_sharpes.append(sharpe)

        elapsed = time.time() - start_time
        mean_sharpe = np.mean(oos_sharpes)
        std_sharpe = np.std(oos_sharpes)

        results['n_estimators'].append(n_est)
        results['sharpe_oos_mean'].append(mean_sharpe)
        results['sharpe_oos_std'].append(std_sharpe)
        results['training_time'].append(elapsed)

        print(f"Sharpe: {mean_sharpe:.4f} ± {std_sharpe:.4f} ({elapsed:.1f}s)")

    results_df = pd.DataFrame(results)

    optimal_idx = np.argmax(results_df['sharpe_oos_mean'].values)
    optimal_n_estimators = results_df['n_estimators'].iloc[optimal_idx]
    optimal_sharpe = results_df['sharpe_oos_mean'].iloc[optimal_idx]

    print(f"\n=== RESULTS ===")
    print(f"Optimal n_estimators: {optimal_n_estimators}")
    print(f"Optimal Sharpe OOS: {optimal_sharpe:.4f}")

    if output_dir is None:
        output_dir = PROJECT_ROOT / "models" / "complexity"

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results_df.to_csv(output_dir / f"complexity_curve_{symbol}_{timestamp}.csv", index=False)

    plt.figure(figsize=(10, 6))
    plt.errorbar(
        results_df['n_estimators'],
        results_df['sharpe_oos_mean'],
        yerr=results_df['sharpe_oos_std'],
        marker='o',
        capsize=5,
        linewidth=2,
        markersize=8,
    )
    plt.axvline(x=optimal_n_estimators, color='r', linestyle='--', label=f'Optimal: {optimal_n_estimators}')
    plt.xlabel('n_estimators', fontsize=12)
    plt.ylabel('Sharpe OOS', fontsize=12)
    plt.title(f'Complexity Curve - {symbol}', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / f"complexity_curve_{symbol}_{timestamp}.png", dpi=150)
    plt.close()

    summary = {
        'symbol': symbol,
        'timestamp': timestamp,
        'optimal_n_estimators': int(optimal_n_estimators),
        'optimal_sharpe_oos': float(optimal_sharpe),
        'all_results': results,
    }

    with open(output_dir / f"optimal_n_estimators_{symbol}_latest.json", 'w') as f:
        json.dump(summary, f, indent=2, default=float)

    print(f"\nResults saved to {output_dir}")
    return summary


def main():
    parser = argparse.ArgumentParser(description='Complexity Analysis for LightGBM')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Symbol to analyze')
    parser.add_argument('--n-splits', type=int, default=5, help='Number of CV splits')
    parser.add_argument('--embargo-bars', type=int, default=5, help='Embargo bars for PurgedKFold')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory')

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None

    results = run_complexity_analysis(
        symbol=args.symbol,
        n_splits=args.n_splits,
        embargo_bars=args.embargo_bars,
        output_dir=output_dir,
    )

    print("\n=== SUMMARY ===")
    print(f"Symbol: {results['symbol']}")
    print(f"Optimal n_estimators: {results['optimal_n_estimators']}")
    print(f"Optimal Sharpe OOS: {results['optimal_sharpe_oos']:.4f}")


if __name__ == '__main__':
    main()