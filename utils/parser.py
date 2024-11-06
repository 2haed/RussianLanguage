import subprocess
from datetime import datetime
from uuid import uuid4
import matplotlib.pyplot as plt
import networkx as nx
import spacy
from sqlalchemy import text, select
import aspose.words as aw
import os
from docx import Document
import tempfile
import asyncio
from db.database import SentenceToText, Sentence, Word, WordToSentence, UserInfo

nlp = spacy.load("ru_core_news_sm")
nlp.max_length = 3000000

class SentenceInfo:
    def __init__(self, text, sentence_number, sentence_id, text_id, meta_timestamp, user_id):
        self.text = text
        self.sentence_number = sentence_number
        self.sentence_id = sentence_id
        self.text_id = text_id
        self.meta_timestamp = meta_timestamp
        self.user_id = user_id

async def parse_text_and_save(text: str, user_id: int, session, user_name: str):
    existing_user = await session.execute(select(UserInfo).filter_by(user_id=user_id))
    user_record = existing_user.scalar()

    # Если пользователь не найден, добавляем его в таблицу
    if not user_record:
        new_user = UserInfo(user_id=user_id, user_name=user_name)
        session.add(new_user)
        
    text_id = uuid4()
    doc = nlp(text)
    time = datetime.now()

    sentence_number = 0
    for sent in doc.sents:
        sentence_number += 1

        sentence_id = uuid4()

        sentence_info = SentenceInfo(
            text=sent.text,
            sentence_number=sentence_number,
            sentence_id=sentence_id,
            text_id=text_id,
            meta_timestamp=time,
            user_id=user_id
        )

        new_sentence = Sentence(sentence_id=sentence_info.sentence_id, 
                                text=sentence_info.text, 
                                user_id=sentence_info.user_id
        )
        session.add(new_sentence)

        new_sentence_to_text = SentenceToText(
            sentence_id=sentence_info.sentence_id, text_id=sentence_info.text_id,
            sentence_number=sentence_info.sentence_number, 
            meta_timestamp=sentence_info.meta_timestamp
        )
        session.add(new_sentence_to_text)

        word_number = 0
        for token in sent:
            word_number += 1

            word_id = uuid4()

            if token.dep_ == 'conj':
                dep = token.head.dep_
            else:
                dep = token.dep_

            new_word = Word(word_id=word_id, text=str(token.text), pos=str(token.pos_), dep=str(dep), lemma=str(token.lemma_), head_idx=int(token.head.i))
            session.add(new_word)

            new_word_to_sentence = WordToSentence(word_id=word_id, 
                                                  sentence_id=sentence_info.sentence_id, 
                                                  word_number=token.i
        )
            session.add(new_word_to_sentence)

    await session.commit()

async def create_and_send_graph(session):
    G = nx.DiGraph()
    result = await session.execute(text("""
                select w.text as text, pos, dm.description as dep, head_idx, word_number as token_idx from word w
                join word_to_sentence using(word_id)
                join sentence using(sentence_id)
                join sentence_to_text using(sentence_id)
                join dep_mapping dm on w.dep = dm.code
            where meta_timestamp = (select max(meta_timestamp) from sentence_to_text)
                """))
    words = result.fetchall()

    if len(words) > 100:
        return False

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

    for dep in words_list:
        if dep["token_idx"] != dep["head_idx"]:
            G.add_edge(dep["head_idx"], dep["token_idx"])

    pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    plt.figure(figsize=(24, 16))

    labels = nx.get_node_attributes(G, 'label')
    nx.draw_networkx_nodes(G, pos, node_size=1500, node_color='lightblue')

    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=15)

    nx.draw_networkx_labels(G, pos, labels, font_size=12)

    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', rotate=False)

    plt.axis('off')
    plt.savefig("graph.png", format="png")
    plt.close()
    return True


async def process_file(file_content, file_extension):
    text_content = ""
    with tempfile.TemporaryDirectory() as temp_dir:
        if file_extension == '.txt':
            text_content = file_content.getvalue().decode('utf-8').strip()

        elif file_extension == ".docx":
            temp_file_path = os.path.join(temp_dir, 'temp.docx')
            with open(temp_file_path, 'wb') as f:
                f.write(file_content.getvalue())

            doc = Document(temp_file_path)

            text_content = "\n".join(paragraph.text.strip() for paragraph in doc.paragraphs)
            text_content = ' '.join(text_content.split())

        elif file_extension == ".doc":
            temp_doc_path = os.path.join(temp_dir, 'temp.doc')
            with open(temp_doc_path, 'wb') as f:
                f.write(file_content.getvalue())

            result = subprocess.run(['antiword', temp_doc_path], stdout=subprocess.PIPE, text=True)
            if result.returncode == 0:
                text_content = result.stdout.strip()
            else:
                raise Exception(f"Ошибка при чтении .doc файла: {result.stderr}")

    text_content = ' '.join(text_content.split())

    return text_content
