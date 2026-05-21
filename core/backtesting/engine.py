"""
Module: core/backtesting/engine.py
Responsibility: Walk-forward backtesting engine with realistic costs
Dependencies: metrics, costs, feature_engineering, signal_engine, logger
"""
from __future__ import annotations

import pandas as pd

from core.backtesting.costs import CostModel
from core.backtesting.metrics import compute_all
from core.config.constants import HARD_LIMITS, MIN_CANDLES_BACKTEST
from core.exceptions import BacktestError
from core.features.feature_engineering import FeatureEngine
from core.observability.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TRAIN_SIZE = 500
DEFAULT_TEST_SIZE = 100
DEFAULT_STEP_SIZE = 50
MIN_SHARPE = 1.0
MIN_SORTINO = 1.5
MAX_DRAWDOWN_THRESHOLD = 0.20


class BacktestEngine:
    def __init__(self, cost_model: CostModel | None = None):
        self._costs = cost_model or CostModel()
        self._feature_engine = FeatureEngine()

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        strategy_fn,
        train_size: int = DEFAULT_TRAIN_SIZE,
        test_size: int = DEFAULT_TEST_SIZE,
        step_size: int = DEFAULT_STEP_SIZE,
        initial_capital: float = 10000.0,
    ) -> dict:
        if len(df) < MIN_CANDLES_BACKTEST:
            raise BacktestError(
                f"Need at least {MIN_CANDLES_BACKTEST} candles, got {len(df)}"
            )

        all_trades: list[dict] = []
        equity_curve: list[float] = [initial_capital]
        window_results: list[dict] = []
        capital = initial_capital

        windows = list(self._rolling_windows(df, train_size, test_size, step_size))
        logger.info(
            "backtest_started", windows=len(windows), symbol=df["symbol"].iloc[0]
        )

        for i, (train_df, test_df) in enumerate(windows):
            window_trades = self._simulate_period(test_df, strategy_fn, capital)
            for t in window_trades:
                t = self._costs.apply(t)
                capital += t["net_pnl"]
                equity_curve.append(capital)
            all_trades.extend(window_trades)

            if window_trades:
                w_metrics = compute_all(
                    window_trades,
                    [initial_capital] + [t.get("net_pnl", 0) for t in window_trades],
                )
                window_results.append(
                    {"window": i, "trades": len(window_trades), **w_metrics}
                )

        aggregate = compute_all(all_trades, equity_curve)
        aggregate["windows"] = window_results
        aggregate["final_capital"] = round(capital, 2)
        aggregate["initial_capital"] = initial_capital

        self._log_result(aggregate)
        return aggregate

    def passes_thresholds(self, metrics: dict) -> bool:
        """Return True if metrics meet minimum requirements for strategy activation."""
        return (
            metrics.get("sharpe_ratio", 0) >= MIN_SHARPE
            and metrics.get("sortino_ratio", 0) >= MIN_SORTINO
            and metrics.get("max_drawdown", 1) <= MAX_DRAWDOWN_THRESHOLD
            and metrics.get("win_rate", 0) >= 0.45
            and metrics.get("profit_factor", 0) >= 1.3
        )

    def _simulate_period(
        self, test_df: pd.DataFrame, strategy_fn, capital: float
    ) -> list[dict]:
        trades = []
        try:
            features_list = self._feature_engine.calculate_batch(test_df)
        except Exception as e:
            logger.warning("backtest_feature_error", error=str(e))
            return trades

        position = None
        for features in features_list:
            if position is not None:
                close = features.close
                hit = self._check_exit(position, close)
                if hit:
                    gross_pnl = self._calc_pnl(position, close)
                    trades.append(
                        {
                            "entry_price": position["entry"],
                            "exit_price": close,
                            "side": position["side"],
                            "quantity": position["qty"],
                            "value": position["entry"] * position["qty"],
                            "gross_pnl": gross_pnl,
                            "net_pnl": gross_pnl,
                        }
                    )
                    position = None
                    continue

            if position is None:
                signal = strategy_fn(features)
                if signal and signal.get("action") in ("BUY", "SELL"):
                    risk_pct = HARD_LIMITS["max_risk_per_trade_pct"]
                    price_risk = abs(signal["entry_price"] - signal["stop_loss"])
                    qty = (capital * risk_pct / price_risk) if price_risk > 0 else 0
                    if qty > 0:
                        position = {
                            "side": signal["action"],
                            "entry": signal["entry_price"],
                            "sl": signal["stop_loss"],
                            "tp": signal["take_profit"],
                            "qty": qty,
                        }
        return trades

    def _check_exit(self, position: dict, current_price: float) -> bool:
        if position["side"] == "BUY":
            return current_price <= position["sl"] or current_price >= position["tp"]
        return current_price >= position["sl"] or current_price <= position["tp"]

    def _calc_pnl(self, position: dict, exit_price: float) -> float:
        if position["side"] == "BUY":
            return (exit_price - position["entry"]) * position["qty"]
        return (position["entry"] - exit_price) * position["qty"]

    @staticmethod
    def _rolling_windows(df, train_size, test_size, step_size):
        start = train_size
        while start + test_size <= len(df):
            train = df.iloc[start - train_size : start]
            test = df.iloc[start : start + test_size]
            yield train, test
            start += step_size

    def _log_result(self, metrics: dict) -> None:
        passed = self.passes_thresholds(metrics)
        logger.info(
            "backtest_complete",
            sharpe=metrics.get("sharpe_ratio"),
            sortino=metrics.get("sortino_ratio"),
            max_dd=metrics.get("max_drawdown"),
            win_rate=metrics.get("win_rate"),
            total_trades=metrics.get("total_trades"),
            passes_thresholds=passed,
        )

    # QWQ-10: Walk-forward con reentrenamiento real en cada ventana
    def run_walk_forward_with_retrain(
        self,
        df: pd.DataFrame,
        train_fn,  # Function: (X_train, y_train) -> trained_model
        predict_fn,  # Function: (model, X_test) -> predictions
        get_features_fn,  # Function: (df) -> (X, y) tuple
        train_size: int = DEFAULT_TRAIN_SIZE,
        test_size: int = DEFAULT_TEST_SIZE,
        step_size: int = DEFAULT_STEP_SIZE,
        initial_capital: float = 10000.0,
    ) -> dict:
        """
        QWQ-10: Walk-forward con reentrenamiento real en cada ventana.

        Diferencia vs run_walk_forward:
        - run_walk_forward: usa la misma estrategia/función en todas las ventanas
        - run_walk_forward_with_retrain: entrena un nuevo modelo en cada ventana

        Args:
            df: DataFrame con datos OHLCV
            train_fn: Función que recibe (X_train, y_train) y devuelve un modelo entrenado
            predict_fn: Función que recibe (modelo, X_test) y devuelve predicciones
            get_features_fn: Función que recibe df y devuelve (X, y) con features listas
            train_size: Número de barras para entrenamiento
            test_size: Número de barras para test
            step_size: Paso entre ventanas
            initial_capital: Capital inicial

        Returns:
            Dict con métricas agregadas + métricas por ventana + modelos entrenados
        """
        if len(df) < MIN_CANDLES_BACKTEST:
            raise BacktestError(
                f"Need at least {MIN_CANDLES_BACKTEST} candles, got {len(df)}"
            )

        all_trades: list[dict] = []
        equity_curve: list[float] = [initial_capital]
        window_results: list[dict] = []
        trained_models: list = []
        capital = initial_capital

        windows = list(self._rolling_windows(df, train_size, test_size, step_size))
        logger.info(
            "walk_forward_retrain_started",
            windows=len(windows),
            symbol=df["symbol"].iloc[0] if "symbol" in df.columns else "unknown"
        )

        for i, (train_df, test_df) in enumerate(windows):
            try:
                X_train, y_train = get_features_fn(train_df)
                X_test, y_test = get_features_fn(test_df)

                if len(X_train) < 50 or len(X_test) < 10:
                    logger.warning(
                        "walk_forward_window_skipped",
                        window=i,
                        train_size=len(X_train),
                        test_size=len(X_test),
                    )
                    continue

                model = train_fn(X_train, y_train)
                trained_models.append(model)

                predictions = predict_fn(model, X_test)

                window_trades = self._simulate_with_predictions(
                    test_df, predictions, y_test, capital
                )

                for t in window_trades:
                    t = self._costs.apply(t)
                    capital += t["net_pnl"]
                    equity_curve.append(capital)
                all_trades.extend(window_trades)

                if window_trades:
                    w_metrics = compute_all(
                        window_trades,
                        [initial_capital] + [t.get("net_pnl", 0) for t in window_trades],
                    )
                    window_results.append(
                        {
                            "window": i,
                            "trades": len(window_trades),
                            "train_size": len(X_train),
                            "test_size": len(X_test),
                            "sharpe_oos": w_metrics.get("sharpe_ratio", 0),
                            "sortino_oos": w_metrics.get("sortino_ratio", 0),
                            "max_drawdown_oos": w_metrics.get("max_drawdown", 0),
                            "win_rate_oos": w_metrics.get("win_rate", 0),
                        }
                    )
                    logger.info(
                        "walk_forward_window_complete",
                        window=i,
                        sharpe=w_metrics.get("sharpe_ratio"),
                        trades=len(window_trades),
                    )

            except Exception as e:
                logger.warning(
                    "walk_forward_window_error",
                    window=i,
                    error=str(e),
                )
                continue

        aggregate = compute_all(all_trades, equity_curve)
        aggregate["windows"] = window_results
        aggregate["final_capital"] = round(capital, 2)
        aggregate["initial_capital"] = initial_capital
        aggregate["num_windows"] = len(window_results)
        aggregate["num_models"] = len(trained_models)

        # Calcular métricas de walk-forward
        if window_results:
            sharpes = [w["sharpe_oos"] for w in window_results if w["sharpe_oos"] is not None]
            aggregate["avg_sharpe_oos"] = round(sum(sharpes) / len(sharpes), 3) if sharpes else 0
            aggregate["min_sharpe_oos"] = round(min(sharpes), 3) if sharpes else 0
            aggregate["max_sharpe_oos"] = round(max(sharpes), 3) if sharpes else 0

        self._log_walk_forward_retrain_result(aggregate)
        return aggregate

    def _simulate_with_predictions(
        self,
        test_df: pd.DataFrame,
        predictions: list,
        y_true: list,
        capital: float
    ) -> list[dict]:
        """Simula trading usando predicciones del modelo."""
        trades = []
        position = None
        prediction_idx = 0

        try:
            features_list = self._feature_engine.calculate_batch(test_df)
        except Exception as e:
            logger.warning("backtest_feature_error", error=str(e))
            return trades

        for features in features_list:
            if position is not None:
                close = features.close
                hit = self._check_exit(position, close)
                if hit:
                    gross_pnl = self._calc_pnl(position, close)
                    trades.append(
                        {
                            "entry_price": position["entry"],
                            "exit_price": close,
                            "side": position["side"],
                            "quantity": position["qty"],
                            "value": position["entry"] * position["qty"],
                            "gross_pnl": gross_pnl,
                            "net_pnl": gross_pnl,
                        }
                    )
                    position = None
                    continue

            if position is None and prediction_idx < len(predictions):
                pred = predictions[prediction_idx]
                prediction_idx += 1

                # pred puede ser 0, 1, 2 (sell, hold, buy) o probabilidad
                if isinstance(pred, (int, float)):
                    if pred == 2 or (isinstance(pred, float) and pred > 0.6):
                        action = "BUY"
                    elif pred == 0 or (isinstance(pred, float) and pred < 0.4):
                        action = "SELL"
                    else:
                        continue
                else:
                    continue

                # Generar señal básica
                signal = {
                    "action": action,
                    "entry_price": features.close,
                    "stop_loss": features.close * 0.98 if action == "BUY" else features.close * 1.02,
                    "take_profit": features.close * 1.04 if action == "BUY" else features.close * 0.96,
                }

                risk_pct = HARD_LIMITS["max_risk_per_trade_pct"]
                price_risk = abs(signal["entry_price"] - signal["stop_loss"])
                qty = (capital * risk_pct / price_risk) if price_risk > 0 else 0
                if qty > 0:
                    position = {
                        "side": signal["action"],
                        "entry": signal["entry_price"],
                        "sl": signal["stop_loss"],
                        "tp": signal["take_profit"],
                        "qty": qty,
                    }

        return trades

    def _log_walk_forward_retrain_result(self, metrics: dict) -> None:
        """Log específico para walk-forward con reentrenamiento."""
        passed = self.passes_thresholds(metrics)
        logger.info(
            "walk_forward_retrain_complete",
            final_capital=metrics.get("final_capital"),
            total_trades=metrics.get("total_trades"),
            sharpe_ratio=metrics.get("sharpe_ratio"),
            avg_sharpe_oos=metrics.get("avg_sharpe_oos"),
            min_sharpe_oos=metrics.get("min_sharpe_oos"),
            max_sharpe_oos=metrics.get("max_sharpe_oos"),
            num_windows=metrics.get("num_windows"),
            passes_thresholds=passed,
        )
