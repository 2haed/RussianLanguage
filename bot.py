import os
import re
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram import F
from aiogram.filters import Command
from aiogram.utils.markdown import hlink, hbold
from db import async_session
import asyncio
from sqlalchemy import text
from parser import parse_text_and_save, create_and_send_graph

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

@router.message(F.document)
async def handle_file(message: Message):
    file = message.document
    if file:
        # Получаем файл
        file_info = await bot.get_file(file.file_id)
        file_content = await bot.download_file(file_info.file_path)

        # Преобразуем содержимое в текст
        text = file_content.getvalue().decode('utf-8')

        # Сохраняем содержимое в базу данных (распарсивая на предложения и слова)
        async with async_session() as session:
            await parse_text_and_save(text, session)

        # Отправляем сообщение с запросом на выбор команды
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Текст")],
                [KeyboardButton(text="Картинка")]
            ],
            resize_keyboard=True
        )
        await message.answer("Файл получен. Как ты хочешь увидеть результат: в виде таблицы или картинки?",
                             reply_markup=keyboard)


# Обработка выбора команды (Таблица или Картинка)
@router.message(F.text.in_({"Текст", "Картинка", "Статистика"}))
async def handle_choice(message: Message):
    # Получаем последнюю запись в базе данных
    async with async_session() as session:
        # Используем text() для объявления SQL-запроса
        if message.text == "Текст":
            result = await session.execute(
                text("""
            with words as (
                            select
                                word_id,
                                coalesce(start_format_string, '') || coalesce(text, '') || coalesce(end_format_string, '') as text
                            from word w
                            join dep_mapping dm on w.dep = dm.code
                            left join dep_formats df using(description)
                        ), raw as (
                        select ws.sentence_id,
                                sentence_number,
                                        STRING_AGG(w.text, ' ' ORDER BY ws.word_number)
                AS full_text
                        FROM sentence_to_text stt
                            JOIN sentence s USING (sentence_id)
                            join word_to_sentence ws using (sentence_id)
                            join words w using (word_id)
                        where meta_timestamp = (select max(meta_timestamp) from sentence_to_text)
                        group by ws.sentence_id, sentence_number
                        )
                        select STRING_AGG(full_text, ' ' ORDER BY sentence_number) AS full_text from raw
                """)
            )
            last_file = result.fetchone()
            if last_file:
                await message.answer(f"Вот содержимое файла разобранное по членам предложения:\n\n{last_file[0]}", parse_mode="HTML")

        elif message.text == "Картинка":
            await create_and_send_graph(session)
            if os.path.exists('graph.png'):
                photo_file = FSInputFile(path='graph.png')
                await message.answer_photo(photo=photo_file, caption="Вот ваша картинка:")
            else:
                await message.answer("Не удалось создать картинку.")
        else:
            await message.answer("Нет данных для отображения.")


# Старт бота
async def start_bot():
    # Регистрация роутера в диспетчере
    dp.include_router(router)

    # Запускаем поллинг для бота
    await dp.start_polling(bot)
