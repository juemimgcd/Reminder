from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.mneme.conf.config import settings


engine = create_async_engine(
    url=settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def open_database_session(*, write: bool) -> AsyncIterator[AsyncSession]:
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
        finally:
            await session.close()


@asynccontextmanager
async def open_read_session() -> AsyncIterator[AsyncSession]:
    async with open_database_session(write=False) as session:
        yield session


@asynccontextmanager
async def open_write_session() -> AsyncIterator[AsyncSession]:
    async with open_database_session(write=True) as session:
        yield session


async def get_database() -> AsyncIterator[AsyncSession]:
    async with open_read_session() as session:
        yield session


async def get_write_database() -> AsyncIterator[AsyncSession]:
    async with open_write_session() as session:
        yield session


get_db = get_database
