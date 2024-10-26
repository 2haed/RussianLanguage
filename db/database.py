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


class POSMapping(Base):
    __tablename__ = 'pos_mapping'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)


class DEPMapping(Base):
    __tablename__ = 'dep_mapping'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)


class DEPFormats(Base):
    __tablename__ = 'dep_formats'

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, unique=True, nullable=False)
    start_format_string = Column(String, nullable=False)
    end_format_string = Column(String, nullable=False)


# Вставьте сюда ваши константы
POS_MAPPING = {"NOUN": "Существительное", "VERB": "Глагол", "ADJ": "Прилагательное", "ADV": "Наречие",
    "PRON": "Местоимение", "DET": "Местоимение", "ADP": "Предлог", "CONJ": "Союз", "PRT": "Частица",
    "INTJ": "Междометие", "NUM": "Числительное", "PROPN": "Собственное имя", "PART": "Частица",
    "SCONJ": "Союз", "PUNCT": "Знаки препинания", "CCONJ": "Союз"}

DEP_MAPPING = dependencies_translation = {
    "ROOT": "сказуемое",
    "acl": "причастие",
    "acl:relcl": "причастие",
    "advcl": "деепричастие",
    "advmod": "обстоятельство",
    "amod": "определение",
    "appos": "определение",
    "aux": "сказуемое",
    "aux:pass": "сказуемое",
    "case": "предлог",
    "cc": "союз",
    "ccomp": "дополнение",
    "compound": "определение",
    "conj": "союз",
    "cop": "сказуемое",
    "csubj": "подлежащее",
    "csubj:pass": "подлежащее",
    "dep": "дополнение",
    "det": "определение",
    "discourse": "частица",
    "expl": "частица",
    "fixed": "союз",
    "flat": "определение",
    "flat:foreign": "определение",
    "flat:name": "определение",
    "iobj": "дополнение",
    "list": "определение",
    "mark": "союз",
    "nmod": "дополнение",
    "nsubj": "подлежащее",
    "nsubj:pass": "подлежащее",
    "nummod": "определение",
    "nummod:entity": "определение",
    "nummod:gov": "определение",
    "obj": "дополнение",
    "obl": "обстоятельство",
    "obl:agent": "обстоятельство",
    "orphan": "определение",
    "parataxis": "союз",
    "punct": "частица",
    "xcomp": "дополнение"
}

DEP_FORMATS = {
    'подлежащее': ('__', '__'),
    'сказуемое': ('**__', '__**'),
    'определение': ('_', '_'),
    'дополнение': ('_', '_'),
    'обстоятельство': ('_', '_'),
    'причастие': ('__*', '*__'),
    'деепричастие': ('__*', '*__'),
}


async def populate_initial_data():
    async with async_session() as session:
        async with session.begin():
            # Проверка и заполнение таблицы pos_mapping
            pos_count = await session.execute(select(func.count()).select_from(POSMapping))
            if pos_count.scalar() == 0:  # Если таблица пуста
                for code, description in POS_MAPPING.items():
                    pos_entry = POSMapping(code=code, description=description)
                    session.add(pos_entry)

            # Проверка и заполнение таблицы dep_mapping
            dep_count = await session.execute(select(func.count()).select_from(DEPMapping))
            if dep_count.scalar() == 0:  # Если таблица пуста
                for code, description in DEP_MAPPING.items():
                    dep_entry = DEPMapping(code=code, description=description)
                    session.add(dep_entry)

            # Проверка и заполнение таблицы dep_formats
            dep_format_count = await session.execute(select(func.count()).select_from(DEPFormats))
            if dep_format_count.scalar() == 0:  # Если таблица пуста
                for description, format_string in DEP_FORMATS.items():
                    dep_format_entry = DEPFormats(description=description, start_format_string=format_string[0],
                        end_format_string=format_string[1])
                    session.add(dep_format_entry)
