#!/usr/bin/env python3
"""
Модуль для работы с гипотезами CVR оптимизации

Этот модуль предназначен для:
- Чтения гипотез из Excel файла
- Анализа CVR данных пользователя
- Подготовки данных для отправки в ChatGPT
- Генерации персонализированных рекомендаций

Планируется к реализации в следующей итерации.
"""

import pandas as pd
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class HypothesesManager:
    """Менеджер гипотез для CVR оптимизации"""
    
    def __init__(self, excel_file_path: str = "hypotheses.xlsx"):
        """
        Инициализация менеджера гипотез
        
        Args:
            excel_file_path: Путь к Excel файлу с гипотезами
        """
        self.excel_file_path = excel_file_path
        self.hypotheses_data = None
        
    def load_hypotheses(self) -> Optional[pd.DataFrame]:
        """
        Загрузить гипотезы из Excel файла
        
        Returns:
            DataFrame с гипотезами или None если ошибка
        """
        try:
            # Попытка чтения Excel файла
            df = pd.read_excel(self.excel_file_path)
            self.hypotheses_data = df
            return df
        except Exception as e:
            print(f"Ошибка при чтении файла гипотез: {e}")
            return None
    
    def get_user_cvr_analysis(self, user_id: int) -> Dict:
        """
        Получить анализ CVR данных пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с анализом CVR
        """
        from db import get_user_history
        from metrics import calculate_metrics_for_history
        
        history = get_user_history(user_id)
        if not history:
            return {"error": "Нет данных для анализа"}
        
        # Рассчитываем метрики
        metrics = calculate_metrics_for_history(history)
        
        # Анализируем тренды
        analysis = {
            "total_weeks": len(set(row['week_start'] for row in history)),
            "channels": list(set(row['channel_name'] for row in history)),
            "avg_cvr1": self._calculate_avg_cvr(metrics, 'cvr1'),
            "avg_cvr2": self._calculate_avg_cvr(metrics, 'cvr2'),
            "avg_cvr3": self._calculate_avg_cvr(metrics, 'cvr3'),
            "avg_cvr4": self._calculate_avg_cvr(metrics, 'cvr4'),
            "problem_areas": self._identify_problem_areas(metrics),
            "last_activity": max(row['week_start'] for row in history)
        }
        
        return analysis
    
    def prepare_chatgpt_prompt(self, user_id: int) -> Optional[str]:
        """
        Подготовить промпт для ChatGPT с данными пользователя и гипотезами
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Строка промпта для ChatGPT или None если ошибка
        """
        # Загружаем гипотезы
        if self.hypotheses_data is None:
            self.load_hypotheses()
        
        if self.hypotheses_data is None:
            return None
        
        # Получаем анализ пользователя
        user_analysis = self.get_user_cvr_analysis(user_id)
        if "error" in user_analysis:
            return None
        
        # Формируем промпт
        prompt = f"""
Проанализируй данные воронки поиска работы пользователя и предложи персонализированные рекомендации.

ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
- Общее количество недель активности: {user_analysis['total_weeks']}
- Каналы поиска: {', '.join(user_analysis['channels'])}
- Средний CVR1 (Ответы/Подачи): {user_analysis['avg_cvr1']:.1f}%
- Средний CVR2 (Скрининги/Ответы): {user_analysis['avg_cvr2']:.1f}%
- Средний CVR3 (Онсайты/Скрининги): {user_analysis['avg_cvr3']:.1f}%
- Средний CVR4 (Офферы/Онсайты): {user_analysis['avg_cvr4']:.1f}%
- Проблемные области: {', '.join(user_analysis['problem_areas'])}
- Последняя активность: {user_analysis['last_activity']}

ДОСТУПНЫЕ ГИПОТЕЗЫ ДЛЯ ОПТИМИЗАЦИИ:
{self._format_hypotheses_for_prompt()}

ЗАДАЧА:
На основе данных пользователя и доступных гипотез предложи 3-5 наиболее релевантных рекомендаций для улучшения CVR. 
Каждая рекомендация должна включать:
1. Конкретную гипотезу из списка
2. Обоснование почему она подходит этому пользователю
3. Практические шаги для реализации
4. Ожидаемый результат
"""
        return prompt
    
    def _calculate_avg_cvr(self, metrics: List[Dict], cvr_field: str) -> float:
        """Рассчитать средний CVR"""
        cvr_values = [m[cvr_field] for m in metrics if m[cvr_field] != "—"]
        if not cvr_values:
            return 0.0
        return sum(cvr_values) / len(cvr_values)
    
    def _identify_problem_areas(self, metrics: List[Dict]) -> List[str]:
        """Определить проблемные области на основе низких CVR"""
        problems = []
        
        avg_cvr1 = self._calculate_avg_cvr(metrics, 'cvr1')
        avg_cvr2 = self._calculate_avg_cvr(metrics, 'cvr2')
        avg_cvr3 = self._calculate_avg_cvr(metrics, 'cvr3')
        avg_cvr4 = self._calculate_avg_cvr(metrics, 'cvr4')
        
        if avg_cvr1 < 10:
            problems.append("Низкий отклик на подачи")
        if avg_cvr2 < 30:
            problems.append("Проблемы на этапе скрининга")
        if avg_cvr3 < 50:
            problems.append("Сложности с прохождением на онсайт")
        if avg_cvr4 < 30:
            problems.append("Низкое количество офферов")
            
        return problems or ["Нет критических проблем"]
    
    def _format_hypotheses_for_prompt(self) -> str:
        """Форматировать гипотезы для промпта"""
        if self.hypotheses_data is None:
            return "Гипотезы недоступны"
        
        # Преобразуем DataFrame в читаемый формат
        try:
            formatted = []
            for idx, row in self.hypotheses_data.iterrows():
                # Предполагаем стандартную структуру Excel файла
                formatted.append(f"- {row.iloc[0]}: {row.iloc[1]}")
            return "\n".join(formatted)
        except Exception as e:
            return f"Ошибка форматирования гипотез: {e}"

# Функции для интеграции с существующей системой
def get_hypotheses_for_user(user_id: int) -> Optional[str]:
    """
    Получить рекомендации по гипотезам для пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Промпт для ChatGPT или None
    """
    manager = HypothesesManager()
    return manager.prepare_chatgpt_prompt(user_id)

def analyze_user_performance(user_id: int) -> Dict:
    """
    Проанализировать производительность пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Словарь с анализом
    """
    manager = HypothesesManager()
    return manager.get_user_cvr_analysis(user_id)

if __name__ == "__main__":
    # Тестирование модуля
    print("Модуль гипотез загружен")
    print("Файл hypotheses.xlsx готов для анализа")
    
    # Попытка загрузить и показать структуру файла
    manager = HypothesesManager()
    df = manager.load_hypotheses()
    
    if df is not None:
        print(f"\nСтруктура файла гипотез:")
        print(f"Количество строк: {len(df)}")
        print(f"Столбцы: {list(df.columns)}")
        print(f"\nПервые несколько строк:")
        print(df.head())
    else:
        print("\nНе удалось загрузить файл. Убедитесь что установлен openpyxl:")
        print("pip install openpyxl")