import os
import re
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink, hbold
from db import async_session
import asyncio
from sqlalchemy import text
from parser import parse_text_and_save, create_and_send_graph, extract_text_from_doc
import logging
from docx import Document

TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=TOKEN)
dp = Dispatcher()

router = Router()

waiting_for_file = {}


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(("Список команд:\n"
                          "/help - Показывает этот список\n"
                          "/init - бот запросит текст с файлом, чтобы выдать обратно текст, разобранный по членам предложения\n"))


@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(("Привет, {user}.\n"
                          "Это бот для синтаксического разбора предложений на русском языке.\n"
                          "Жми /help если хочешь ознакомиться со списком команд.\n"
                          "Это open source проект, вот ссылка: {source_url}").format(
        user=hbold(message.from_user.full_name),
        source_url=hlink("GitHub", "https://github.com/2haed/RussianLanguage"), ), parse_mode="HTML")


@router.message(Command("init"))
async def init_command(message: Message):
    waiting_for_file[message.from_user.id] = True
    await message.answer("Пришли файл (txt/doc/docx), который ты хочешь проанализировать.")


@router.message(F.document)
async def handle_file(message: Message):
    if waiting_for_file.get(message.from_user.id):
        file = message.document
        if file:
            file_info = await bot.get_file(file.file_id)
            file_content = await bot.download_file(file_info.file_path)
            file_extension = os.path.splitext(file.file_name)[1].lower()
            text_content = ""

            try:
                if file_extension == ".txt":
                    text_content = file_content.getvalue().decode('utf-8')
                elif file_extension == ".docx":
                    doc = Document(file_content)
                    text_content = "\n".join(paragraph.text for paragraph in doc.paragraphs)
                elif file_extension == ".doc":
                    text_content = extract_text_from_doc(file_content)

                async with async_session() as session:
                    await parse_text_and_save(text_content, session)

                waiting_for_file[message.from_user.id] = False

                builder = InlineKeyboardBuilder()
                builder.add(InlineKeyboardButton(text="Текст", callback_data="text_choice"))
                builder.add(InlineKeyboardButton(text="Картинка", callback_data="image_choice"))
                builder.add(InlineKeyboardButton(text="Статистика", callback_data="stats_choice"))
                builder.adjust(1)
                await message.answer("Файл получен. Как ты хочешь увидеть результат: в виде текста, картинки или статистики?",
                                     reply_markup=builder.as_markup())
            except Exception as e:
                await message.answer(f"Произошла ошибка при обработке файла: {str(e)}")
    else:
        await message.answer("Сначала используй команду /init, чтобы отправить файл.")


@router.callback_query(F.data.in_({"text_choice", "image_choice", "stats_choice"}))
async def handle_choice(call: CallbackQuery):
    async with async_session() as session:
        if call.data == "text_choice":
            result = await session.execute(text("""
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
                    """))
            last_file = result.fetchone()
            if last_file:
                full_text = last_file[0]

                if len(full_text) <= 4096:
                    await call.message.answer(f"Вот содержимое файла:\n\n{full_text}", parse_mode="HTML")
                else:
                    with open("text_data.txt", "w", encoding="utf-8") as file:
                        file.write(full_text)

                    txt_file = FSInputFile("text_data.txt")
                    await call.message.answer_document(txt_file, caption="Текст слишком большой, вот файл с текстом.")

        elif call.data == "image_choice":
            await create_and_send_graph(session)
            if os.path.exists('graph.png'):
                photo_file = FSInputFile(path='graph.png')
                await call.message.answer_photo(photo=photo_file, caption="Вот ваша картинка:")
            else:
                await call.message.answer("Не удалось создать картинку.")

        elif call.data == "stats_choice":
            result = await session.execute(text("""
                        select dm.description as dep, count(*) from word w
                            join word_to_sentence using(word_id)
                            join sentence using(sentence_id)
                            join sentence_to_text using(sentence_id)
                            join dep_mapping dm on w.dep = dm.code
                        where 1=1
                            and meta_timestamp = (select max(meta_timestamp) from sentence_to_text)
                            and pos != 'PUNCT'
                        group by 1
                        order by 2 desc
                        """))
            stats = result.fetchall()

            if stats:
                max_dep_length = max(len(row.dep) for row in stats)

                table_header = "Член предложения" + " " * (max_dep_length - len("Член предложения")) + " | Количество\n"
                table_header += "-" * (max_dep_length + 14) + "\n"

                table_rows = ""
                for row in stats:
                    table_rows += f"{row.dep:<{max_dep_length}} | {row.count}\n"
                table = f"<pre>{table_header}{table_rows}</pre>"
                await call.message.answer(table, parse_mode="HTML")


async def start_bot():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())
