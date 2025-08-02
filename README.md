# Mulentiy Bot

Телеграм-бот на Aiogram 3 для подсчёта дневного заработка и ведения истории доходов.

## Требования
- Python 3.10+

## Установка и запуск

1. Склонируйте репозиторий и перейдите в каталог проекта.
2. (Опционально) создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создайте файл `.env` и укажите токен бота от BotFather:
   ```bash
   cp .env.example .env
   nano .env  # впишите значение BOT_TOKEN
   ```
   Пример содержимого:
   ```ini
   BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
   ```
5. Запустите бота:
   ```bash
   python bot.py
   ```

При первом запуске будет создан файл базы данных `bot.db` в корне проекта.

## Основные команды
- `/start` – начать расчёт и открыть меню
- `/history` – управлять историей записей
- `/help` – краткая справка
- `/cancel` – отменить текущий шаг
