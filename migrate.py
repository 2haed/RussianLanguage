import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from db import create_tables  # Импортируйте вашу функцию создания таблиц

async def main():
    await create_tables()

if __name__ == "__main__":
    asyncio.run(main())