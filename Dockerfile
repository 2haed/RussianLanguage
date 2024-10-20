FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download ru_core_news_sm

CMD ["python", "main.py"]