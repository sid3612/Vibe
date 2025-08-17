
#!/usr/bin/env python3
"""
Тест проверки системы после изменения порога CVR с 10% до 20%
"""

import sys
sys.path.append('.')

from cvr_autoanalyzer import CVRAutoAnalyzer

def test_new_threshold():
    """Тестирование нового порога CVR 20%"""
    print("🧪 Тестирование порога CVR 20%...")
    
    analyzer = CVRAutoAnalyzer()
    
    # Тест 1: Значения ниже 20% должны быть проблемными
    test_cases = [
        (15.0, 10, True),   # CVR 15% < 20% = проблема
        (8.5, 10, True),    # CVR 8.5% < 20% = проблема  
        (25.0, 10, False),  # CVR 25% > 20% = норма
        (20.0, 10, False),  # CVR 20% = норма (граничное)
        (19.9, 10, True),   # CVR 19.9% < 20% = проблема
        (5.0, 3, False),    # Знаменатель < 5 = игнорируем
    ]
    
    print("\n🔍 Тестирование логики детекции проблем:")
    all_passed = True
    
    for cvr_value, denominator, expected in test_cases:
        result = analyzer._is_problem_cvr(cvr_value, denominator)
        status = "✅" if result == expected else "❌"
        print(f"  {status} CVR {cvr_value}%, знаменатель {denominator}: {result} (ожидалось {expected})")
        if result != expected:
            all_passed = False
    
    # Тест 2: Правила выбора гипотез не изменились
    print("\n📝 Проверка правил выбора гипотез:")
    expected_mapping = {
        'CVR1': ['H1'],
        'CVR2': ['H1', 'H2'], 
        'CVR3': ['H3', 'H4'],
        'CVR4': ['H5']
    }
    
    mapping_correct = analyzer.cvr_hypothesis_mapping == expected_mapping
    print(f"  {'✅' if mapping_correct else '❌'} Правила выбора гипотез: {mapping_correct}")
    if not mapping_correct:
        all_passed = False
        print(f"    Ожидалось: {expected_mapping}")
        print(f"    Получено: {analyzer.cvr_hypothesis_mapping}")
    
    # Тест 3: Извлечение численных значений
    print("\n🔢 Проверка извлечения CVR значений:")
    test_metrics = {
        'cvr1': '15%',
        'cvr2': '25%', 
        'cvr3': '—',
        'cvr4': '18%'
    }
    
    cvr_values = analyzer._extract_cvr_numbers(test_metrics)
    expected_values = {'cvr1': 15.0, 'cvr2': 25.0, 'cvr3': None, 'cvr4': 18.0}
    
    extraction_correct = cvr_values == expected_values
    print(f"  {'✅' if extraction_correct else '❌'} Извлечение CVR: {extraction_correct}")
    if not extraction_correct:
        all_passed = False
        print(f"    Ожидалось: {expected_values}")
        print(f"    Получено: {cvr_values}")
    
    print(f"\n{'🎉' if all_passed else '⚠️'} Результат тестирования: {'ВСЕ ТЕСТЫ ПРОШЛИ' if all_passed else 'ЕСТЬ ПРОБЛЕМЫ'}")
    return all_passed

if __name__ == "__main__":
    success = test_new_threshold()
    sys.exit(0 if success else 1)
