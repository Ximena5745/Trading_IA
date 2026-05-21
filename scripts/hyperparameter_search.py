"""
Script: Bayesian Hyperparameter Search para TechnicalAgent
M3.1: Bayesian HP Search (Optuna)

Objetivo: Encontrar mejores hiperparámetros para LightGBM usando Bayesian Optimization.
Métrica objetivo: Sharpe OOS (no accuracy).

Usage:
    python scripts/hyperparameter_search.py --symbol BTCUSDT --n-trials 50
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import optuna
from optuna.samplers import TPESampler

import lightgbm as lgb
from core.ml.validation import PurgedKFold
from core.backtesting.metrics import sharpe_ratio


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


def objective(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
    embargo_bars: int = 5,
) -> float:
    """Objective function for Optuna: maximize Sharpe OOS."""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 700),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 15, 127),
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'random_state': 42,
        'n_jobs': -1,
        'verbose': -1,
    }

    purged_kfold = PurgedKFold(n_splits=n_splits, embargo_bars=embargo_bars)
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

        trial.report(np.mean(oos_sharpes), fold_idx)

        if trial.should_prune():
            raise optuna.TrialPruned()

    mean_sharpe = np.mean(oos_sharpes)
    return mean_sharpe


def run_hyperparameter_search(
    symbol: str,
    n_trials: int = 50,
    n_splits: int = 5,
    embargo_bars: int = 5,
    output_dir: Path = None,
) -> dict:
    """Run Bayesian hyperparameter search."""
    print(f"Loading training data for {symbol}...")
    X, y = load_training_data(symbol)
    print(f"Loaded {len(X)} samples with {X.shape[1]} features")

    sampler = TPESampler(seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.set_metric_names(['sharpe_oos'])

    print(f"Starting hyperparameter search with {n_trials} trials...")
    study.optimize(
        lambda trial: objective(trial, X, y, n_splits, embargo_bars),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    best_params = study.best_params
    best_sharpe = study.best_value

    print(f"\nBest Sharpe OOS: {best_sharpe:.4f}")
    print(f"Best params: {best_params}")

    if output_dir is None:
        output_dir = PROJECT_ROOT / "models" / "hyperopt"

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        'symbol': symbol,
        'timestamp': timestamp,
        'best_sharpe_oos': best_sharpe,
        'best_params': best_params,
        'n_trials': n_trials,
        'study_best_value': study.best_value,
        'study_best_params': study.best_params,
    }

    results_file = output_dir / f"best_params_{symbol}_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    latest_link = output_dir / f"best_params_{symbol}_latest.json"
    with open(latest_link, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {results_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Bayesian Hyperparameter Search for TechnicalAgent')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Symbol to optimize')
    parser.add_argument('--n-trials', type=int, default=50, help='Number of Optuna trials')
    parser.add_argument('--n-splits', type=int, default=5, help='Number of CV splits')
    parser.add_argument('--embargo-bars', type=int, default=5, help='Embargo bars for PurgedKFold')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory')

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None

    results = run_hyperparameter_search(
        symbol=args.symbol,
        n_trials=args.n_trials,
        n_splits=args.n_splits,
        embargo_bars=args.embargo_bars,
        output_dir=output_dir,
    )

    print("\n=== SUMMARY ===")
    print(f"Symbol: {results['symbol']}")
    print(f"Best Sharpe OOS: {results['best_sharpe_oos']:.4f}")
    print(f"Best Parameters: {results['best_params']}")


if __name__ == '__main__':
    main()