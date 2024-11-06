import os
import uuid
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
engine = create_engine(DATABASE_URL, echo=True)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sentence (
    sentence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    user_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_info (
    user_id INTEGER PRIMARY KEY,
    user_name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS word (
    word_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text VARCHAR(255) NOT NULL,
    pos VARCHAR(50) NOT NULL,
    dep VARCHAR(50) NOT NULL,
    lemma VARCHAR(255) NOT NULL,
    head_idx INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sentence_to_text (
    sentence_id UUID REFERENCES sentence(sentence_id),
    text_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sentence_number INTEGER NOT NULL,
    meta_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS word_to_sentence (
    word_id UUID REFERENCES word(word_id),
    sentence_id UUID REFERENCES sentence(sentence_id),
    word_number INTEGER NOT NULL,
    PRIMARY KEY (word_id, sentence_id)
);
"""

def create_tables():
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLES_SQL))
        print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
