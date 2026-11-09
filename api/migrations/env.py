"""Alembic muhiti.

Ulanish manzili `app.config.settings` dan olinadi, ya'ni ilova bilan bir xil
`.env` ishlatiladi. Testlar o'z bazasini `config.attributes["database_url"]`
orqali beradi.
"""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401 — jadvallar metadata'ga tushishi uchun
from app.config import settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    url = config.attributes.get("database_url") or settings.database_url
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline rejim ishlatilmaydi: migratsiyalar bazaga ulanib bajariladi.")

asyncio.run(_run_online())
