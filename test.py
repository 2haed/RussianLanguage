from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import json
import asyncio
import networkx as nx
import graphviz
import matplotlib.pyplot as plt

# Строка подключения
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=True)

# Настройка сессии
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def fetch_data():
    async with async_session() as session:
        # Выполняем основной запрос

        # Создание графа
        G = nx.DiGraph()

        result = await session.execute(text("""
            select w.text as text, pos, dm.description as dep, head_idx, token_idx from word w
            join word_to_sentence using(word_id)
            join sentence using(sentence_id)
            join sentence_to_text using(sentence_id)
            join dep_mapping dm on w.dep = dm.code
        where meta_timestamp = (select max(meta_timestamp) from sentence_to_text)
            """))
        words = result.fetchall()

        # Формируем список словарей
        words_list = [
            {
                "text": word.text,
                "pos": word.pos,
                "dep": word.dep,
                "head_idx": word.head_idx,
                "token_idx": word.token_idx
            }
            for word in words
        ]

        for dep in words_list:
            node_label = f"{dep['text']}\n ({dep['dep']})"
            G.add_node(dep["token_idx"], label=node_label)

        # Добавление ребер без подписей
        for dep in words_list:
            if dep["token_idx"] != dep["head_idx"]:
                G.add_edge(dep["head_idx"], dep["token_idx"])

        # Настройка позиции узлов
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        plt.figure(figsize=(24, 16))
        # Рисование узлов
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_nodes(G, pos, node_size=1500, node_color='lightblue')

        # Рисование ребер
        nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=15)

        # Рисование подписей узлов
        nx.draw_networkx_labels(G, pos, labels, font_size=12)

        # Рисование подписей ребер
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', rotate=False)

        # Удаление осей
        plt.axis('off')
        plt.savefig("graph.png", format="png")


# Вызов функции для теста
import asyncio

asyncio.run(fetch_data())
