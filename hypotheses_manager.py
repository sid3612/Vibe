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
        # Автоматически загружаем гипотезы при инициализации
        self.load_hypotheses()

        # Встроенные гипотезы на случай отсутствия Excel файла
        self.built_in_hypotheses = {
            'H1': {
                'id': 'H1',
                'title': 'Позиционирование профиля',
                'cvr_focus': 'CVR1 (Подачи → Ответы)',
                'question': 'Соответствует ли ваш профиль ожиданиям работодателей?',
                'actions': 'Оптимизация резюме, профиля LinkedIn, сопроводительных писем',
                'effect': 'Увеличение количества ответов на подачи'
            },
            'H2': {
                'id': 'H2', 
                'title': 'Каналы поиска',
                'cvr_focus': 'CVR1-CVR2 (Подачи → Ответы → Скрининги)',
                'question': 'Используете ли вы правильные каналы для вашей роли?',
                'actions': 'Диверсификация каналов, фокус на нишевых площадках',
                'effect': 'Улучшение качества откликов и прохождения скрининга'
            },
            'H3': {
                'id': 'H3',
                'title': 'Подготовка к скринингу',
                'cvr_focus': 'CVR2-CVR3 (Скрининги → Онсайты)',
                'question': 'Готовы ли вы к первичным разговорам с HR?',
                'actions': 'Подготовка elevator pitch, отработка частых вопросов',
                'effect': 'Увеличение прохождения на технические интервью'
            },
            'H4': {
                'id': 'H4',
                'title': 'Техническая подготовка',
                'cvr_focus': 'CVR3 (Онсайты → Офферы)',
                'question': 'Достаточна ли ваша техническая подготовка?',
                'actions': 'Изучение кейсов, решение задач, подготовка портфолио',
                'effect': 'Повышение успешности на технических интервью'
            },
            'H5': {
                'id': 'H5',
                'title': 'Переговоры об оффере',
                'cvr_focus': 'CVR4 (Онсайты → Офферы)',
                'question': 'Умеете ли вы правильно завершать интервью?',
                'actions': 'Подготовка вопросов компании, техники закрытия',
                'effect': 'Увеличение конверсии в офферы'
            }
        }

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
            print(f"✅ Загружено {len(df)} гипотез из {self.excel_file_path}")
            print(f"Столбцы: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"❌ Ошибка при чтении файла гипотез {self.excel_file_path}: {e}")
            print("Используются встроенные гипотезы")
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

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Dict]:
        """
        Получить гипотезу по ID

        Args:
            hypothesis_id: ID гипотезы (например, 'H1', 'H2', и т.д.)

        Returns:
            Словарь с данными гипотезы или None если не найдена
        """
        # Сначала пытаемся найти в загруженных из Excel данных
        if self.hypotheses_data is not None:
            try:
                # Ищем по столбцу hid (второй столбец)
                matching_rows = self.hypotheses_data[self.hypotheses_data['hid'].astype(str) == hypothesis_id]
                if not matching_rows.empty:
                    row = matching_rows.iloc[0]
                    return {
                        'id': hypothesis_id,
                        'title': f"Гипотеза {hypothesis_id}",
                        'description': row['name'] if 'name' in row else 'Без описания',
                        'cvr_focus': f"Тема: {row['h_topic']}" if 'h_topic' in row else 'Из базы гипотез',
                        'question': 'Подходит ли эта гипотеза для вашей ситуации?',
                        'actions': row['name'] if 'name' in row else 'Нет действий',
                        'effect': 'Улучшение конверсии'
                    }
            except Exception as e:
                print(f"Ошибка при поиске гипотезы в Excel: {e}")

        # Если не найдено в Excel или Excel не загружен, используем встроенные
        return self.built_in_hypotheses.get(hypothesis_id)

    def get_hypotheses_by_ids(self, hypothesis_ids: List[str]) -> List[Dict[str, str]]:
        """
        Получить гипотезы по списку ID

        Args:
            hypothesis_ids: Список ID гипотез (например, ['H1', 'H2'])

        Returns:
            Список словарей с гипотезами
        """
        hypotheses = []

        # Проверяем загружены ли данные из Excel
        if self.hypotheses_data is not None:
            print(f"🔍 Поиск гипотез в Excel для {hypothesis_ids}")

            for _, row in self.hypotheses_data.iterrows():
                if row['hid'] in hypothesis_ids:
                    hypothesis = {
                        'id': row['hid'],
                        'hid': row['hid'],
                        'name': row['name'],         # Полное содержимое гипотезы
                        'description': row['name'],  # Дублируем для совместимости
                        'actions': row['name'],      # Дублируем для совместимости
                        'effect': 'Улучшение конверсии'
                    }
                    hypotheses.append(hypothesis)
                    print(f"✅ Найдена гипотеза {row['hid']}: {row['name'][:100]}...")

            print(f"📊 Найдено {len(hypotheses)} гипотез в Excel для {hypothesis_ids}")
        else:
            # Fallback на встроенные гипотезы
            print(f"⚠️ Excel не загружен, используем встроенные гипотезы для {hypothesis_ids}")
            for h_id in hypothesis_ids:
                if h_id in self.built_in_hypotheses:
                    hypotheses.append(self.built_in_hypotheses[h_id])

        return hypotheses

    def get_random_hypotheses(self, count: int = 5) -> List[Dict]:
        """
        Получить случайные гипотезы из Excel файла

        Args:
            count: Количество гипотез для возврата

        Returns:
            Список гипотез
        """
        if self.hypotheses_data is None or len(self.hypotheses_data) == 0:
            # Возвращаем встроенные гипотезы
            return list(self.built_in_hypotheses.values())[:count]

        try:
            # Берем случайную выборку
            sample_size = min(count, len(self.hypotheses_data))
            random_rows = self.hypotheses_data.sample(n=sample_size)

            hypotheses = []
            for idx, row in random_rows.iterrows():
                h_id = str(row.iloc[1]) if len(row) > 1 else f"H{idx}"
                h_name = str(row.iloc[2]) if len(row) > 2 else "Без названия"

                hypotheses.append({
                    'id': h_id,
                    'title': f"Гипотеза {h_id}",
                    'description': h_name,
                    'cvr_focus': 'Из базы гипотез',
                    'question': 'Подходит ли эта гипотеза для вашей ситуации?',
                    'actions': h_name,
                    'effect': 'Улучшение конверсии'
                })

            return hypotheses
        except Exception as e:
            print(f"Ошибка при получении случайных гипотез: {e}")
            return list(self.built_in_hypotheses.values())[:count]

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
            # Используем встроенные гипотезы если Excel недоступен
            formatted = []
            for h_id, hypothesis in self.built_in_hypotheses.items():
                formatted.append(f"- {h_id}: {hypothesis['title']} - {hypothesis['actions']}")
            return "\n".join(formatted)

        # Преобразуем DataFrame в читаемый формат
        try:
            formatted = []
            for idx, row in self.hypotheses_data.iterrows():
                # Структура: h_topic, hid, name
                if len(row) >= 3:
                    h_id = str(row.iloc[1])  # hid
                    h_name = str(row.iloc[2])  # name
                    formatted.append(f"- {h_id}: {h_name[:200]}{'...' if len(h_name) > 200 else ''}")
                else:
                    formatted.append(f"- {row.iloc[0]}: {row.iloc[1] if len(row) > 1 else 'Нет описания'}")
            return "\n".join(formatted[:20])  # Ограничиваем до 20 гипотез для промпта
        except Exception as e:
            print(f"Ошибка форматирования гипотез: {e}")
            # Fallback к встроенным гипотезам
            formatted = []
            for h_id, hypothesis in self.built_in_hypotheses.items():
                formatted.append(f"- {h_id}: {hypothesis['title']} - {hypothesis['actions']}")
            return "\n".join(formatted)

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