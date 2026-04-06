"""
Module: core/consensus/asset_specific_consensus.py
Responsibility: Consensus engine with asset-specific multi-model support
Dependencies: voting_engine, asset_specific_agent, models, logger

Este módulo extiende el consensus engine para soportar el AssetSpecificAgent
con arquitectura multi-modelo por tipo de activo.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.agents.asset_specific_agent import AssetSpecificAgent, create_asset_agent
from core.consensus.conflict_logger import ConflictLogger
from core.models import (
    AgentOutput,
    AssetClass,
    ConsensusOutput,
    RegimeOutput,
    detect_asset_class,
)
from core.observability.logger import get_logger

logger = get_logger(__name__)

# Pesos para el modo asset-specific (cuando se usa AssetSpecificAgent)
# El AssetSpecificAgent ya tiene su propio ensemble interno, por lo que
# se le da un peso mayor en el consenso final
ASSET_SPECIFIC_WEIGHTS: dict[str, float] = {
    "asset_specific_v1": 0.60,  # Multi-modelo por activo
    "technical_v1": 0.25,       # Modelo técnico base
    "regime_v1": 0.15,          # Regimen (complementario)
}

# Pesos legacy para compatibilidad
AGENT_WEIGHTS_CRYPTO: dict[str, float] = {
    "technical_v1": 0.45,
    "regime_v1": 0.35,
    "microstructure_v1": 0.20,
}

AGENT_WEIGHTS_MT5: dict[str, float] = {
    "technical_v1": 0.55,
    "regime_v1": 0.45,
    "microstructure_v1": 0.00,
}

MIN_CONSENSUS_SCORE = 0.30
MIN_AGENTS_AGREEING = 0.60


class AssetSpecificConsensusEngine:
    """
    Consensus engine que integra el AssetSpecificAgent con arquitectura multi-modelo.
    
    Características:
    - Detecta automáticamente la clase de activo
    - Usa AssetSpecificAgent cuando está disponible
    - Fallback a agents individuales si no hay modelos entrenados
    - Aplica filtros de decisión adicionales
    """
    
    def __init__(
        self,
        use_asset_specific: bool = True,
        model_base_path: str = "data/models/asset_specific",
    ):
        self._conflict_logger = ConflictLogger()
        self._use_asset_specific = use_asset_specific
        self._model_base_path = model_base_path
        
        # Cache de agents específicos por símbolo
        self._asset_agents: dict[str, AssetSpecificAgent] = {}
        
    def _get_asset_agent(self, symbol: str) -> Optional[AssetSpecificAgent]:
        """Obtiene o crea un AssetSpecificAgent para el símbolo."""
        if not self._use_asset_specific:
            return None
        
        if symbol not in self._asset_agents:
            try:
                agent = create_asset_agent(
                    symbol=symbol,
                    model_base_path=self._model_base_path,
                )
                if agent.is_ready():
                    self._asset_agents[symbol] = agent
                    logger.info("asset_agent_created", symbol=symbol)
                else:
                    logger.warning("asset_agent_not_ready", symbol=symbol)
                    return None
            except Exception as e:
                logger.error("asset_agent_creation_failed", symbol=symbol, error=str(e))
                return None
        
        return self._asset_agents.get(symbol)
    
    def aggregate(
        self,
        agent_outputs: list[AgentOutput],
        regime: RegimeOutput,
        symbol: Optional[str] = None,
    ) -> ConsensusOutput:
        """
        Agrega predicciones de múltiples agents con soporte asset-specific.
        
        Args:
            agent_outputs: Lista de outputs de agents individuales
            regime: Output del RegimeAgent
            symbol: Símbolo del activo (opcional)
        
        Returns:
            ConsensusOutput con la decisión final
        """
        # Detectar símbolo si no se proporciona
        if symbol is None and agent_outputs:
            symbol = agent_outputs[0].symbol
        
        if not symbol:
            raise ValueError("Symbol must be provided or present in agent_outputs")
        
        ts = agent_outputs[0].timestamp if agent_outputs else datetime.utcnow()
        
        # Intentar usar AssetSpecificAgent
        asset_agent = self._get_asset_agent(symbol)
        
        if asset_agent is not None:
            return self._aggregate_with_asset_agent(
                asset_agent, agent_outputs, regime, symbol, ts
            )
        else:
            return self._aggregate_legacy(agent_outputs, regime, symbol, ts)
    
    def _aggregate_with_asset_agent(
        self,
        asset_agent: AssetSpecificAgent,
        agent_outputs: list[AgentOutput],
        regime: RegimeOutput,
        symbol: str,
        timestamp: datetime,
    ) -> ConsensusOutput:
        """Agrega usando el AssetSpecificAgent como principal."""
        
        # Gate 1: regime veto
        if not regime.signal_allowed:
            logger.info(
                "signal_blocked_by_regime",
                symbol=symbol,
                regime=regime.regime.value,
                confidence=regime.confidence,
            )
            return ConsensusOutput(
                timestamp=timestamp,
                symbol=symbol,
                final_direction="NEUTRAL",
                weighted_score=0.0,
                agents_agreement=0.0,
                blocked_by_regime=True,
                agent_outputs=agent_outputs,
                conflicts=[],
            )
        
        # Obtener predicción del AssetSpecificAgent
        # Nota: El asset_agent ya tiene features internamente
        # En una implementación real, necesitaríamos pasarle las features
        # Aquí usamos los outputs existentes como proxy
        
        asset_output = next(
            (o for o in agent_outputs if o.agent_id == "asset_specific_v1"),
            None
        )
        
        if asset_output is None:
            # Si no hay output del asset agent, usar legacy
            return self._aggregate_legacy(agent_outputs, regime, symbol, timestamp)
        
        # Calcular score ponderado
        weights = ASSET_SPECIFIC_WEIGHTS
        total_weight = 0.0
        weighted_score = 0.0
        
        for output in agent_outputs:
            weight = weights.get(output.agent_id, 0.0)
            if weight == 0.0:
                continue
            weighted_score += output.score * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_score /= total_weight
        
        # Determinar dirección
        if weighted_score >= MIN_CONSENSUS_SCORE:
            dominant = "BUY"
        elif weighted_score <= -MIN_CONSENSUS_SCORE:
            dominant = "SELL"
        else:
            dominant = "NEUTRAL"
        
        # Calcular agreement
        active_outputs = [
            o for o in agent_outputs if weights.get(o.agent_id, 0.0) > 0.0
        ]
        
        if dominant != "NEUTRAL" and active_outputs:
            agreeing = sum(
                1 for o in active_outputs
                if (dominant == "BUY" and o.score > 0) or
                   (dominant == "SELL" and o.score < 0)
            )
            agreement = agreeing / len(active_outputs)
        else:
            agreement = 0.0
        
        # Gate 2: minimum agreement
        if agreement < MIN_AGENTS_AGREEING and dominant != "NEUTRAL":
            logger.info(
                "signal_blocked_low_agreement",
                symbol=symbol,
                agreement=agreement,
                threshold=MIN_AGENTS_AGREEING,
            )
            dominant = "NEUTRAL"
        
        # Detectar conflictos
        conflicts = self._conflict_logger.detect_conflicts(agent_outputs)
        
        logger.info(
            "asset_specific_consensus_result",
            symbol=symbol,
            direction=dominant,
            score=round(weighted_score, 4),
            agreement=round(agreement, 4),
            mode="asset_specific",
            conflicts=len(conflicts),
        )
        
        return ConsensusOutput(
            timestamp=timestamp,
            symbol=symbol,
            final_direction=dominant,
            weighted_score=round(weighted_score, 4),
            agents_agreement=round(agreement, 4),
            blocked_by_regime=False,
            agent_outputs=agent_outputs,
            conflicts=conflicts,
        )
    
    def _aggregate_legacy(
        self,
        agent_outputs: list[AgentOutput],
        regime: RegimeOutput,
        symbol: str,
        timestamp: datetime,
    ) -> ConsensusOutput:
        """Agregación legacy cuando no hay AssetSpecificAgent disponible."""
        
        from core.consensus.voting_engine import AGENT_WEIGHTS_CRYPTO, AGENT_WEIGHTS_MT5
        
        conflicts = self._conflict_logger.detect_conflicts(agent_outputs)
        
        # Gate 1: regime veto
        if not regime.signal_allowed:
            logger.info(
                "signal_blocked_by_regime",
                symbol=symbol,
                regime=regime.regime.value,
                confidence=regime.confidence,
            )
            return ConsensusOutput(
                timestamp=timestamp,
                symbol=symbol,
                final_direction="NEUTRAL",
                weighted_score=0.0,
                agents_agreement=0.0,
                blocked_by_regime=True,
                agent_outputs=agent_outputs,
                conflicts=conflicts,
            )
        
        # Seleccionar pesos según clase de activo
        asset_class = detect_asset_class(symbol)
        weights = AGENT_WEIGHTS_CRYPTO if asset_class == AssetClass.CRYPTO else AGENT_WEIGHTS_MT5
        
        # Calcular score ponderado
        total_weight = 0.0
        weighted_score = 0.0
        
        for output in agent_outputs:
            weight = weights.get(output.agent_id, 0.10)
            if weight == 0.0:
                continue
            weighted_score += output.score * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_score /= total_weight
        
        # Determinar dirección y agreement
        active_outputs = [o for o in agent_outputs if weights.get(o.agent_id, 0.10) > 0.0]
        
        if abs(weighted_score) >= MIN_CONSENSUS_SCORE and active_outputs:
            dominant = "BUY" if weighted_score > 0 else "SELL"
            agreeing = sum(
                1 for o in active_outputs
                if (dominant == "BUY" and o.score > 0) or
                   (dominant == "SELL" and o.score < 0)
            )
            agreement = agreeing / len(active_outputs)
        else:
            dominant = "NEUTRAL"
            agreement = 0.0
        
        # Gate 2: minimum agreement
        if agreement < MIN_AGENTS_AGREEING and dominant != "NEUTRAL":
            logger.info(
                "signal_blocked_low_agreement",
                symbol=symbol,
                agreement=agreement,
                threshold=MIN_AGENTS_AGREEING,
            )
            dominant = "NEUTRAL"
        
        # Gate 3: minimum score
        if abs(weighted_score) < MIN_CONSENSUS_SCORE:
            dominant = "NEUTRAL"
        
        logger.info(
            "legacy_consensus_result",
            symbol=symbol,
            direction=dominant,
            score=round(weighted_score, 4),
            agreement=round(agreement, 4),
            mode="legacy",
            conflicts=len(conflicts),
        )
        
        return ConsensusOutput(
            timestamp=timestamp,
            symbol=symbol,
            final_direction=dominant,
            weighted_score=round(weighted_score, 4),
            agents_agreement=round(agreement, 4),
            blocked_by_regime=False,
            agent_outputs=agent_outputs,
            conflicts=conflicts,
        )
    
    def get_agent_status(self, symbol: str) -> dict:
        """Retorna el estado de los agents para un símbolo."""
        asset_agent = self._get_asset_agent(symbol)
        
        status = {
            "symbol": symbol,
            "asset_specific_available": asset_agent is not None,
        }
        
        if asset_agent:
            status.update(asset_agent.get_model_status())
        
        return status


# Factory function
def create_consensus_engine(
    use_asset_specific: bool = True,
    model_base_path: str = "data/models/asset_specific",
) -> AssetSpecificConsensusEngine:
    """
    Factory para crear el consensus engine.
    
    Args:
        use_asset_specific: Si se debe usar el AssetSpecificAgent
        model_base_path: Ruta base para los modelos
    
    Returns:
        AssetSpecificConsensusEngine configurado
    """
    return AssetSpecificConsensusEngine(
        use_asset_specific=use_asset_specific,
        model_base_path=model_base_path,
    )


__all__ = [
    "AssetSpecificConsensusEngine",
    "create_consensus_engine",
    "ASSET_SPECIFIC_WEIGHTS",
]
