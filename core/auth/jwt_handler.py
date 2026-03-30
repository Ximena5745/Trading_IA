"""
Module: core/auth/jwt_handler.py
Responsibility: JWT token generation and validation
Dependencies: python-jose, settings
"""
from __future__ import annotations

from datetime import datetime, timedelta

from jose import JWTError, jwt

from core.exceptions import AuthenticationError
from core.observability.logger import get_logger

logger = get_logger(__name__)


class JWTHandler:
    def __init__(
        self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60
    ):
        self._secret = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, user_id: str, role: str) -> str:
        payload = {
            "sub": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=self._expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return payload
        except JWTError as e:
            logger.warning("jwt_decode_failed", error=str(e))
            raise AuthenticationError("Invalid or expired token") from e

    def decode_refresh(self, token: str) -> str:
        payload = self.decode(token)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Not a refresh token")
        return payload["sub"]
