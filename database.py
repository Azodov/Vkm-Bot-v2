"""
PostgreSQL database connection va session management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import config

# Database engine yaratish - optimallashtirilgan
engine = create_async_engine(
    config.database.url,
    echo=config.debug,  # Debug rejimiga qarab
    future=True,
    # Connection pool optimallashtirish - yanada yaxshilangan
    pool_size=15,  # Asosiy pool o'lchami (10 -> 15)
    max_overflow=25,  # Qo'shimcha connectionlar (20 -> 25)
    pool_pre_ping=True,  # Connection health check
    pool_recycle=3600,  # Connection'larni 1 soatdan keyin yangilash
    pool_timeout=30,  # Connection olish uchun timeout (sekund)
    connect_args={
        "server_settings": {
            "application_name": "telegram_bot",
            "jit": "off",  # Tezlik uchun
            "statement_timeout": "30000",  # 30 soniya query timeout
        }
    },
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base model
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session olish
    Usage:
        async with get_db_session() as session:
            # database operatsiyalari
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Database jadvallarini yaratish"""
    # Modellarni import qilish (jadvallar yaratish uchun kerak)
    import models  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Database ulanishini yopish"""
    await engine.dispose()
