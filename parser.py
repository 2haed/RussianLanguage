async def parse_file(file_path):
    # Открываем файл для чтения
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    # Просто возвращаем текст
    return text