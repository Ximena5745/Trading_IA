"""
Module: core/infrastructure/task_queue.py
Responsibility: Celery + Redis Queue para pipeline async con retry.
  - Tareas asíncronas para ejecución de trading
  - Retry automático con backoff exponencial
  - Rate limiting por símbolo
Dependencies: celery, redis
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.observability.logger import get_logger

logger = get_logger(__name__)

CELERY_AVAILABLE = True
try:
    from celery import Celery, Task
    from celery.exceptions import MaxRetriesExceededError
except ImportError:
    CELERY_AVAILABLE = False


app = Celery(
    "trading_ia",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)


@dataclass
class TaskResult:
    task_id: str
    status: str
    result: Optional[dict]
    error: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_trading_cycle(self: Task, symbol: str, cycle_data: dict) -> dict:
    """Tarea principal del ciclo de trading."""
    try:
        logger.info("trading_cycle_started", symbol=symbol)

        from scripts.run_pipeline import _pipeline_cycle

        result = _pipeline_cycle(symbol, cycle_data)

        logger.info("trading_cycle_completed", symbol=symbol)
        return {"status": "success", "result": result}

    except Exception as exc:
        logger.error("trading_cycle_failed", symbol=symbol, error=str(exc))

        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.critical("trading_cycle_max_retries", symbol=symbol)
            return {"status": "failed", "error": str(exc)}


@app.task(bind=True, max_retries=2)
def execute_order(self: Task, order_data: dict) -> dict:
    """Tarea para ejecutar una orden."""
    try:
        from core.execution.live_binance_executor import LiveBinanceExecutor
        from core.config.settings import get_settings

        settings = get_settings()
        executor = LiveBinanceExecutor(
            api_key=settings.BINANCE_API_KEY,
            secret_key=settings.BINANCE_SECRET_KEY,
            testnet=settings.BINANCE_TESTNET,
        )

        result = executor.execute_market(
            symbol=order_data["symbol"],
            side=order_data["side"],
            quantity=order_data["quantity"],
        )

        return {
            "status": "success",
            "order_id": result.order_id,
            "fill_price": result.fill_price,
        }

    except Exception as exc:
        logger.error("order_execution_failed", error=str(exc))
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(bind=True, max_retries=1)
def send_alert(self: Task, alert_data: dict) -> dict:
    """Tarea para enviar alertas."""
    try:
        from core.notifications.telegram_bot import TelegramBot
        from core.config.settings import get_settings

        settings = get_settings()
        bot = TelegramBot(
            token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )

        bot.send_message(alert_data["message"])
        return {"status": "sent"}

    except Exception as exc:
        logger.error("alert_send_failed", error=str(exc))
        return {"status": "failed", "error": str(exc)}


@app.task
def backtest_task(config: dict) -> dict:
    """Tarea de backtesting asíncrono."""
    from scripts.backtest_crypto_model import run_backtest

    result = run_backtest(config)
    return {"status": "completed", "result": result}


@app.task
def retrain_model_task(config: dict) -> dict:
    """Tarea de reentrenamiento de modelo."""
    from scripts.retrain import main as train_model

    result = train_model(config)
    return {"status": "completed", "model_path": result}


class TaskQueueManager:
    """
    Manager para manejo de tareas asíncronas.

    M7.3: Task Queue con Celery + Redis.
    """

    def __init__(self):
        self._celery_app = app
        self._rate_limits: dict[str, datetime] = {}

    def submit_trading_cycle(self, symbol: str, cycle_data: dict) -> str:
        """Submit trading cycle task."""
        if not self._check_rate_limit(symbol):
            logger.warning("rate_limit_exceeded", symbol=symbol)
            raise ValueError(f"Rate limit exceeded for {symbol}")

        task = execute_trading_cycle.apply_async(args=[symbol, cycle_data])
        return task.id

    def submit_order(self, order_data: dict) -> str:
        """Submit order execution task."""
        task = execute_order.apply_async(args=[order_data])
        return task.id

    def submit_alert(self, alert_data: dict) -> str:
        """Submit alert task."""
        task = send_alert.apply_async(args=[alert_data])
        return task.id

    def get_task_result(self, task_id: str) -> TaskResult:
        """Obtener resultado de una tarea."""
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=self._celery_app)

        return TaskResult(
            task_id=task_id,
            status=result.status,
            result=result.result if result.ready() else None,
            error=result.info if result.failed() else None,
            started_at=result.started,
            completed_at=result.completed,
        )

    def _check_rate_limit(self, symbol: str) -> bool:
        """Verificar rate limit por símbolo."""
        from datetime import timedelta

        last_time = self._rate_limits.get(symbol)
        if last_time and datetime.utcnow() - last_time < timedelta(minutes=5):
            return False

        self._rate_limits[symbol] = datetime.utcnow()
        return True