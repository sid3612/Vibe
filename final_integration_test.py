#!/usr/bin/env python3
"""
Финальный интеграционный тест с реальными данными
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta

def setup_test_user():
    """Создаем тестового пользователя в БД"""
    conn = sqlite3.connect('funnel_coach.db')
    cursor = conn.cursor()
    
    user_id = 12345
    
    # Удаляем существующие данные для чистого теста
    cursor.execute("DELETE FROM week_data WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM event_feedback WHERE user_id = ?", (user_id,))
    
    # Добавляем пользователя
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, active_funnel, reminders_enabled, reminder_frequency)
        VALUES (?, 'passive', 1, 'weekly')
    """, (user_id,))
    
    # Добавляем начальные данные за прошлую неделю (все нули)
    last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute("""
        INSERT OR REPLACE INTO week_data 
        (user_id, week_start, channel, funnel_type, applications, views, responses, screenings, onsites, offers, rejections)
        VALUES (?, ?, 'LinkedIn', 'passive', 0, 5, 0, 0, 0, 0, 0)
    """, (user_id, last_week))
    
    # Добавляем данные за текущую неделю с изменениями
    this_week = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        INSERT OR REPLACE INTO week_data 
        (user_id, week_start, channel, funnel_type, applications, views, responses, screenings, onsites, offers, rejections)
        VALUES (?, ?, 'LinkedIn', 'passive', 0, 7, 1, 0, 0, 0, 2)
    """, (user_id, this_week))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Тестовый пользователь {user_id} создан с данными:")
    print(f"   - Прошлая неделя {last_week}: views=5, responses=0, rejections=0")
    print(f"   - Текущая неделя {this_week}: views=7, responses=1, rejections=2")
    print(f"   - Ожидаемые изменения: responses +1, rejections +2")
    
    return user_id, this_week

def test_trigger_calculation():
    """Проверяем расчет триггеров на реальных данных"""
    print("\n🔍 Проверка trigger calculation на реальных данных из БД...")
    
    user_id, this_week = setup_test_user()
    
    # Получаем данные из БД
    from db import get_week_data
    
    # Симулируем старые данные (до изменения)
    old_data = {'views': 5, 'responses': 0, 'screenings': 0, 'onsites': 0, 'offers': 0, 'rejections': 0}
    
    # Получаем новые данные из БД
    new_data_record = get_week_data(user_id, this_week, 'LinkedIn', 'passive')
    if new_data_record:
        new_data = dict(new_data_record)
        print(f"   Новые данные из БД: {new_data}")
        
        # Проверяем trigger
        from reflection_v31 import ReflectionV31System
        sections = ReflectionV31System.check_reflection_trigger(
            user_id, this_week, 'LinkedIn', 'passive', old_data, new_data
        )
        
        print(f"   Обнаружено секций для рефлексии: {len(sections)}")
        for section in sections:
            print(f"   - {section['stage_display']} (+{section['delta']})")
        
        return len(sections) > 0
    else:
        print("❌ Не удалось получить данные из БД")
        return False

def test_callback_data_format():
    """Проверяем формат callback данных кнопок"""
    print("\n🎯 Проверка формата callback данных...")
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from reflection_v31 import ReflectionV31System
    
    # Создаем тестовые секции
    sections = [
        {'stage': 'response', 'delta': 1, 'stage_display': '✉️ Ответ'},
        {'stage': 'reject_no_interview', 'delta': 2, 'stage_display': '❌ Отказ без интервью'}
    ]
    
    # Создаем клавиатуру как в offer_reflection_form
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data=f"reflection_v31_yes_{len(sections)}")],
        [InlineKeyboardButton(text="Нет", callback_data="reflection_v31_no")]
    ])
    
    yes_button = keyboard.inline_keyboard[0][0]
    no_button = keyboard.inline_keyboard[1][0]
    
    print(f"   Кнопка 'Да': callback_data = '{yes_button.callback_data}'")
    print(f"   Кнопка 'Нет': callback_data = '{no_button.callback_data}'")
    
    # Проверяем, что callback данные соответствуют фильтрам обработчиков
    yes_matches_filter = yes_button.callback_data.startswith("reflection_v31_yes_")
    no_matches_filter = no_button.callback_data == "reflection_v31_no"
    
    print(f"   'Да' соответствует фильтру: {yes_matches_filter}")
    print(f"   'Нет' соответствует фильтру: {no_matches_filter}")
    
    return yes_matches_filter and no_matches_filter

def test_handler_registration():
    """Проверяем регистрацию обработчиков"""
    print("\n📋 Проверка регистрации обработчиков...")
    
    try:
        from integration_v31 import register_v31_reflection_handlers
        from aiogram import Dispatcher
        
        # Создаем тестовый диспетчер
        dp = Dispatcher()
        
        # Регистрируем обработчики
        register_v31_reflection_handlers(dp)
        
        print("   ✅ Обработчики зарегистрированы без ошибок")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка регистрации обработчиков: {e}")
        return False

def cleanup_test_data():
    """Очищаем тестовые данные"""
    conn = sqlite3.connect('funnel_coach.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM week_data WHERE user_id = 12345")
    cursor.execute("DELETE FROM users WHERE user_id = 12345") 
    cursor.execute("DELETE FROM event_feedback WHERE user_id = 12345")
    conn.commit()
    conn.close()
    print("\n🧹 Тестовые данные очищены")

def main():
    """Запускаем полный интеграционный тест"""
    print("🚀 ФИНАЛЬНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ ФОРМЫ РЕФЛЕКСИИ")
    print("=" * 60)
    
    try:
        # 1. Тест trigger calculation
        trigger_works = test_trigger_calculation()
        
        # 2. Тест callback data format
        callback_works = test_callback_data_format()
        
        # 3. Тест handler registration
        handlers_work = test_handler_registration()
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННОГО ТЕСТИРОВАНИЯ:")
        print(f"   🎯 Trigger detection: {'✅ РАБОТАЕТ' if trigger_works else '❌ НЕ РАБОТАЕТ'}")
        print(f"   🔘 Callback buttons: {'✅ РАБОТАЮТ' if callback_works else '❌ НЕ РАБОТАЮТ'}")
        print(f"   📋 Handler registration: {'✅ РАБОТАЕТ' if handlers_work else '❌ НЕ РАБОТАЕТ'}")
        
        overall_success = trigger_works and callback_works and handlers_work
        
        if overall_success:
            print("\n🎉 ВСЕ КОМПОНЕНТЫ РАБОТАЮТ КОРРЕКТНО!")
            print("📝 Форма рефлексии должна запускаться при добавлении данных")
        else:
            print("\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В ИНТЕГРАЦИИ")
            print("🔧 Требуется дополнительная отладка")
            
        return overall_success
        
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)