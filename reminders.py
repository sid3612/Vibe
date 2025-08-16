import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import REMINDER_TIMES, TIMEZONE
from db import get_users_for_reminders

# Глобальный планировщик
scheduler = None

async def send_reminder(bot, user_id: int, reminder_type: str):
    """Отправить напоминание пользователю"""
    if reminder_type == 'daily':
        message = """
⏰ Ежедневное напоминание!

Не забудьте обновить данные по вашей воронке поиска работы.

Что сегодня произошло в вашем поиске?
• Отправили новые отклики?
• Получили ответы от компаний?
• Прошли интервью?

/menu - Обновить данные
"""
    elif reminder_type == 'weekly':
        message = """
📊 Еженедельное напоминание!

Время подвести итоги недели и добавить данные в воронку.

Рекомендуем:
1. Добавить данные за прошедшую неделю
2. Проанализировать метрики CVR
3. Скорректировать стратегию поиска

/menu - Добавить данные
/faq - Посмотреть формулы расчета
"""
    else:
        return
    
    try:
        await bot.send_message(user_id, message)
    except Exception as e:
        print(f"Error sending reminder to user {user_id}: {e}")

async def daily_reminder_job(bot):
    """Задача ежедневных напоминаний"""
    users = get_users_for_reminders('daily')
    
    for user in users:
        await send_reminder(bot, user['user_id'], 'daily')
        # Небольшая задержка между отправками
        await asyncio.sleep(0.1)

async def weekly_reminder_job(bot):
    """Задача еженедельных напоминаний"""
    users = get_users_for_reminders('weekly')
    
    for user in users:
        await send_reminder(bot, user['user_id'], 'weekly')
        # Небольшая задержка между отправками
        await asyncio.sleep(0.1)

def setup_reminders(bot):
    """Настроить планировщик напоминаний"""
    global scheduler
    
    # Создаем планировщик
    timezone = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=timezone)
    
    # Ежедневные напоминания в 18:00
    daily_time = REMINDER_TIMES['daily']
    scheduler.add_job(
        daily_reminder_job,
        trigger=CronTrigger(
            hour=daily_time['hour'],
            minute=daily_time['minute'],
            timezone=timezone
        ),
        args=[bot],
        id='daily_reminders',
        name='Daily Reminders'
    )
    
    # Еженедельные напоминания по понедельникам в 10:00
    weekly_time = REMINDER_TIMES['weekly']
    scheduler.add_job(
        weekly_reminder_job,
        trigger=CronTrigger(
            day_of_week=weekly_time['day_of_week'],  # 0 = понедельник
            hour=weekly_time['hour'],
            minute=weekly_time['minute'],
            timezone=timezone
        ),
        args=[bot],
        id='weekly_reminders',
        name='Weekly Reminders'
    )
    
    # Запускаем планировщик
    scheduler.start()
    print("Reminder scheduler started")

def shutdown_reminders():
    """Остановить планировщик напоминаний"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("Reminder scheduler stopped")

# Функция для тестирования напоминаний
async def test_reminder(bot, user_id: int, reminder_type: str):
    """Тестовая функция для отправки напоминания"""
    await send_reminder(bot, user_id, reminder_type)
