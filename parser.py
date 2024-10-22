from datetime import datetime
from uuid import uuid4
import matplotlib.pyplot as plt
import networkx as nx
import spacy
from sqlalchemy import text
from db import SentenceToText, Sentence, Word, WordToSentence

nlp = spacy.load("ru_core_news_sm")
async def parse_text_and_save(text: str, session):
    # Генерируем UUID для текста
    text_id = uuid4()

    # Пропускаем текст через модель spaCy
    doc = nlp(text)
    time = datetime.now()

    sentence_number = 0
    for sent in doc.sents:
        sentence_number += 1

        # Генерируем UUID для предложения
        sentence_id = uuid4()

        # Сохраняем предложение в таблицу sentence
        new_sentence = Sentence(sentence_id=sentence_id, text=sent.text)
        session.add(new_sentence)

        # Сохраняем связь предложения с текстом в таблицу sentence_to_text
        new_sentence_to_text = SentenceToText(sentence_id=sentence_id, text_id=text_id, sentence_number=sentence_number, meta_timestamp=time)
        session.add(new_sentence_to_text)

        # Обрабатываем каждое слово в предложении
        word_number = 0
        for token in sent:
            word_number += 1

            # Генерируем UUID для слова
            word_id = uuid4()

            # Сохраняем слово в таблицу word с его частью речи и синтаксической связью
            new_word = Word(word_id=word_id, lemma=token.lemma_, text=token.text, pos=token.pos_, dep=token.dep_, head_idx=token.head.i, token_idx=token.i)
            session.add(new_word)

            # Сохраняем связь слова с предложением в таблицу word_to_sentence
            new_word_to_sentence = WordToSentence(word_id=word_id, sentence_id=sentence_id, word_number=word_number)
            session.add(new_word_to_sentence)

    # Коммитим все изменения
    await session.commit()

async def create_and_send_graph(session):
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

    if len(words > 100):
        return 1

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
    plt.close()  # Закрытие фигуры
    return 0




