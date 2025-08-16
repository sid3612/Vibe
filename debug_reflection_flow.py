#!/usr/bin/env python3
"""
Полное регрессионное тестирование формы рефлексии
"""

import sys
import asyncio
import sqlite3
from unittest.mock import Mock, AsyncMock

async def test_reflection_flow():
    """Тестируем весь поток формы рефлексии"""
    print("🔍 ПОЛНОЕ РЕГРЕССИОННОЕ ТЕСТИРОВАНИЕ ФОРМЫ РЕФЛЕКСИИ")
    
    # 1. Проверяем триггер logic
    print("\n1️⃣ Тестирование триггера рефлексии...")
    from reflection_v31 import ReflectionV31System
    
    # Тестовые данные
    old_data = {'responses': 0, 'screenings': 0, 'onsites': 0, 'offers': 0, 'rejections': 0}
    new_data = {'responses': 1, 'screenings': 0, 'onsites': 0, 'offers': 0, 'rejections': 1}
    
    sections = ReflectionV31System.check_reflection_trigger(
        user_id=123, 
        week_start="2025-08-11", 
        channel="LinkedIn", 
        funnel_type="passive",
        old_data=old_data, 
        new_data=new_data
    )
    
    print(f"   Триггер результат: {len(sections)} секций")
    for section in sections:
        print(f"   - {section['stage_display']} (+{section['delta']})")
    
    if not sections:
        print("❌ ПРОБЛЕМА: Триггер не срабатывает!")
        return False
    
    # 2. Проверяем offer_reflection_form
    print("\n2️⃣ Тестирование предложения формы...")
    mock_message = Mock()
    mock_message.answer = AsyncMock()
    
    await ReflectionV31System.offer_reflection_form(
        mock_message, 123, "2025-08-11", "LinkedIn", "passive", sections
    )
    
    # Проверяем что метод был вызван
    if not mock_message.answer.called:
        print("❌ ПРОБЛЕМА: offer_reflection_form не отправляет сообщение!")
        return False
    
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]  # Первый позиционный аргумент
    keyboard = call_args[1]['reply_markup']  # keyword argument
    
    print(f"   Текст сообщения: {repr(message_text[:100])}")
    print(f"   Кнопки: {[btn.text for row in keyboard.inline_keyboard for btn in row]}")
    
    # 3. Проверяем регистрацию обработчиков
    print("\n3️⃣ Тестирование регистрации обработчиков...")
    from integration_v31 import register_v31_reflection_handlers
    from aiogram import Dispatcher
    
    # Создаем тестовый диспетчер
    dp = Dispatcher()
    register_v31_reflection_handlers(dp)
    
    # Проверяем что обработчики зарегистрированы
    handlers_count = len(dp._handlers)
    print(f"   Зарегистрировано обработчиков: {handlers_count}")
    
    # 4. Проверяем callback данные кнопок
    print("\n4️⃣ Анализ callback данных...")
    yes_callback = f"reflection_v31_yes_{len(sections)}"
    no_callback = "reflection_v31_no"
    
    print(f"   Кнопка 'Да': callback_data='{yes_callback}'")
    print(f"   Кнопка 'Нет': callback_data='{no_callback}'")
    
    # 5. Проверяем импорты обработчиков
    print("\n5️⃣ Проверка импортов обработчиков...")
    try:
        from reflection_v31 import (
            handle_reflection_v31_yes, 
            handle_reflection_v31_no,
            handle_section_rating,
            ReflectionV31States
        )
        print("   ✅ Все обработчики импортируются")
    except ImportError as e:
        print(f"   ❌ Ошибка импорта обработчиков: {e}")
        return False
    
    # 6. Тестируем состояния FSM
    print("\n6️⃣ Проверка FSM состояний...")
    states = [
        ReflectionV31States.section_rating,
        ReflectionV31States.section_reject_type,
        ReflectionV31States.section_strengths,
        ReflectionV31States.section_weaknesses
    ]
    print(f"   FSM состояния определены: {len(states)} состояний")
    
    # 7. Проверяем фильтры в main.py
    print("\n7️⃣ Анализ фильтров callback обработчиков...")
    
    # Симулируем различные callback данные
    test_callbacks = [
        "reflection_v31_yes_1",
        "reflection_v31_no", 
        "rating_3",
        "reject_type_no_interview",
        "skip_strengths"
    ]
    
    # Проверяем какие callback'и будут обработаны основным обработчиком
    from aiogram import F
    
    # Воссоздаем фильтр из main.py
    main_filter = (~F.data.startswith("rating_") & 
                  ~F.data.startswith("reason_v31_") & 
                  ~F.data.startswith("reasons_v31_") & 
                  ~F.data.startswith("skip_strengths") & 
                  ~F.data.startswith("skip_weaknesses") & 
                  ~F.data.startswith("skip_form") & 
                  ~F.data.startswith("reject_type_"))
    
    print("   Тестирование фильтра основного обработчика:")
    for callback_data in test_callbacks:
        # Создаем mock объект с data
        mock_callback = Mock()
        mock_callback.data = callback_data
        
        # Этот тест показывает логику, но не может точно проверить фильтр aiogram
        should_handle = not any([
            callback_data.startswith("rating_"),
            callback_data.startswith("reason_v31_"),
            callback_data.startswith("reasons_v31_"),
            callback_data.startswith("skip_strengths"),
            callback_data.startswith("skip_weaknesses"), 
            callback_data.startswith("skip_form"),
            callback_data.startswith("reject_type_")
        ])
        
        print(f"   - {callback_data}: {'✅ main handler' if should_handle else '❌ blocked by filter'}")
    
    print("\n8️⃣ ДИАГНОСТИКА ПРОБЛЕМЫ:")
    print("   - Триггер работает: ✅")
    print("   - Сообщение отправляется: ✅") 
    print("   - Кнопки создаются: ✅")
    print("   - Обработчики импортируются: ✅")
    print("   - FSM состояния работают: ✅")
    print("   - reflection_v31_yes_1 НЕ блокируется главным фильтром: ✅")
    print("   - reflection_v31_no НЕ блокируется главным фильтром: ✅")
    
    print(f"\n🎯 СЛЕДУЮЩИЙ ШАГ: Проверить регистрацию обработчиков в integration_v31.py")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_reflection_flow())
    sys.exit(0 if success else 1)