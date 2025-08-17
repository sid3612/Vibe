#!/usr/bin/env python3
"""
CVR Auto-Analyzer - автоматический анализ проблем в воронке
Итерация 4: Автодетект проблем (CVR<10%), выбор гипотез и генерация рекомендаций через ChatGPT
"""

import json
import asyncio
from typing import Dict, List, Tuple, Optional
from db import get_profile, get_user_history, get_reflection_history
from hypotheses_manager import HypothesesManager
from metrics import calculate_cvr_metrics
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI library not installed. Install with: pip install openai")


class CVRAutoAnalyzer:
    """Автоматический анализатор CVR для детекта проблем и генерации рекомендаций"""

    def __init__(self):
        self.hypotheses_manager = HypothesesManager()

        # Проверяем загрузились ли гипотезы
        if self.hypotheses_manager.hypotheses_data is not None:
            print(f"✅ CVR Analyzer: Загружено {len(self.hypotheses_manager.hypotheses_data)} гипотез из Excel")
        else:
            print("⚠️ CVR Analyzer: Используются встроенные гипотезы")

        # Правила выбора гипотез по CVR (согласно требованиям)
        self.cvr_hypothesis_mapping = {
            'CVR1': ['H1'],        # CVR1 < 20% = H1
            'CVR2': ['H1', 'H2'],  # CVR2 < 20% = H1, H2
            'CVR3': ['H3', 'H4'],  # CVR3 < 20% = H3, H4
            'CVR4': ['H5'],        # CVR4 < 20% = H5
        }

    def detect_cvr_problems(self, user_id: int) -> Dict[str, any]:
        """
        Автодетект проблем CVR (CVR<20% при знаменателе ≥5)

        Returns:
            Dict с найденными проблемами и соответствующими гипотезами
        """
        print(f"🔍 Анализ CVR для пользователя {user_id}...")

        # Получаем данные пользователя
        history = get_user_history(user_id)
        profile = get_profile(user_id)

        if not history:
            return {"problems": [], "message": "Недостаточно данных для анализа"}

        # Рассчитываем метрики для последних данных
        latest_data = self._get_latest_funnel_data(history, profile)
        if not latest_data:
            return {"problems": [], "message": "Нет актуальных данных воронки"}

        print(f"📊 Данные воронки: {latest_data}")

        funnel_type = latest_data.get('funnel_type', 'active')
        metrics = calculate_cvr_metrics(latest_data, funnel_type)
        if not metrics:
            return {"problems": [], "message": "Ошибка расчета метрик"}

        print(f"📈 Метрики CVR: {metrics}")

        # Ищем проблемные CVR
        problems = []

        # Получаем численные значения CVR из строковых представлений
        cvr_values = self._extract_cvr_numbers(metrics)

        # Определяем знаменатели для проверки (≥5)
        # CVR = числитель / знаменатель, поэтому знаменатель = предыдущий этап воронки
        if funnel_type == 'active':
            denominators = {
                'CVR1': latest_data.get('applications', 0),  # responses / applications
                'CVR2': latest_data.get('responses', 0),     # screenings / responses
                'CVR3': latest_data.get('screenings', 0),    # onsites / screenings
                'CVR4': latest_data.get('onsites', 0)        # offers / onsites
            }
        else:
            denominators = {
                'CVR1': latest_data.get('views', 0),         # incoming / views
                'CVR2': latest_data.get('incoming', 0),      # screenings / incoming
                'CVR3': latest_data.get('screenings', 0),    # onsites / screenings
                'CVR4': latest_data.get('onsites', 0)        # offers / onsites
            }

        cvr_checks = [
            ('CVR1', cvr_values.get('cvr1'), denominators.get('CVR1', 0)),
            ('CVR2', cvr_values.get('cvr2'), denominators.get('CVR2', 0)),
            ('CVR3', cvr_values.get('cvr3'), denominators.get('CVR3', 0)),
            ('CVR4', cvr_values.get('cvr4'), denominators.get('CVR4', 0))
        ]

        for cvr_name, cvr_value, denominator in cvr_checks:
            print(f"🔍 Проверка {cvr_name}: value={cvr_value}, denominator={denominator}")
            if self._is_problem_cvr(cvr_value, denominator):
                # Получаем соответствующие гипотезы
                hypothesis_ids = self.cvr_hypothesis_mapping.get(cvr_name, [])
                hypotheses = []

                # Добавляем только гипотезы согласно строгим правилам
                for h_id in hypothesis_ids:
                    hypothesis = self.hypotheses_manager.get_hypothesis(h_id)
                    if hypothesis:
                        hypotheses.append(hypothesis)

                print(f"📝 Для {cvr_name} найдено {len(hypotheses)} гипотез")

                problems.append({
                    'cvr_name': cvr_name,
                    'cvr_value': cvr_value,
                    'denominator': denominator,
                    'hypotheses': hypotheses,
                    'user_data': latest_data  # Добавляем данные пользователя в каждую проблему
                })

                print(f"❌ Проблема: {cvr_name} = {cvr_value:.1f}% (знаменатель: {denominator})")
            else:
                print(f"✅ {cvr_name} в норме: {cvr_value}% (знаменатель: {denominator})")

        return {
            "problems": problems,
            "user_data": latest_data,
            "profile": profile,
            "message": f"Найдено проблем: {len(problems)}" if problems else "Проблем не обнаружено"
        }

    def _extract_cvr_numbers(self, metrics: Dict[str, str]) -> Dict[str, Optional[float]]:
        """Извлекает численные значения CVR из строковых представлений"""
        cvr_values = {}
        for key, value in metrics.items():
            if value == "—":
                cvr_values[key] = None
            else:
                try:
                    # Удаляем символ % и конвертируем в число
                    numeric_value = float(value.replace('%', ''))
                    cvr_values[key] = numeric_value
                except (ValueError, AttributeError):
                    cvr_values[key] = None
        return cvr_values

    def _is_problem_cvr(self, cvr_value: Optional[float], denominator: int) -> bool:
        """Проверяет, является ли CVR проблемным (CVR<20% при знаменателе ≥5)"""
        if cvr_value is None or denominator < 5:
            return False
        return cvr_value < 20.0

    def _get_latest_funnel_data(self, history: List[Dict], profile: Dict) -> Optional[Dict]:
        """Получает последние данные воронки для анализа"""
        if not history:
            return None

        # Группируем по неделям и берем последнюю
        weeks = {}
        for row in history:
            week = row['week_start']
            if week not in weeks:
                weeks[week] = {}

            channel = row['channel_name']
            if channel not in weeks[week]:
                weeks[week][channel] = row

        # Берем последнюю неделю
        latest_week = max(weeks.keys())
        latest_week_data = weeks[latest_week]

        # Суммируем данные по всем каналам за неделю
        funnel_type = profile.get('preferred_funnel_type', 'active')

        if funnel_type == 'active':
            totals = {
                'applications': 0, 'responses': 0, 'screenings': 0,
                'onsites': 0, 'offers': 0, 'rejections': 0
            }
        else:
            totals = {
                'views': 0, 'incoming': 0, 'screenings': 0,
                'onsites': 0, 'offers': 0, 'rejections': 0
            }

        for channel_data in latest_week_data.values():
            for field in totals.keys():
                totals[field] += channel_data.get(field, 0)

        totals['week_start'] = latest_week
        totals['funnel_type'] = funnel_type

        return totals

    def prepare_chatgpt_data(self, user_id: int, problems: List[Dict]) -> Dict[str, any]:
        """
        Подготавливает пакет данных для отправки в ChatGPT

        Args:
            user_id: ID пользователя
            problems: Список найденных проблем CVR

        Returns:
            Dict с данными для ChatGPT
        """
        profile = get_profile(user_id)
        reflection_history = get_reflection_history(user_id, 5)  # Последние 5 рефлексий

        # Собираем все уникальные гипотезы
        all_hypotheses = []
        hypothesis_ids = set()

        for problem in problems:
            for hypothesis in problem.get('hypotheses', []):
                h_id = hypothesis.get('id')
                if h_id and h_id not in hypothesis_ids:
                    hypothesis_ids.add(h_id)
                    all_hypotheses.append(hypothesis)

        # Формируем срез воронки
        funnel_snapshot = self._create_funnel_snapshot(problems)

        chatgpt_data = {
            "user_profile": {
                "role": profile.get('role', 'Не указано'),
                "level": profile.get('level', 'Не указано'),
                "location": profile.get('location', 'Не указано'),
                "target_location": profile.get('target_location', 'Не указано'),
                "deadline_weeks": profile.get('deadline_weeks', 'Не указано'),
                "funnel_type": profile.get('preferred_funnel_type', 'active'),
                "salary_expectations": profile.get('salary_expectations'),
                "industries": profile.get('industries'),
                "competencies": profile.get('competencies')
            },
            "reflection_history": reflection_history,
            "funnel_snapshot": funnel_snapshot,
            "problems": problems,
            "hypotheses": all_hypotheses,
            "analysis_timestamp": "now"
        }

        return chatgpt_data

    def _create_funnel_snapshot(self, problems: List[Dict]) -> Dict[str, any]:
        """Создает снапшот воронки с проблемными местами"""
        if not problems:
            return {}

        # Берем данные из первой проблемы (они все должны быть с одной недели)
        sample_problem = problems[0]
        user_data = sample_problem.get('user_data', {})

        snapshot = {
            "week": user_data.get('week_start', 'Unknown'),
            "funnel_type": user_data.get('funnel_type', 'active'),
            "metrics": {},
            "problem_areas": []
        }

        # Добавляем метрики и проблемные области
        for problem in problems:
            cvr_name = problem['cvr_name']
            cvr_value = problem['cvr_value']

            snapshot["metrics"][cvr_name] = f"{cvr_value:.1f}%"
            snapshot["problem_areas"].append({
                "metric": cvr_name,
                "value": cvr_value,
                "status": "critical" if cvr_value < 5 else "low"
            })

        return snapshot

    def generate_recommendations_prompt(self, chatgpt_data: Dict[str, any]) -> str:
        """
        Генерирует промпт для ChatGPT на основе данных анализа

        Args:
            chatgpt_data: Подготовленные данные для анализа

        Returns:
            Строка с промптом для ChatGPT
        """
        profile = chatgpt_data["user_profile"]
        problems = chatgpt_data["problems"]
        hypotheses = chatgpt_data["hypotheses"]
        funnel_snapshot = chatgpt_data["funnel_snapshot"]

        prompt = f"""Привет! Ты HackOFFer AI-ментор по поиску работы. Проанализируй воронку кандидата и дай 10 персональных рекомендаций.

ПРОФИЛЬ КАНДИДАТА:
• Роль: {profile['role']}
• Уровень: {profile['level']}
• Локация: {profile['location']} → {profile['target_location']}
• Срок поиска: {profile['deadline_weeks']} недель
• Тип воронки: {"Активный поиск (подает заявки)" if profile['funnel_type'] == 'active' else "Пассивный поиск (находят его)"}

ПРОБЛЕМНЫЕ ОБЛАСТИ (CVR < 20% при знаменателе ≥5):"""

        for problem in problems:
            prompt += f"\n• {problem['cvr_name']}: {problem['cvr_value']:.1f}% (знаменатель: {problem['denominator']})"

        prompt += f"\n\nДОСТУПНЫЕ ГИПОТЕЗЫ ДЛЯ РЕШЕНИЯ:"

        for hypothesis in hypotheses:
            prompt += f"\n\n{hypothesis['id']} — {hypothesis['title']}"
            prompt += f"\n👉 {hypothesis['cvr_focus']}"
            prompt += f"\nВопрос: {hypothesis['question']}"
            prompt += f"\nДействия: {hypothesis['actions']}"
            prompt += f"\nЭффект: {hypothesis['effect']}"

        prompt += f"""

ЗАДАЧА:
1. Проанализируй проблемные CVR кандидата
2. Выбери наиболее релевантные гипотезы для его ситуации
3. Сгенерируй 10 персональных рекомендаций с учетом его профиля

ФОРМАТ ОТВЕТА:
Каждая рекомендация должна быть:
• Конкретной и выполнимой
• Привязанной к его роли ({profile['role']}) и уровню ({profile['level']})
• Нацеленной на улучшение конкретного CVR
• С примером или шаблоном где возможно

Начинай каждую рекомендацию с номера (1-10) и эмодзи."""

        return prompt

    async def get_chatgpt_recommendations(self, chatgpt_data: Dict[str, any]) -> Optional[str]:
        """
        Получает рекомендации от ChatGPT через API

        Args:
            chatgpt_data: Подготовленные данные для анализа

        Returns:
            Строка с рекомендациями от ChatGPT или None при ошибке
        """
        if not OPENAI_AVAILABLE or not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            print("⚠️ OpenAI API не настроен. Возвращаем промпт для ручного использования.")
            return None

        try:
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)

            prompt = self.generate_recommendations_prompt(chatgpt_data)

            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты HackOFFer AI-ментор по поиску работы. Анализируй воронку кандидата и давай персональные рекомендации."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=OPENAI_MAX_TOKENS,
                temperature=0.7
            )

            recommendations = response.choices[0].message.content.strip()
            print(f"✅ Получены рекомендации от ChatGPT ({len(recommendations)} символов)")
            return recommendations

        except Exception as e:
            print(f"❌ Ошибка при запросе к OpenAI API: {e}")
            return None


async def analyze_and_recommend_async(user_id: int, use_api: bool = True) -> Optional[Dict[str, any]]:
    """
    Асинхронная функция: анализирует CVR и получает рекомендации

    Args:
        user_id: ID пользователя
        use_api: Использовать ли OpenAI API для получения рекомендаций

    Returns:
        Dict с результатами анализа и рекомендациями
    """
    analyzer = CVRAutoAnalyzer()

    # Шаг 1: Детект проблем CVR
    analysis_result = analyzer.detect_cvr_problems(user_id)

    if not analysis_result["problems"]:
        return {
            "status": "no_problems",
            "message": analysis_result["message"],
            "recommendations": None
        }

    # Шаг 2: Подготовка данных для ChatGPT
    chatgpt_data = analyzer.prepare_chatgpt_data(user_id, analysis_result["problems"])

    # Шаг 3: Генерация промпта
    prompt = analyzer.generate_recommendations_prompt(chatgpt_data)

    # Шаг 4: Попытка получить рекомендации через API
    ai_recommendations = None
    if use_api:
        ai_recommendations = await analyzer.get_chatgpt_recommendations(chatgpt_data)

    return {
        "status": "problems_found",
        "problems": analysis_result["problems"],
        "chatgpt_data": chatgpt_data,
        "chatgpt_prompt": prompt,
        "ai_recommendations": ai_recommendations,
        "message": f"Найдено {len(analysis_result['problems'])} проблем CVR. " + 
                  ("Получены AI рекомендации." if ai_recommendations else "Готов промпт для ChatGPT.")
    }

def analyze_and_recommend(user_id: int) -> Optional[Dict[str, any]]:
    """
    Синхронная обертка для совместимости с существующим кодом
    """
    try:
        return asyncio.run(analyze_and_recommend_async(user_id, use_api=False))
    except RuntimeError:
        # Если уже в event loop, создаем новый loop в отдельном потоке
        import threading
        import concurrent.futures

        def run_analysis():
            return asyncio.run(analyze_and_recommend_async(user_id, use_api=False))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_analysis)
            return future.result()


if __name__ == "__main__":
    # Тестируем анализатор
    print("🧪 Тестирование CVR Auto-Analyzer...")

    # Создаем тестовый анализ
    analyzer = CVRAutoAnalyzer()
    print("✅ CVR Auto-Analyzer инициализирован")

    # Тестируем детекцию проблем
    test_problems = analyzer._is_problem_cvr(8.5, 10)  # Должно быть True
    test_no_problems = analyzer._is_problem_cvr(15.0, 10)  # Должно быть False
    test_low_denominator = analyzer._is_problem_cvr(5.0, 3)  # Должно быть False

    print(f"✅ Детекция проблем: {test_problems}, {not test_no_problems}, {not test_low_denominator}")
    print("🎉 CVR Auto-Analyzer готов к работе!")