"""
Script: scripts/seed_admin.py
Responsibility: Create the first admin user in the database.
  Run once after DB is set up. Idempotent — skips if email already exists.

Usage:
  python scripts/seed_admin.py --email admin@traderai.local --password <your_password>
  python scripts/seed_admin.py  (uses defaults from .env or prompts interactively)
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.settings import get_settings
from core.db.session import close_pool, init_pool
from core.db.user_repository import create_user, user_exists
from core.observability.logger import configure_logging

configure_logging()


async def seed(email: str, password: str) -> None:
    settings = get_settings()
    await init_pool(settings.DATABASE_URL)
    try:
        if await user_exists(email):
            print(f"⚠️  Usuario '{email}' ya existe. No se creó uno nuevo.")
            return
        user = await create_user(email=email, plain_password=password, role="admin")
        print(f"\n✅ Admin creado:")
        print(f"   ID    : {user.id}")
        print(f"   Email : {user.email}")
        print(f"   Role  : {user.role}")
        print(f"\n   Guarda estas credenciales en un lugar seguro.")
        print(f"   El password NO se puede recuperar — solo resetear.")
    finally:
        await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--email",    default="", help="Admin email address")
    parser.add_argument("--password", default="", help="Admin password (min 12 chars)")
    args = parser.parse_args()

    email = args.email or input("Admin email: ").strip()
    password = args.password or getpass.getpass("Admin password (min 12 chars): ")

    if not email or "@" not in email:
        print("❌ Email inválido.")
        sys.exit(1)
    if len(password) < 12:
        print("❌ Password debe tener al menos 12 caracteres.")
        sys.exit(1)

    asyncio.run(seed(email, password))


if __name__ == "__main__":
    main()
