import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from db import create_tables, populate_initial_data  # Импортируйте вашу функцию создания таблиц

async def main():
    await create_tables()
    await populate_initial_data()

if __name__ == "__main__":
    asyncio.run(main())