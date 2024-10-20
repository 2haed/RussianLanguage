import datetime
import spacy
from db import SentenceToText, Sentence, Word, WordToSentence
from uuid import uuid4
import networkx as nx
import graphviz
from sqlalchemy import text
import matplotlib.pyplot as plt

nlp = spacy.load("ru_core_news_sm")
async def parse_text_and_save(text: str, session):
    # Генерируем UUID для текста
    text_id = uuid4()

    # Пропускаем текст через модель spaCy
    doc = nlp(text)

    sentence_number = 0
    for sent in doc.sents:
        sentence_number += 1

        # Генерируем UUID для предложения
        sentence_id = uuid4()

        # Сохраняем предложение в таблицу sentence
        new_sentence = Sentence(sentence_id=sentence_id, text=sent.text)
        session.add(new_sentence)

        # Сохраняем связь предложения с текстом в таблицу sentence_to_text
        new_sentence_to_text = SentenceToText(sentence_id=sentence_id, text_id=text_id, sentence_number=sentence_number, meta_timestamp=datetime.now())
        session.add(new_sentence_to_text)

        # Обрабатываем каждое слово в предложении
        word_number = 0
        for token in sent:
            word_number += 1

            # Генерируем UUID для слова
            word_id = uuid4()

            # Сохраняем слово в таблицу word с его частью речи и синтаксической связью
            new_word = Word(word_id=word_id, text=token.text, pos=token.pos_, dep=token.dep_, head_idx=token.head.i, token_idx=token.i)
            session.add(new_word)

            # Сохраняем связь слова с предложением в таблицу word_to_sentence
            new_word_to_sentence = WordToSentence(word_id=word_id, sentence_id=sentence_id, word_number=word_number)
            session.add(new_word_to_sentence)

    # Коммитим все изменения
    await session.commit()

async def create_and_send_graph(session):
    # Создание графа
    G = nx.DiGraph()

    # Извлечение данных из базы данных
    # Измените запрос на получение данных из таблицы word
    result = await session.execute(text("""
    select * from word w
    """))
    words = result.scalars().all()
    print(words)
    # Добавление узлов и ребер в граф
    for word in words:
        node_label = f"{word.text}\n ({word.dep})"
        G.add_node(word.token_idx, label=node_label)

    for word in words:
        if word.token_idx != word.head_idx:  # Добавление ребер
            G.add_edge(word.head_idx, word.token_idx)

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

    # Удаление осей
    plt.axis('off')

    # Сохранение графа в файл
    graph_file_path = f"graph.png"  # Генерация уникального имени файла
    plt.savefig(graph_file_path)
    plt.close()  # Закрытие фигуры после сохранения



