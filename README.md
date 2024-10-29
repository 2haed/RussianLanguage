# Russian Language
## Описание проекта
Проект **Russian Syntax Analyzer** предназначен для анализа текста на русском языке с разбиением каждого предложения на члены предложения. Программа обрабатывает текстовые файлы форматов `.txt` и `.doc`, выводит результат на экран с выделенными членами предложения и предоставляет возможность анализа статистики.
### Основные функции:
1. **Разбиение предложений на члены предложения**: Программа анализирует текст и выделяет его грамматические структуры, включая подлежащее, сказуемое, дополнение и другие члены предложения.
2. **Выделение отдельных членов предложения**: Пользователь может запросить вывод только отдельных частей грамматических структур (например, только подлежащих или только дополнений).
3. **Статистика использования членов предложения**: Программа выводит статистику по частоте встречаемости различных слов в качестве членов предложения.
4. **Просмотр содержимого базы данных**: Результаты анализа сохраняются в базе данных, и пользователь может просматривать записи.
5. **Распознавание текста с точностью >75%**: Проект нацелен на точность синтаксического разбора выше 75%.
6. **Приемлемая производительность**: Программа оптимизирована для работы с большими текстовыми объемами без задержек.
   
## Стек технологий
- Язык программирования: **Python**
- Библиотеки:
  - [Aiogram](https://github.com/aiogram/aiogram) — для взаимодействия с Telegram API.
  - [SQLAlchemy](https://www.sqlalchemy.org/) — для работы с базой данных.
  - [Spacy](https://spacy.io/models/ru) — для синтаксического разбора
  - [Matplotlib](https://matplotlib.org/) — для визуализации статистики.
- Форматы входных данных: `.txt`, `.doc`
- База данных: **PostgreSQL**
- **Docker** для контейнеризации 
## Установка
1. **Клонируйте репозиторий**:
```bash
git clone https://github.com/2haed/RussianLanguage.git
cd RussianLanguage
```
## Использование
1. **Запуск**
Для запуска проекта используйте следующую команду:
```
docker-compose up --build
```
2. **Команды бота**:
   - `/start` — Начало работы с ботом, информация о проекте.
   - `/help` — Просмотр списка команд.
   - `/init` — Запросить файл для анализа.
   - `/stats` - Блок со статистикой
   - `/leaderboard` — Таблица лидеров 
3. **Функции анализа текста**:
   После отправки команды `/init` пользователь может загрузить текстовый файл и выбрать способ отображения результатов:
   - **Текст**: Выводит текст с выделенными членами предложения.
   - **Картинка**: Визуализирует синтаксический разбор.
   - **Статистика**: Отображает частотную статистику по членам предложения.
4. **Таблица лидеров**:
   Показывает таблицу лидеров, по количеству загруженных слов, файлов
5. **Статистика**:
   - **Кнопка Графики** — Выводит графики
      - **Распределение частей речи** — Этот график демонстрирует, как различные части речи (существительные, глаголы, прилагательные и т.д.) распределены в тексте.
      - **Распределение синтаксических зависимостей** — На этом графике представлены синтаксические зависимости между словами в предложениях. Он показывает, как слова связаны друг с другом и какие зависимости наиболее распространены.
      - **Длина предложений** — График длины предложений отображает количество слов или символов в каждом предложении.
      - **Топ 10 частотных слов** — Данный график показывает 10 наиболее часто встречающихся слов в тексте.
      - **Часть речи и длина предложений** — Этот график иллюстрирует взаимосвязь между частями речи и длиной предложений. 
      - **Статистика синтаксиса пользователей** — График представляет синтаксическую статистику, собранную от разных пользователей.
      - **Длина предложений с течением времени** — Этот график показывает, как длина предложений менялась с течением времени. 
      - **Корреляция частей речи и зависимостей** — На этом графике представлена корреляция между частями речи и их синтаксическими зависимостями.
   - **Кнопка Отчеты** — Выводит агрегированный отчет в excel
## Архитектура проекта (MVC)
Проект реализован по методологии MVC (Model-View-Controller):
- **Model**: Обрабатывает и сохраняет данные. Для этого используется SQLAlchemy для взаимодействия с базой данных.
- **View**: Визуализирует результаты анализа для пользователя. Это могут быть текстовые ответы или графики.
- **Controller**: Управляет логикой работы бота, обрабатывает команды и запросы пользователя.
## База данных
Результаты анализа сохраняются в базе данных для последующего использования. Структура базы данных состоит из следующих таблиц:
- **sentence**: Сохраненные предложения.
- **sentence_to_text**: Мэппинг предложений и текста.
- **word_to_sentence**: Мэппинг предложений и слов.
- **word**: Слова, разбитые по членам предложения.
- **dep_mapping**: Мэппинг членов предложений.
- **dep_formats**: Форматирование членов предложения.
- **pos_mapping**: Мэппинг частей речи
- **user_info**: Данные по Юзеру 