from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.mneme.memoria.server.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def _open_session(*, write: bool) -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            if write and session.in_transaction():
                await session.commit()
            elif not write and session.in_transaction():
                await session.rollback()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise


@asynccontextmanager
async def open_read_session() -> AsyncIterator[AsyncSession]:
    async with _open_session(write=False) as session:
        yield session


@asynccontextmanager
async def open_write_session() -> AsyncIterator[AsyncSession]:
    async with _open_session(write=True) as session:
        yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    async with open_read_session() as session:
        yield session
