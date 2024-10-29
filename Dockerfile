FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app
RUN apt-get update && \
    apt-get install -y wget ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*
# Устанавливаем системные зависимости для pygraphviz, Graphviz и antiword
RUN apt-get update && \
    apt-get install -y \
        graphviz \
        libgraphviz-dev \
        gcc \
        g++ \
        antiword && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
RUN pip install -r requirements.txt --no-cache-dir

# Загружаем модель для spaCy
RUN python -m spacy download ru_core_news_sm

# Указываем команду по умолчанию для запуска приложения
CMD ["python", "main.py"]
