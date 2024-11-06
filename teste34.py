# import os
import pandas as pd
# import psycopg2
# import seaborn as sns
# from matplotlib import pyplot as plt
# from sqlalchemy import create_engine, text
from theano.compat.six.moves import input
from six.moves import input
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# Создание синхронного подключения к базе данных
engine = create_engine(DATABASE_URL)


with engine.connect() as connection:
    result = connection.execute(text("""
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
    plt.show()
    # plt.close()
#
