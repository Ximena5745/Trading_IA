"""
Module: core/agents/agent_monitor.py
Responsibility: Monitor agent performance and health
Dependencies: pandas, numpy, structlog
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.models import AgentOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)


class AgentMonitor:
    """Monitor agent performance, accuracy, and health metrics."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.predictions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.outcomes: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.confidence_scores: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.last_activity: Dict[str, datetime] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.performance_metrics: Dict[str, Dict] = {}
    
    def record_prediction(self, agent_output: AgentOutput) -> None:
        """Record a new agent prediction."""
        agent_id = agent_output.agent_id
        self.predictions[agent_id].append({
            "timestamp": agent_output.timestamp,
            "symbol": agent_output.symbol,
            "direction": agent_output.direction,
            "score": agent_output.score,
            "confidence": agent_output.confidence,
        })
        self.confidence_scores[agent_id].append(agent_output.confidence)
        self.last_activity[agent_id] = datetime.utcnow()
        
        # Update performance metrics
        self._update_performance_metrics(agent_id)
    
    def record_outcome(self, agent_id: str, symbol: str, actual_direction: str, pnl: float) -> None:
        """Record the actual outcome of a prediction."""
        self.outcomes[agent_id].append({
            "timestamp": datetime.utcnow(),
            "symbol": symbol,
            "actual_direction": actual_direction,
            "pnl": pnl,
        })
    
    def record_error(self, agent_id: str, error: Exception) -> None:
        """Record an agent error."""
        self.error_counts[agent_id] += 1
        logger.warning("agent_error", agent_id=agent_id, error=str(error))
    
    def get_agent_health(self, agent_id: str) -> Dict:
        """Get comprehensive health status for an agent."""
        if agent_id not in self.last_activity:
            return {"status": "inactive", "message": "No activity recorded"}
        
        last_activity = self.last_activity[agent_id]
        time_since_last = datetime.utcnow() - last_activity
        
        # Check if agent is stale
        if time_since_last > timedelta(hours=1):
            status = "stale"
        elif time_since_last > timedelta(minutes=5):
            status = "warning"
        else:
            status = "active"
        
        # Calculate metrics
        accuracy = self._calculate_accuracy(agent_id)
        avg_confidence = self._calculate_avg_confidence(agent_id)
        error_rate = self._calculate_error_rate(agent_id)
        
        return {
            "status": status,
            "last_activity": last_activity.isoformat(),
            "time_since_last_minutes": int(time_since_last.total_seconds() / 60),
            "accuracy": accuracy,
            "avg_confidence": avg_confidence,
            "error_rate": error_rate,
            "total_predictions": len(self.predictions[agent_id]),
            "total_outcomes": len(self.outcomes[agent_id]),
            "error_count": self.error_counts[agent_id],
        }
    
    def get_performance_report(self, agent_id: str) -> Dict:
        """Get detailed performance report for an agent."""
        if agent_id not in self.performance_metrics:
            return {"error": "No performance data available"}
        
        predictions = list(self.predictions[agent_id])
        outcomes = list(self.outcomes[agent_id])
        
        if not predictions:
            return {"error": "No predictions recorded"}
        
        # Direction accuracy
        correct_predictions = 0
        total_comparisons = 0
        
        for outcome in outcomes:
            # Find corresponding prediction
            pred = next((p for p in predictions 
                        if p["symbol"] == outcome["symbol"] and 
                        p["timestamp"] < outcome["timestamp"]), None)
            if pred:
                total_comparisons += 1
                if pred["direction"] == outcome["actual_direction"]:
                    correct_predictions += 1
        
        direction_accuracy = correct_predictions / total_comparisons if total_comparisons > 0 else 0
        
        # PnL analysis
        pnls = [o["pnl"] for o in outcomes]
        pnl_stats = {}
        if pnls:
            pnl_stats = {
                "total_pnl": sum(pnls),
                "avg_pnl": np.mean(pnls),
                "win_rate": len([p for p in pnls if p > 0]) / len(pnls),
                "sharpe_ratio": self._calculate_sharpe(pnls),
                "max_drawdown": self._calculate_max_drawdown(pnls),
            }
        
        # Confidence analysis
        confidences = list(self.confidence_scores[agent_id])
        confidence_stats = {}
        if confidences:
            confidence_stats = {
                "avg_confidence": np.mean(confidences),
                "confidence_std": np.std(confidences),
                "confidence_trend": self._calculate_confidence_trend(confidences),
            }
        
        return {
            "agent_id": agent_id,
            "period_start": predictions[0]["timestamp"].isoformat() if predictions else None,
            "period_end": predictions[-1]["timestamp"].isoformat() if predictions else None,
            "total_predictions": len(predictions),
            "total_outcomes": len(outcomes),
            "direction_accuracy": direction_accuracy,
            "pnl_stats": pnl_stats,
            "confidence_stats": confidence_stats,
            "error_count": self.error_counts[agent_id],
        }
    
    def _update_performance_metrics(self, agent_id: str) -> None:
        """Update cached performance metrics for an agent."""
        predictions = list(self.predictions[agent_id])
        if not predictions:
            return
        
        # Calculate basic metrics
        directions = [p["direction"] for p in predictions]
        scores = [p["score"] for p in predictions]
        confidences = [p["confidence"] for p in predictions]
        
        self.performance_metrics[agent_id] = {
            "last_updated": datetime.utcnow(),
            "prediction_count": len(predictions),
            "direction_distribution": {
                "BUY": directions.count("BUY"),
                "SELL": directions.count("SELL"),
                "NEUTRAL": directions.count("NEUTRAL"),
            },
            "avg_score": np.mean(scores),
            "score_std": np.std(scores),
            "avg_confidence": np.mean(confidences),
        }
    
    def _calculate_accuracy(self, agent_id: str) -> float:
        """Calculate prediction accuracy for an agent."""
        predictions = list(self.predictions[agent_id])
        outcomes = list(self.outcomes[agent_id])
        
        if not predictions or not outcomes:
            return 0.0
        
        correct = 0
        total = 0
        
        for outcome in outcomes:
            pred = next((p for p in predictions 
                        if p["symbol"] == outcome["symbol"] and 
                        p["timestamp"] < outcome["timestamp"]), None)
            if pred:
                total += 1
                if pred["direction"] == outcome["actual_direction"]:
                    correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _calculate_avg_confidence(self, agent_id: str) -> float:
        """Calculate average confidence score."""
        confidences = list(self.confidence_scores[agent_id])
        return np.mean(confidences) if confidences else 0.0
    
    def _calculate_error_rate(self, agent_id: str) -> float:
        """Calculate error rate."""
        total_predictions = len(self.predictions[agent_id])
        if total_predictions == 0:
            return 0.0
        return self.error_counts[agent_id] / total_predictions
    
    def _calculate_sharpe(self, pnls: List[float]) -> float:
        """Calculate Sharpe ratio for PnL series."""
        if len(pnls) < 2:
            return 0.0
        returns = np.array(pnls)
        return np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
    
    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """Calculate maximum drawdown."""
        if not pnls:
            return 0.0
        
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / peak
        return np.max(drawdown) if len(drawdown) > 0 else 0.0
    
    def _calculate_confidence_trend(self, confidences: List[float]) -> str:
        """Calculate confidence trend over recent predictions."""
        if len(confidences) < 10:
            return "insufficient_data"
        
        recent = confidences[-10:]
        older = confidences[-20:-10] if len(confidences) >= 20 else confidences[:-10]
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older)
        
        diff = recent_avg - older_avg
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"


# Global instance for monitoring all agents
agent_monitor = AgentMonitor()
