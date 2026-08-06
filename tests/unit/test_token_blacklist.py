"""
Tests for core/auth/token_blacklist.py

Paso 8 del plan maestro ("gaps baratos"): la logica de blacklist vivia
inline dentro de JWTHandler; se extrajo a su propio modulo. Estos tests
cubren el modulo aislado, incluido el comportamiento fail-open cuando
Redis no responde (ver docstring de TokenBlacklist para el porque).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from core.auth.token_blacklist import TokenBlacklist


class TestTokenBlacklistWithRedis:
    @pytest.fixture
    def mock_redis(self):
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        return redis_mock

    @pytest.fixture
    def blacklist(self, mock_redis):
        return TokenBlacklist("redis://localhost:6379", redis_client=mock_redis)

    def test_add_writes_ttl_bounded_key(self, blacklist, mock_redis):
        exp = (datetime.utcnow() + timedelta(minutes=60)).timestamp()
        result = blacklist.add("jti-123", exp)

        assert result is True
        mock_redis.setex.assert_called_once()
        args, _ = mock_redis.setex.call_args
        assert args[0] == "blacklist:jti-123"

    def test_add_clamps_ttl_to_max_ttl_seconds(self, blacklist, mock_redis):
        exp = (datetime.utcnow() + timedelta(days=30)).timestamp()
        blacklist.add("jti-123", exp, max_ttl_seconds=604800)

        args, _ = mock_redis.setex.call_args
        assert args[1] <= 604800

    def test_is_blacklisted_true(self, blacklist, mock_redis):
        mock_redis.exists.return_value = True
        assert blacklist.is_blacklisted("jti-123") is True

    def test_is_blacklisted_false(self, blacklist, mock_redis):
        mock_redis.exists.return_value = False
        assert blacklist.is_blacklisted("jti-123") is False


class TestTokenBlacklistFailsOpenWithoutRedis:
    """Sin Redis disponible, is_blacklisted/add no deben lanzar -- degradan a False."""

    @pytest.fixture
    def blacklist(self):
        bl = TokenBlacklist("redis://unreachable-host:6379")
        bl._get_redis = lambda: None  # simulate Redis unavailable
        return bl

    def test_is_blacklisted_returns_false_without_redis(self, blacklist):
        assert blacklist.is_blacklisted("jti-123") is False

    def test_add_returns_false_without_redis(self, blacklist):
        exp = (datetime.utcnow() + timedelta(minutes=60)).timestamp()
        assert blacklist.add("jti-123", exp) is False
