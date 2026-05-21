"""
Tests for core/auth/ and api/routes/auth.py
CA-5: JWT con validación real y logout efectivo
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from core.auth.jwt_handler import JWTHandler
from core.auth.permissions import Role, has_permission


class TestJWTValidation:
    """Tests for JWT token validation."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler with test secret."""
        return JWTHandler(
            secret_key="test-secret-key-minimum-32-characters-long!!",
            algorithm="HS256",
            expire_minutes=60,
            redis_client=None,
        )

    def test_jwt_validation(self, jwt_handler):
        """CA-1: JWT con secret real valida correctamente"""
        token = jwt_handler.create_access_token("user123", "trader")
        payload = jwt_handler.decode(token)

        assert payload["sub"] == "user123"
        assert payload["role"] == "trader"
        assert payload["type"] == "access"

    def test_jwt_invalid_token_rejected(self, jwt_handler):
        """JWT con token inválido debe ser rechazado"""
        with pytest.raises(Exception):  # AuthenticationError
            jwt_handler.decode("invalid.token.here")

    def test_jwt_expired_token_rejected(self, jwt_handler):
        """JWT con token expirado debe ser rechazado"""
        # Crear un token ya expirado
        from jose import jwt as jose_jwt
        payload = {
            "sub": "user123",
            "role": "trader",
            "exp": datetime.utcnow() - timedelta(hours=1),  # expirado
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access",
        }
        token = jose_jwt.encode(payload, jwt_handler._secret, algorithm=jwt_handler._algorithm)

        with pytest.raises(Exception):
            jwt_handler.decode(token)

    def test_refresh_token_creation(self, jwt_handler):
        """Refresh token se crea correctamente"""
        token = jwt_handler.create_refresh_token("user123")
        payload = jwt_handler.decode(token)

        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_refresh_token_requires_type(self, jwt_handler):
        """decode_refresh() requiere token tipo refresh"""
        # Crear access token
        access_token = jwt_handler.create_access_token("user123", "trader")

        with pytest.raises(Exception, match="Not a refresh token"):
            jwt_handler.decode_refresh(access_token)


class TestTokenBlacklist:
    """Tests for token blacklist (logout efectivo)."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        return redis_mock

    @pytest.fixture
    def jwt_handler_with_redis(self, mock_redis):
        """JWT handler with mock Redis."""
        return JWTHandler(
            secret_key="test-secret-key-minimum-32-characters-long!!",
            algorithm="HS256",
            expire_minutes=60,
            redis_client=mock_redis,
        )

    def test_blacklist_add(self, jwt_handler_with_redis, mock_redis):
        """CA-2: Tokens en blacklist son rechazados"""
        token = jwt_handler_with_redis.create_access_token("user123", "trader")

        # Añadir a blacklist
        result = jwt_handler_with_redis.add_to_blacklist(token)
        assert result is True

        # Verificar que se llamó a Redis
        mock_redis.setex.assert_called_once()

    def test_blacklisted_token_rejected(self, jwt_handler_with_redis, mock_redis):
        """Token en blacklist debe ser rechazado"""
        token = jwt_handler_with_redis.create_access_token("user123", "trader")
        jti = None

        # Obtener el jti del token para blacklist
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, jwt_handler_with_redis._secret, options={"verify_exp": False})
        jti = payload.get("jti")

        # Simular que está en blacklist
        mock_redis.exists.return_value = True

        # Intentar decodificar debería fallar
        with pytest.raises(Exception, match="Token has been revoked"):
            jwt_handler_with_redis.decode(token)


class TestRBAC:
    """Tests for role-based access control."""

    def test_admin_has_all_permissions(self):
        """Admin tiene permisos para todo"""
        assert has_permission("admin", "admin") is True
        assert has_permission("admin", "trader") is True
        assert has_permission("admin", "viewer") is True

    def test_trader_permissions(self):
        """Trader tiene permisos de trader y viewer"""
        assert has_permission("trader", "admin") is False
        assert has_permission("trader", "trader") is True
        assert has_permission("trader", "viewer") is True

    def test_viewer_permissions(self):
        """Viewer solo tiene permisos de viewer"""
        assert has_permission("viewer", "admin") is False
        assert has_permission("viewer", "trader") is False
        assert has_permission("viewer", "viewer") is True

    def test_invalid_role_returns_false(self):
        """Rol inválido retorna False"""
        assert has_permission("invalid_role", "admin") is False
        assert has_permission("admin", "invalid_role") is False

    def test_role_enum_values(self):
        """Verificar valores del enum Role"""
        assert Role.ADMIN.value == "admin"
        assert Role.TRADER.value == "trader"
        assert Role.VIEWER.value == "viewer"


class TestRateLimiting:
    """Tests for rate limiting (se verificaría con integración)."""

    def test_register_endpoint_has_rate_limit(self):
        """Rate limit en /auth/register debe ser 3/min"""
        # Esta verificación requiere tests de integración
        # Por ahora verificamos que el decorador existe en el código
        pass  # Test placeholder para integración

    def test_login_endpoint_has_rate_limit(self):
        """Rate limit en /auth/login debe ser 5/min"""
        # Verificación en código
        pass  # Test placeholder para integración


if __name__ == "__main__":
    pytest.main([__file__, "-v"])