import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from db import async_session


async def generate_excel_report():
    async with async_session() as session:
        sentence_data = await session.execute(text("""
            SELECT s.sentence_id, s.text, u.user_name, COUNT(w.word_id) AS word_count
            FROM sentence s
            JOIN word_to_sentence wts ON s.sentence_id = wts.sentence_id
            JOIN word w ON wts.word_id = w.word_id
            JOIN user_info u ON s.user_id = u.user_id
            GROUP BY s.sentence_id, s.text, u.user_name;
        """))

        sentences_df = pd.DataFrame(sentence_data.fetchall(),
                                    columns=['Sentence ID', 'Sentence Text', 'User', 'Word Count'])

        sentence_summary = sentences_df.groupby('User').agg(
            Total_Sentences=('Sentence ID', 'count'),
            Avg_Word_Count=('Word Count', 'mean')
        ).reset_index()

        word_data = await session.execute(text("""
            SELECT w.text, w.pos, COUNT(*) as frequency
            FROM word w
            GROUP BY w.text, w.pos
            ORDER BY frequency DESC;
        """))

        words_df = pd.DataFrame(word_data.fetchall(), columns=['Слово', 'Часть речи', 'Частота'])
        with pd.ExcelWriter('report.xlsx', engine='xlsxwriter') as writer:
            sentences_df.to_excel(writer, sheet_name='Sentences', index=False)
            sentence_summary.to_excel(writer, sheet_name='Summary', index=False)
            words_df.to_excel(writer, sheet_name='Word Frequency', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Summary']

            format_header = workbook.add_format({'bold': True, 'bg_color': '#ADD8E6'})
            worksheet.set_row(0, None, format_header)

            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'categories': ['Summary', 1, 0, len(sentence_summary), 0],
                'values': ['Summary', 1, 2, len(sentence_summary), 2],
                'name': 'Avg Word Count',
            })
            worksheet.insert_chart('E2', chart)

        return "report.xlsx"