from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from conf.config import settings

engine = create_async_engine(
    url=settings.DATABASE_URL,
    pool_size=10,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False

)


async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



get_db = get_database
