"""
Module: core/auth/jwt_handler.py
Responsibility: JWT token generation and validation with blacklist support
Dependencies: python-jose, settings, token_blacklist
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import redis
from jose import JWTError, jwt

from core.auth.token_blacklist import TokenBlacklist
from core.exceptions import AuthenticationError
from core.observability.logger import get_logger
from core.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class JWTHandler:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expire_minutes: int = 60,
        redis_client: Optional[redis.Redis] = None,
    ):
        self._secret = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes
        self._blacklist = TokenBlacklist(settings.REDIS_URL, redis_client)

    def create_access_token(self, user_id: str, role: str) -> str:
        payload = {
            "sub": user_id,
            "role": role,
            "jti": str(uuid4()),
            "exp": datetime.utcnow() + timedelta(minutes=self._expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "jti": str(uuid4()),
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])

            if payload.get("type") == "access":
                jti = payload.get("jti")
                if jti and self._blacklist.is_blacklisted(jti):
                    raise AuthenticationError("Token has been revoked")

            return payload
        except JWTError as e:
            logger.warning("jwt_decode_failed", error=str(e))
            raise AuthenticationError("Invalid or expired token") from e

    def decode_refresh(self, token: str) -> str:
        payload = self.decode(token)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Not a refresh token")
        return payload["sub"]

    def add_to_blacklist(self, token: str, expiry_seconds: int = 604800) -> bool:
        try:
            payload = jwt.decode(
                token, self._secret, algorithms=[self._algorithm], options={"verify_exp": False}
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                return self._blacklist.add(jti, exp, expiry_seconds)
        except Exception as exc:
            logger.warning("blacklist_add_failed", error=str(exc))
        return False
