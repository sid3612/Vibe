#!/usr/bin/env python3
"""
Простая отладка проблемы с кнопками рефлексии
"""

def check_main_py_callback_filter():
    """Проверим фильтр основного callback обработчика"""
    print("🔍 АНАЛИЗ ФИЛЬТРА CALLBACK ОБРАБОТЧИКА В MAIN.PY")
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Найдем строку с фильтром
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '@dp.callback_query' in line and '~F.data.startswith' in line:
            print(f"Строка {i+1}: {line.strip()}")
            
            # Анализируем какие callback'и блокируются
            blocked_prefixes = []
            if 'reflection_v31_' in line:
                blocked_prefixes.append('reflection_v31_')
            if 'rating_' in line:
                blocked_prefixes.append('rating_')
            if 'reason_v31_' in line:
                blocked_prefixes.append('reason_v31_')
            
            print(f"Заблокированные префиксы: {blocked_prefixes}")
            
            # Проверим тестовые callback'и
            test_callbacks = [
                "reflection_v31_yes_2",
                "reflection_v31_no", 
                "rating_3",
                "main_menu"
            ]
            
            for callback in test_callbacks:
                blocked = any(callback.startswith(prefix) for prefix in blocked_prefixes if 'reflection_v31_' not in blocked_prefixes)
                status = "BLOCKED" if blocked else "ALLOWED"
                print(f"   {callback}: {status}")
    
    return True

def check_integration_handlers():
    """Проверим обработчики в integration_v31.py"""
    print("\n📋 АНАЛИЗ ОБРАБОТЧИКОВ В INTEGRATION_V31.PY")
    
    with open('integration_v31.py', 'r') as f:
        content = f.read()
    
    # Ищем регистрацию обработчиков
    handlers_found = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if '@dp.callback_query' in line:
            # Следующая строка должна содержать def
            if i + 1 < len(lines):
                def_line = lines[i + 1].strip()
                print(f"Обработчик: {line.strip()}")
                print(f"   Функция: {def_line}")
                
                # Проверим фильтр
                if 'reflection_v31_yes_' in line:
                    handlers_found.append('yes_handler')
                elif 'reflection_v31_no' in line:
                    handlers_found.append('no_handler')
    
    print(f"Найдено обработчиков: {handlers_found}")
    return len(handlers_found) >= 2

def check_main_py_handler_registration():
    """Проверим регистрацию reflection обработчиков в main.py"""
    print("\n🔧 ПРОВЕРКА РЕГИСТРАЦИИ ОБРАБОТЧИКОВ В MAIN.PY")
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    registration_found = False
    lines = content.split('\n')
    
    for line in lines:
        if 'register_v31_reflection_handlers' in line:
            print(f"Найдена регистрация: {line.strip()}")
            registration_found = True
    
    if not registration_found:
        print("❌ ПРОБЛЕМА: Обработчики рефлексии НЕ зарегистрированы в main.py!")
        return False
    
    return True

def main():
    print("🚀 ПРОСТАЯ ОТЛАДКА ПРОБЛЕМЫ С КНОПКАМИ РЕФЛЕКСИИ")
    print("=" * 50)
    
    # 1. Проверим фильтр в main.py
    filter_ok = check_main_py_callback_filter()
    
    # 2. Проверим обработчики в integration_v31.py
    handlers_ok = check_integration_handlers()
    
    # 3. Проверим регистрацию в main.py
    registration_ok = check_main_py_handler_registration()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТ АНАЛИЗА:")
    print(f"   🔍 Фильтр callback: {'✅ OK' if filter_ok else '❌ ПРОБЛЕМА'}")
    print(f"   📋 Обработчики: {'✅ OK' if handlers_ok else '❌ ПРОБЛЕМА'}")
    print(f"   🔧 Регистрация: {'✅ OK' if registration_ok else '❌ ПРОБЛЕМА'}")
    
    if not registration_ok:
        print("\n🎯 НАЙДЕНА ПРОБЛЕМА!")
        print("   Обработчики reflection v3.1 не зарегистрированы в main.py")
        print("   Нужно добавить: register_v31_reflection_handlers(dp)")
        return False
    
    if filter_ok and handlers_ok and registration_ok:
        print("\n🤔 Все проверки прошли успешно, проблема может быть в другом месте")
    
    return True

if __name__ == "__main__":
    main()