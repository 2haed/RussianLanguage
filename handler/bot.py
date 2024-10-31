import os
import prettytable as pt 

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink, hbold
from db.database import async_session, DEP_DESCRIPTION
import asyncio
from sqlalchemy import text
from utils.parser import parse_text_and_save, create_and_send_graph, process_file

from utils.reports import generate_excel_report
from utils.stats import plot_part_of_speech_distribution, plot_syntax_dependency_distribution, \
    plot_sentence_length_distribution, plot_top_10_frequent_words, plot_word_part_of_speech_vs_sentence_length, \
    plot_user_syntax_statistics, plot_sentence_length_over_time, plot_pos_dependency_correlation

TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=TOKEN)
dp = Dispatcher()

router = Router()

waiting_for_file = {}


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(("Список команд:\n"
                          "/help - Показывает этот список\n"
                          "/init - Бот запросит текст с файлом, чтобы выдать обратно текст, разобранный по членам предложения\n"
                          "/stats - Статистические данные.\n"
                          "/leaderboard - Таблица лидеров.\n"
                          ))


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
    await message.answer("Пришли файл (txt/doc/docx) или текст (в сообщении), который ты хочешь проанализировать.")


@router.message(F.document | F.text)
async def handle_file(message: Message):
    if waiting_for_file.get(message.from_user.id):
        file = message.document
        text_content = message.text # Если в сообщении есть файл, то текст из файла перепишет эту переменную

        if file:
            file_info = await bot.get_file(file.file_id)
            file_content = await bot.download_file(file_info.file_path)
            file_extension = os.path.splitext(file.file_name)[1].lower()

            try:
                text_content = await process_file(file_content, file_extension)
            except Exception as e:
                await message.answer(f"Произошла ошибка при обработке файла: {str(e)}")
            
        async with async_session() as session:
            await parse_text_and_save(text_content, message.from_user.id, session, message.from_user.full_name)

        waiting_for_file[message.from_user.id] = False

        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Текст", callback_data="text_choice"))
        builder.add(InlineKeyboardButton(text="Картинка", callback_data="image_choice"))
        builder.add(InlineKeyboardButton(text="Статистика", callback_data="stats_choice"))
        builder.adjust(1)
        await message.answer("Текст получен. Как ты хочешь увидеть результат: в виде текста, картинки или статистики?",
                                reply_markup=builder.as_markup())

    else:
        await message.answer("Сначала используй команду /init, чтобы отправить файл или текст.")


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
                                    left join dep_mapping dm on w.dep = dm.code
                                    left join dep_formats df using(description)
                                ), raw as (
                                select ws.sentence_id,
                                        sentence_number,
                                                STRING_AGG(w.text, ' ' ORDER BY word_number)
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
                    await call.message.answer(f"Вот содержимое файла:\n{DEP_DESCRIPTION}\n\n{full_text}", parse_mode="HTML")
                else:
                    with open("text_data.html", "w", encoding="utf-8") as file:
                        file.write(f'<body><div>Памятка к тексту:<br>{DEP_DESCRIPTION}<br></div><br><div>{full_text}</div></body>')

                    md_file = FSInputFile("text_data.html")
                    await call.message.answer_document(md_file, caption="Текст слишком большой, вот файл с текстом.")

        elif call.data == "image_choice":
            status = await create_and_send_graph(session)
            if status:
                if os.path.exists('graph.png'):
                    photo_file = FSInputFile(path='graph.png')
                    await call.message.answer_photo(photo=photo_file, caption="Вот ваша картинка:")
            else:
                await call.message.answer("Не удалось создать картинку.")

        elif call.data == "stats_choice":
            result = await session.execute(text("""
                        select w.lemma, dm.description as dep, count(*) from word w
                            join word_to_sentence using(word_id)
                            join sentence using(sentence_id)
                            join sentence_to_text using(sentence_id)
                            join dep_mapping dm on w.dep = dm.code
                        where 1=1
                            and meta_timestamp = (select max(meta_timestamp) from sentence_to_text)
                            and pos != 'PUNCT'
                        group by 1, 2
                        order by 3 desc
                        """))
            stats = result.fetchall()

            if stats:
                table = pt.PrettyTable(['Слово', 'Член предложения', 'Кол-во'])
            
                if len(stats) > 30:
                    stats = stats[:30]

                for row in stats:
                    table.add_row([row.lemma, row.dep, row.count])

                await call.message.answer(f"<pre>{table}</pre>", parse_mode="HTML")


@router.message(Command("leaderboard"))
async def leaderboard_command(message: Message):
    async with async_session() as session:
        result = await session.execute(text("""
            select user_name, count(word_id) as uniq_words, count(DISTINCT text_id) AS uniq_files from word
            join word_to_sentence using(word_id)
            join sentence using(sentence_id)
            join user_info using(user_id)
            join sentence_to_text using(sentence_id)
            group by user_name
            order by 2 desc
            Limit 10;
        """))
        leaderboard = result.fetchall()

        if leaderboard:
            table = pt.PrettyTable(['User', 'Слов', 'Файлов загружено'])

            if len(leaderboard) > 30:
                    leaderboard = leaderboard[:30]

            for row in leaderboard:
                table.add_row([row.user_name, row.uniq_words, row.uniq_files])

            await message.answer(f"<pre>{table}</pre>", parse_mode="HTML")
        else:
            await message.answer("Нет данных для отображения.")


@router.message(Command("stats"))
async def stats_command(message: Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Графики", callback_data="stats_graphics"))
    builder.add(InlineKeyboardButton(text="Отчеты", callback_data="stats_reports"))
    builder.adjust(2)

    await message.answer("Выберите категорию:", reply_markup=builder.as_markup())



@router.callback_query(F.data.in_({"stats_graphics", "stats_reports"}))
async def stats_choice(call: CallbackQuery):
    if call.data == "stats_graphics":
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Распределение частей речи", callback_data="graph_pos_distribution"))
        builder.add(InlineKeyboardButton(text="Распределение синтаксических зависимостей", callback_data="graph_syntax_dependency"))
        builder.add(InlineKeyboardButton(text="Длина предложений", callback_data="graph_sentence_length"))
        builder.add(InlineKeyboardButton(text="Топ 10 частотных слов", callback_data="graph_top_frequent_words"))
        builder.add(InlineKeyboardButton(text="Часть речи и длина предложения", callback_data="graph_pos_vs_sentence_length"))
        builder.add(InlineKeyboardButton(text="Статистика синтаксиса пользователей", callback_data="graph_user_syntax_stats"))
        builder.add(InlineKeyboardButton(text="Длина предложений с течением времени", callback_data="graph_sentence_length_over_time"))
        builder.add(InlineKeyboardButton(text="Корреляция частей речи и зависимостей",callback_data="graph_pos_dependency_correlation"))
        builder.adjust(1)
        await call.message.edit_text("Выберите график:", reply_markup=builder.as_markup())
    elif call.data == "stats_reports":
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Создать отчет в Excel", callback_data="generate_excel_report"))
        builder.adjust(1)
        await call.message.edit_text("Выберите отчет:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "generate_excel_report")
async def handle_excel_report(call: CallbackQuery):
    try:
        report_file_path = await generate_excel_report()
        if os.path.exists(report_file_path):
            excel_file = FSInputFile(path=report_file_path)
            await call.message.answer_document(excel_file, caption="Вот ваш отчет в Excel.")
        else:
            await call.message.answer("Не удалось создать отчет.")

    except Exception as e:
        await call.message.answer(f"Произошла ошибка при создании отчета: {str(e)}")

@router.callback_query(F.data.in_([
    "graph_pos_distribution",
    "graph_syntax_dependency",
    "graph_sentence_length",
    "graph_top_frequent_words",
    "graph_pos_vs_sentence_length",
    "graph_user_syntax_stats",
    "graph_sentence_length_over_time",
    "graph_pos_dependency_correlation"
]))
async def handle_graph_choice(call: CallbackQuery):
    graph_map = {
        "graph_pos_distribution": plot_part_of_speech_distribution,
        "graph_syntax_dependency": plot_syntax_dependency_distribution,
        "graph_sentence_length": plot_sentence_length_distribution,
        "graph_top_frequent_words": plot_top_10_frequent_words,
        "graph_pos_vs_sentence_length": plot_word_part_of_speech_vs_sentence_length,
        "graph_user_syntax_stats": plot_user_syntax_statistics,
        "graph_sentence_length_over_time": plot_sentence_length_over_time,
        "graph_pos_dependency_correlation": plot_pos_dependency_correlation,
    }

    graph_function = graph_map.get(call.data)
    if graph_function:
        await graph_function(call)

async def start_bot():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())
