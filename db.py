from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, Text
import os

# Настройки подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")

# Создание движка и сессии
engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()

# Создаем фабрику сессий
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Создаем таблицу
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class TestFile(Base):
    __tablename__ = 'test_files'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)