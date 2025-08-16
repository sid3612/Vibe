#!/usr/bin/env python3
"""
Отладка проблемы с неактивными кнопками
"""

def check_button_generation():
    """Проверим генерацию кнопок в offer_reflection_form"""
    print("🔍 ПРОВЕРКА ГЕНЕРАЦИИ КНОПОК")
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Тестовые секции как в реальном сценарии
    sections = [
        {'stage': 'response', 'delta': 1, 'stage_display': '✉️ Ответ'},
        {'stage': 'reject_no_interview', 'delta': 1, 'stage_display': '❌ Отказ'}
    ]
    
    # Создаем клавиатуру точно как в offer_reflection_form
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data=f"reflection_v31_yes_{len(sections)}")],
        [InlineKeyboardButton(text="Нет", callback_data="reflection_v31_no")]
    ])
    
    print(f"Количество секций: {len(sections)}")
    print(f"Кнопка 'Да': callback_data = '{keyboard.inline_keyboard[0][0].callback_data}'")
    print(f"Кнопка 'Нет': callback_data = '{keyboard.inline_keyboard[1][0].callback_data}'")
    
    # Проверим, что callback данные не содержат недопустимых символов
    yes_data = keyboard.inline_keyboard[0][0].callback_data
    no_data = keyboard.inline_keyboard[1][0].callback_data
    
    print(f"\nВалидация callback данных:")
    print(f"'Да' валидные данные: {len(yes_data) <= 64 and yes_data.isascii()}")
    print(f"'Нет' валидные данные: {len(no_data) <= 64 and no_data.isascii()}")
    
    return True

def check_handler_patterns():
    """Проверим соответствие callback данных паттернам обработчиков"""
    print("\n🎯 ПРОВЕРКА ПАТТЕРНОВ ОБРАБОТЧИКОВ")
    
    test_callbacks = [
        "reflection_v31_yes_1",
        "reflection_v31_yes_2", 
        "reflection_v31_no"
    ]
    
    # Проверяем паттерны из integration_v31.py
    for callback in test_callbacks:
        yes_match = callback.startswith("reflection_v31_yes_")
        no_match = callback == "reflection_v31_no"
        
        handler = "YES" if yes_match else "NO" if no_match else "NONE"
        print(f"Callback '{callback}' → обработчик: {handler}")
    
    return True

def check_stage_display_fix():
    """Проверим исправление отображения стадий"""
    print("\n📝 ПРОВЕРКА ИСПРАВЛЕНИЯ ТЕКСТА СТАДИЙ")
    
    from reflection_v31 import ReflectionV31System
    
    # Проверим исправленное отображение
    reject_display = ReflectionV31System.get_stage_display('reject_no_interview')
    print(f"reject_no_interview → '{reject_display}'")
    
    expected = "❌ Отказ"
    fixed = reject_display == expected
    print(f"Исправлено: {'✅' if fixed else '❌'} (ожидали '{expected}')")
    
    return fixed

def main():
    print("🧪 ДИАГНОСТИКА ПРОБЛЕМ С КНОПКАМИ РЕФЛЕКСИИ")
    print("=" * 50)
    
    # Тесты
    button_gen = check_button_generation()
    handler_patterns = check_handler_patterns()
    stage_fix = check_stage_display_fix()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
    print(f"   🔘 Генерация кнопок: {'✅' if button_gen else '❌'}")
    print(f"   🎯 Паттерны обработчиков: {'✅' if handler_patterns else '❌'}")
    print(f"   📝 Исправление текста: {'✅' if stage_fix else '❌'}")
    
    if all([button_gen, handler_patterns, stage_fix]):
        print("\n🎉 ВСЕ КОМПОНЕНТЫ РАБОТАЮТ!")
        print("💡 Если кнопки все еще не работают, проблема в регистрации или порядке обработчиков")
    else:
        print("\n⚠️  НАЙДЕНЫ ПРОБЛЕМЫ В КОМПОНЕНТАХ")
        
    return all([button_gen, handler_patterns, stage_fix])

if __name__ == "__main__":
    main()