"""
Module: core/features/feature_store.py
Responsibility: Versioned in-memory + Redis feature storage with drift detection
Dependencies: redis, models, logger, hashlib
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

import numpy as np
import redis.asyncio as aioredis

from core.models import FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

FEATURE_STORE_KEY = "features:{symbol}:{version}"
FEATURE_HISTORY_KEY = "features_history:{symbol}"
FEATURE_CONFIG_HASH_KEY = "features:config_hash"
MAX_HISTORY = 500
DRIFT_THRESHOLD = 0.1  # KL divergence threshold for drift detection


class FeatureStore:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._local_cache: dict[str, FeatureSet] = {}
        self._config_hash: Optional[str] = None

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url)

    # M2.2.1: Hash de configuración de features
    def compute_config_hash(self, config: dict) -> str:
        """Genera hash SHA256 de la configuración de features."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def set_config(self, config: dict) -> str:
        """Establece la configuración actual y retorna su hash."""
        self._config_hash = self.compute_config_hash(config)
        return self._config_hash

    def get_config_hash(self) -> Optional[str]:
        """Retorna el hash de la configuración actual."""
        return self._config_hash

    # M2.2.2: Detección de drift (KL-divergence)
    def detect_drift(
        self, reference_data: np.ndarray, current_data: np.ndarray
    ) -> dict:
        """
        Detecta feature drift usando KL-divergence.
        Retorna dict con:
        - drift_detected: bool
        - kl_divergence: float
        - drifted_features: list de features con drift
        """
        if len(reference_data) < 10 or len(current_data) < 10:
            return {"drift_detected": False, "kl_divergence": 0.0, "drifted_features": []}

        drifted_features = []
        total_kl = 0.0

        for i in range(min(len(reference_data), len(current_data))):
            ref = reference_data[i]
            curr = current_data[i]

            # Evitar division por cero
            ref = np.clip(ref, 1e-10, None)
            curr = np.clip(curr, 1e-10, None)

            # Normalizar
            ref = ref / ref.sum() if ref.sum() > 0 else ref
            curr = curr / curr.sum() if curr.sum() > 0 else curr

            # KL divergence
            kl = np.sum(ref * np.log(ref / curr))
            total_kl += kl

            if kl > DRIFT_THRESHOLD:
                drifted_features.append(f"feature_{i}")

        avg_kl = total_kl / min(len(reference_data), len(current_data))

        return {
            "drift_detected": avg_kl > DRIFT_THRESHOLD,
            "kl_divergence": float(avg_kl),
            "drifted_features": drifted_features,
        }

    # M2.2.3: Validación de calidad (NaN, outliers, rango)
    def validate_quality(self, features: FeatureSet) -> dict:
        """
        Valida calidad de features.
        Retorna dict con:
        - is_valid: bool
        - nan_count: int
        - outlier_count: int
        - issues: list de problemas encontrados
        """
        issues = []
        nan_count = 0
        outlier_count = 0

        # Convertir a dict para análisis
        feat_dict = features.model_dump()

        for key, value in feat_dict.items():
            if value is None:
                continue

            # Verificar NaN
            if isinstance(value, (int, float)) and np.isnan(value):
                nan_count += 1
                issues.append(f"NaN in {key}")

            # Verificar outliers (más de 5 std de la media)
            if isinstance(value, (list, np.ndarray)):
                arr = np.array(value)
                if len(arr) > 0:
                    mean = np.mean(arr)
                    std = np.std(arr)
                    if std > 0:
                        outliers = np.abs((arr - mean) / std) > 5
                        outlier_count += int(np.sum(outliers))
                        if np.any(outliers):
                            issues.append(f"Outliers in {key}")

        return {
            "is_valid": nan_count == 0 and outlier_count == 0,
            "nan_count": nan_count,
            "outlier_count": outlier_count,
            "issues": issues,
        }

    async def save(self, features: FeatureSet) -> None:
        self._local_cache[features.symbol] = features
        if self._redis:
            key = FEATURE_STORE_KEY.format(
                symbol=features.symbol, version=features.version
            )
            await self._redis.set(key, features.model_dump_json(), ex=3600)
            history_key = FEATURE_HISTORY_KEY.format(symbol=features.symbol)
            await self._redis.lpush(history_key, features.model_dump_json())
            await self._redis.ltrim(history_key, 0, MAX_HISTORY - 1)

            # Guardar hash de configuración
            if self._config_hash:
                await self._redis.hset(
                    FEATURE_CONFIG_HASH_KEY,
                    mapping={features.symbol: self._config_hash},
                )

        logger.debug("features_saved", symbol=features.symbol, version=features.version)

    async def get_latest(
        self, symbol: str, version: str = "v1"
    ) -> Optional[FeatureSet]:
        if symbol in self._local_cache:
            return self._local_cache[symbol]
        if self._redis:
            key = FEATURE_STORE_KEY.format(symbol=symbol, version=version)
            data = await self._redis.get(key)
            if data:
                return FeatureSet.model_validate_json(data)
        return None

    async def get_history(self, symbol: str, limit: int = 100) -> list[FeatureSet]:
        if not self._redis:
            return []
        history_key = FEATURE_HISTORY_KEY.format(symbol=symbol)
        raw_list = await self._redis.lrange(history_key, 0, limit - 1)
        return [FeatureSet.model_validate_json(r) for r in raw_list]

    async def get_config_version(self, symbol: str) -> Optional[str]:
        """Obtiene el hash de configuración guardado para un símbolo."""
        if not self._redis:
            return None
        return await self._redis.hget(FEATURE_CONFIG_HASH_KEY, symbol)
