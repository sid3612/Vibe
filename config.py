import os

# Токен бота Telegram - получаем из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# OpenAI API конфигурация
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
OPENAI_MODEL = "gpt-4o-mini"  # Более доступная модель
OPENAI_MAX_TOKENS = 1000

# Настройки базы данных
DATABASE_NAME = "funnel_coach.db"

# Настройки напоминаний
REMINDER_TIMES = {
    'daily': {'hour': 18, 'minute': 0},
    'weekly': {'day_of_week': 0, 'hour': 10, 'minute': 0}  # понедельник
}

# Часовой пояс для напоминаний
TIMEZONE = "Europe/Moscow"
