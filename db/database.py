import os
import uuid

from sqlalchemy import Column, Integer, String, ForeignKey, select, func, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")

engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SentenceToText(Base):
    __tablename__ = 'sentence_to_text'
    sentence_id = Column(UUID(as_uuid=True), ForeignKey('sentence.sentence_id'), primary_key=True, default=uuid.uuid4)
    text_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sentence_number = Column(Integer, nullable=False)
    meta_timestamp = Column(TIMESTAMP, nullable=False)


class UserInfo(Base):
    __tablename__ = 'user_info'

    user_id = Column(Integer, primary_key=True, unique=True)
    user_name = Column(String, unique=True, nullable=False)


class Sentence(Base):
    __tablename__ = 'sentence'
    sentence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)


class WordToSentence(Base):
    __tablename__ = 'word_to_sentence'
    word_id = Column(UUID(as_uuid=True), ForeignKey('word.word_id'), primary_key=True, default=uuid.uuid4)
    sentence_id = Column(UUID(as_uuid=True), ForeignKey('sentence.sentence_id'), primary_key=True, default=uuid.uuid4)
    word_number = Column(Integer, nullable=False)


class Word(Base):
    __tablename__ = 'word'
    word_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String, nullable=False)
    pos = Column(String, nullable=False)  # Часть речи
    dep = Column(String, nullable=False)  # Синтаксическая зависимость
    lemma = Column(String, nullable=False)
    head_idx = Column(Integer, nullable=False)

