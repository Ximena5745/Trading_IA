"""
Module: core/auth/permissions.py
Responsibility: Role-based access control
Dependencies: none
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


ROLE_HIERARCHY = {
    Role.VIEWER: 0,
    Role.TRADER: 1,
    Role.ADMIN: 2,
}


def has_permission(user_role: str, required_role: str) -> bool:
    user_level = ROLE_HIERARCHY.get(Role(user_role), -1)
    required_level = ROLE_HIERARCHY.get(Role(required_role), 999)
    return user_level >= required_level
