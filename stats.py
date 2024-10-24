import matplotlib.pyplot as plt
from aiogram.types import FSInputFile
from sqlalchemy import text

from db import async_session


async def plot_part_of_speech_distribution(call):
    async with async_session() as session:
        result = await session.execute(text("""
                    SELECT pm.description as pos, COUNT(*) AS count
                    FROM word w
                    join pos_mapping pm on pm.code = w.pos 
                    where pos not in ('DET', 'ADP', 'PRT', 'INTJ', 'PART', 'PUNCT')
                    GROUP BY 1;
                """))

        pos_data = result.fetchall()

    if pos_data:
        labels = [row.pos for row in pos_data]
        counts = [row.count for row in pos_data]

        fig, ax = plt.subplots()
        ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')

        plt.savefig('pos_distribution.png')
        plt.close()

        photo_file = FSInputFile('pos_distribution.png')
        await call.message.answer_photo(photo=photo_file, caption="Процентное распределение частей речи в тексте")
    else:
        await call.message.answer("Нет данных для отображения распределения частей речи.")


async def plot_syntax_dependency_distribution(call):
    async with async_session() as session:

        result = await session.execute(text("""
            SELECT description as dep, COUNT(*) AS count
            FROM word w
            join dep_mapping dm on dm.code = w.dep 
            where dm.description not in ('детерминант', 'знак препинания', 'маркер')
            GROUP BY 1;
        """))

        dep_data = result.fetchall()

        if dep_data:

            labels = [row.dep for row in dep_data]
            counts = [row.count for row in dep_data]

            fig, ax = plt.subplots()
            ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')

            plt.savefig('dep_distribution.png')
            plt.close()

            photo_file = FSInputFile('dep_distribution.png')
            await call.message.answer_photo(photo=photo_file,
                                            caption="Процентное распределение синтаксических зависимостей")
        else:
            await call.message.answer("Нет данных для отображения распределения синтаксических зависимостей.")


async def plot_sentence_length_distribution(call):
    async with async_session() as session:
        result = await session.execute(text("""
            SELECT sentence_id, count(word_id) AS word_count
            FROM word_to_sentence
            group by 1
        """))

        sentence_data = result.fetchall()

        if sentence_data:

            word_counts = [row.word_count for row in sentence_data]

            plt.figure(figsize=(10, 6))
            plt.hist(word_counts, bins=range(1, max(word_counts) + 2), edgecolor='black', alpha=0.7)
            plt.title('Распределение предложений по количеству слов')
            plt.xlabel('Количество слов в предложении')
            plt.ylabel('Количество предложений')

            plt.savefig('sentence_length_distribution.png')
            plt.close()

            photo_file = FSInputFile('sentence_length_distribution.png')
            await call.message.answer_photo(photo=photo_file, caption="Распределение предложений по количеству слов")
        else:
            await call.message.answer("Нет данных для отображения распределения длины предложений.")


async def plot_top_10_frequent_words(call):
    async with async_session() as session:

        result = await session.execute(text("""
            SELECT lemma as text, COUNT(*) as word_count
            FROM word
            where pos not in ('DET', 'ADP', 'PRT', 'INTJ', 'PART', 'PUNCT', 'CONJ', 'X', 'PRON')
                and dep not in ('dep', 'case', 'cc', 'mark', 'punct')
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 10;
        """))

        word_data = result.fetchall()

        if word_data:

            words = [row.text for row in word_data]
            word_counts = [row.word_count for row in word_data]

            plt.figure(figsize=(10, 6))
            plt.barh(words, word_counts, color='skyblue')
            plt.xlabel('Количество повторений')
            plt.title('Топ-10 самых частых слов')

            plt.gca().invert_yaxis()

            plt.savefig('top_10_words.png')
            plt.close()

            photo_file = FSInputFile('top_10_words.png')
            await call.message.answer_photo(photo=photo_file, caption="Топ-10 самых частых слов")
        else:
            await call.message.answer("Нет данных для отображения топ-10 самых частых слов.")


async def plot_word_part_of_speech_vs_sentence_length(call):
    async with async_session() as session:

        result = await session.execute(text("""
            WITH sentence_lengths AS (
                SELECT
                    s.sentence_id,
                    count(distinct word_id) AS sentence_length
                FROM word_to_sentence s
                group by 1),
            pos_frequency AS (
                SELECT
                    sl.sentence_length,
                    w.pos,
                    COUNT(*) AS pos_count
                FROM word w
                JOIN word_to_sentence ws ON w.word_id = ws.word_id
                JOIN sentence_lengths sl ON ws.sentence_id = sl.sentence_id
                GROUP BY sl.sentence_length, w.pos
            )
            SELECT sentence_length, pm.description as pos, pos_count
            FROM pos_frequency ps
            join pos_mapping pm on pm.code= ps.pos
            ORDER BY 1, 2;
        """))

        data = result.fetchall()

        if data:

            pos_categories = {}
            for row in data:
                sentence_length, pos, pos_count = row.sentence_length, row.pos, row.pos_count
                if pos not in pos_categories:
                    pos_categories[pos] = {}
                pos_categories[pos][sentence_length] = pos_categories[pos].get(sentence_length, 0) + pos_count

            plt.figure(figsize=(12, 6))

            for pos, freq_data in pos_categories.items():
                lengths = sorted(freq_data.keys())
                freqs = [freq_data[length] for length in lengths]
                plt.plot(lengths, freqs, label=pos)

            plt.xlabel('Длина предложения (в словах)')
            plt.ylabel('Частота появления части речи')
            plt.title('Частота появления частей речи в зависимости от длины предложений')
            plt.legend(title='Часть речи')
            plt.grid(True)

            plt.savefig('pos_vs_sentence_length.png')
            plt.close()

            photo_file = FSInputFile('pos_vs_sentence_length.png')
            await call.message.answer_photo(photo=photo_file,
                                            caption="Частота появления частей речи в зависимости от длины предложений")
        else:
            await call.message.answer("Нет данных для отображения частот частей речи.")


async def plot_user_syntax_statistics(call):
    async with async_session() as session:

        result = await session.execute(text("""
            SELECT 
                user_name as user_id, 
                dm.description as dep, 
                COUNT(*) AS dep_count
            FROM word w
            JOIN word_to_sentence ws USING(word_id)
            join sentence s USING(sentence_id)
            join user_info ui USING(user_id)
            join dep_mapping dm on dm.code= w.dep
            GROUP BY 
                1, 2
            ORDER BY 
                1, 2;
        """))

        data = result.fetchall()

        if data:

            user_data = {}
            for row in data:
                user_id, dep, dep_count = row.user_id, row.dep, row.dep_count
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id][dep] = dep_count

            plt.figure(figsize=(14, 7))

            for user_id, dep_freq in user_data.items():
                deps = list(dep_freq.keys())
                counts = list(dep_freq.values())
                plt.bar(deps, counts, alpha=0.6, label=f'User {user_id}')

            plt.xlabel('Синтаксические конструкции (dep)')
            plt.ylabel('Частота использования')
            plt.title('Частота использования синтаксических конструкций пользователями')
            plt.legend(title='Пользователи', loc='upper right')
            plt.xticks(rotation=45)
            plt.grid(True)

            plt.savefig('user_syntactic_structure_usage.png')
            plt.close()

            photo_file = FSInputFile('user_syntactic_structure_usage.png')
            await call.message.answer_photo(photo=photo_file,
                                            caption="Частота использования синтаксических конструкций пользователями")
        else:
            await call.message.answer("Нет данных для отображения использования синтаксических конструкций.")


async def plot_sentence_length_over_time(call):
    async with async_session() as session:

        result = await session.execute(text("""
            SELECT
                date_trunc('day', meta_timestamp) AS date,
                AVG(lenght) AS avg_sentence_length
            FROM (select sentence_id, count(word_id) as  lenght from word_to_sentence
            group by sentence_id) s
            join sentence_to_text using(sentence_id)
            GROUP BY date
            ORDER BY date
        """))

        data = result.fetchall()

        if data:
            dates = [row.date for row in data]
            avg_lengths = [row.avg_sentence_length for row in data]

            plt.figure(figsize=(10, 6))
            plt.plot(dates, avg_lengths, marker='o', linestyle='-', color='b')

            plt.xlabel('Дата')
            plt.ylabel('Средняя длина предложения (в словах)')
            plt.title('Изменение средней длины предложений со временем')
            plt.xticks(rotation=45)
            plt.grid(True)

            plt.savefig('sentence_length_over_time.png')
            plt.close()

            photo_file = FSInputFile('sentence_length_over_time.png')
            await call.message.answer_photo(photo=photo_file, caption="Изменение средней длины предложений со временем")
        else:
            await call.message.answer("Нет данных для отображения изменения длины предложений.")


async def plot_pos_dependency_correlation(call):
    import seaborn as sns
    import pandas as pd

    async with async_session() as session:

        result = await session.execute(text("""
            with raw as (SELECT pm.description as pos,
                    dm.description as dep,
                    COUNT(*)       AS frequency
             FROM word w
                      join pos_mapping pm on pm.code = w.pos
                      join dep_mapping dm on dm.code = w.dep
             where 1 = 1
               and dm.description not in ('детерминант', 'знак препинания', 'маркер')
               and pm.code not in ('DET', 'ADP', 'PRT', 'INTJ', 'PART', 'PUNCT')
             GROUP BY 1, 2
             ORDER BY 1, 2)
            select pos, dep, round(frequency/sum(frequency) over (partition by pos), 3) as frequency from raw
        """))

        data = result.fetchall()

        if data:

            df = pd.DataFrame(data, columns=["pos", "dep", "frequency"])

            pivot_table = df.pivot(index='pos', columns='dep', values='frequency').fillna(0)

            plt.figure(figsize=(12, 8))
            sns.heatmap(pivot_table, annot=False, cmap='coolwarm', linewidths=.5)

            plt.title('Корреляция между частями речи и синтаксическими зависимостями')
            plt.xlabel('Синтаксическая зависимость')
            plt.ylabel('Часть речи')

            plt.savefig('pos_dep_correlation.png')
            plt.close()

            photo_file = FSInputFile('pos_dep_correlation.png')
            await call.message.answer_photo(photo=photo_file,
                                            caption="Корреляция между частями речи и синтаксическими зависимостями")
        else:
            await call.message.answer("Нет данных для отображения корреляции.")
