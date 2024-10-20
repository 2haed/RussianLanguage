import os
from aiogram.types import Document
from aiogram import Bot


async def save_file(document, download_folder="downloads"):
    # Создаем папку, если она не существует
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Получаем путь для сохранения файла
    file_path = os.path.join(download_folder, document.file_name)

    # Загружаем файл
    await document.download(destination_file=file_path)

    return file_path
