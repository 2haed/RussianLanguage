import os
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
from aiogram.filters import Command
from aiogram.utils.markdown import hlink, hbold
from db import async_session, TestFile
import asyncio
from sqlalchemy import text


TOKEN = os.getenv('TELEGRAM_TOKEN')

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаем Router для регистрации обработчиков
router = Router()


# Команда /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        (
            "Список команд:\n"
            "/help - Показывает этот список\n"
            "/init - бот запросит текст с файлом, чтобы выдать обратно текст, разобранный по членам предложения\n"
        )
    )


# Команда /start
@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        (
            "Привет, {user}.\n"
            "Это бот для синтаксического разбора предложений на русском языке.\n"
            "Жми /help если хочешь ознакомиться со списком команд.\n"
            "Это open source проект, вот ссылка: {source_url}"
        ).format(
            user=hbold(message.from_user.full_name),
            source_url=hlink("GitHub", "https://github.com/2haed/russian_language_bot"),
        ),
        parse_mode="HTML"
    )


# Команда /init для запроса файла
@router.message(Command("init"))
async def init_command(message: Message):
    await message.answer("Пришли файл (txt/doc/docx), который ты хочешь проанализировать.")


# Обработчик получения файла после команды /init
@router.message(F.document)
async def handle_file(message: Message):
    file = message.document
    if file:
        # Получаем файл
        file_info = await bot.get_file(file.file_id)
        file_content = await bot.download_file(file_info.file_path)

        # Преобразуем содержимое в текст
        text = file_content.getvalue().decode('utf-8')

        # Сохраняем содержимое в базу данных
        async with async_session() as session:
            new_file = TestFile(text=text)
            session.add(new_file)
            await session.commit()

        # Отправляем сообщение с запросом на выбор команды
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Таблица")],
                [KeyboardButton(text="Картинка")]
            ],
            resize_keyboard=True
        )
        await message.answer("Файл получен. Как ты хочешь увидеть результат: в виде таблицы или картинки?",
                             reply_markup=keyboard)


# Обработка выбора команды (Таблица или Картинка)
@router.message(F.text.in_({"Таблица", "Картинка"}))
async def handle_choice(message: Message):
    # Получаем последнюю запись в базе данных
    async with async_session() as session:
        # Используем text() для объявления SQL-запроса
        result = await session.execute(
            text("SELECT text FROM test_files ORDER BY id DESC LIMIT 1")
        )
        last_file = result.fetchone()

    if last_file:
        if message.text == "Таблица":
            await message.answer(f"Вот содержимое файла в виде таблицы:\n\n{last_file[0]}")
        elif message.text == "Картинка":
            await message.answer(f"Вот содержимое файла в виде картинки:\n\n{last_file[0]}")
    else:
        await message.answer("Нет данных для отображения.")


# Старт бота
async def start_bot():
    # Регистрация роутера в диспетчере
    dp.include_router(router)

    # Запускаем поллинг для бота
    await dp.start_polling(bot)
