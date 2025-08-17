#!/usr/bin/env python3
"""
CVR Auto-Analyzer - автоматический анализ проблем в воронке
Итерация 4: Автодетект проблем (CVR<20%), выбор гипотез и генерация рекомендаций через ChatGPT

Основные функции:
1. Автоматическое обнаружение проблем в воронке (CVR < 20% при знаменателе ≥ 5)
2. Подбор релевантных гипотез для каждой проблемы
3. Генерация персонализированных рекомендаций через ChatGPT API
4. Подготовка полного контекста пользователя для анализа
"""

import json
import asyncio
from typing import Dict, List, Tuple, Optional
from db import get_profile, get_user_history, get_reflection_history
from hypotheses_manager import HypothesesManager
from metrics import calculate_cvr_metrics
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS

# Проверяем доступность OpenAI библиотеки
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI library not installed. Install with: pip install openai")


class CVRAutoAnalyzer:
    """
    Автоматический анализатор CVR для детекта проблем и генерации рекомендаций
    
    Класс отвечает за:
    - Обнаружение проблем в воронке поиска работы
    - Подбор соответствующих гипотез для решения
    - Генерацию персональных рекомендаций через AI
    """

    def __init__(self):
        """Инициализация анализатора с загрузкой гипотез и настройкой правил"""
        # Загружаем менеджер гипотез для работы с базой знаний
        self.hypotheses_manager = HypothesesManager()

        # Проверяем успешность загрузки гипотез из Excel файла
        if self.hypotheses_manager.hypotheses_data is not None:
            print(f"✅ CVR Analyzer: Загружено {len(self.hypotheses_manager.hypotheses_data)} гипотез из Excel")
        else:
            print("⚠️ CVR Analyzer: Используются встроенные гипотезы")

        # Правила сопоставления проблемных CVR с соответствующими гипотезами
        # Каждый CVR имеет строго определенный набор гипотез для решения
        self.cvr_hypothesis_mapping = {
            'CVR1': ['H1'],        # Подачи → Ответы: проблемы позиционирования
            'CVR2': ['H1', 'H2'],  # Ответы → Скрининги: позиционирование + каналы
            'CVR3': ['H3', 'H4'],  # Скрининги → Онсайты: подготовка к собеседованиям
            'CVR4': ['H5'],        # Онсайты → Офферы: переговоры и финализация
        }

    def detect_cvr_problems(self, user_id: int) -> Dict[str, any]:
        """
        Основной метод для автоматического обнаружения проблем в воронке
        
        Алгоритм работы:
        1. Получение истории данных пользователя
        2. Расчет актуальных CVR метрик
        3. Проверка каждого CVR на соответствие критериям проблемы
        4. Подбор релевантных гипотез для каждой найденной проблемы
        
        Args:
            user_id: Идентификатор пользователя в системе
            
        Returns:
            Dict с результатами анализа:
            - problems: список найденных проблем с гипотезами
            - user_data: актуальные данные воронки
            - profile: профиль пользователя
            - message: статус анализа
        """
        print(f"🔍 Анализ CVR для пользователя {user_id}...")

        # Получаем историю воронки и профиль пользователя из базы данных
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

        # Начинаем поиск проблемных CVR (конверсий меньше 20%)
        problems = []

        # Извлекаем численные значения CVR из строковых представлений (например, "15%" → 15.0)
        cvr_values = self._extract_cvr_numbers(metrics)

        # Определяем знаменатели для каждого CVR (нужны для проверки достаточности данных ≥5)
        # CVR = числитель / знаменатель, где знаменатель = количество записей на предыдущем этапе
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

        # Проверяем каждый CVR на наличие проблем
        for cvr_name, cvr_value, denominator in cvr_checks:
            print(f"🔍 Проверка {cvr_name}: value={cvr_value}, denominator={denominator}")
            
            # Проверяем критерии проблемы: CVR < 20% И достаточно данных (знаменатель ≥ 5)
            if self._is_problem_cvr(cvr_value, denominator):
                # Получаем ID гипотез, соответствующих этому CVR
                hypothesis_ids = self.cvr_hypothesis_mapping.get(cvr_name, [])
                hypotheses = []

                # Загружаем полные данные гипотез из менеджера
                # Используем строгие правила сопоставления без "умных" предположений
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
        """
        Извлекает численные значения CVR из строковых представлений
        
        Преобразует строки вида "15.5%" в числа 15.5
        Обрабатывает случаи с отсутствующими данными ("—")
        
        Args:
            metrics: Словарь с CVR метриками в строковом формате
            
        Returns:
            Словарь с численными значениями CVR (None для отсутствующих данных)
        """
        cvr_values = {}
        for key, value in metrics.items():
            if value == "—":  # Отсутствующие данные
                cvr_values[key] = None
            else:
                try:
                    # Удаляем символ % и конвертируем в число с плавающей точкой
                    numeric_value = float(value.replace('%', ''))
                    cvr_values[key] = numeric_value
                except (ValueError, AttributeError):
                    # Если не удалось конвертировать, помечаем как отсутствующие
                    cvr_values[key] = None
        return cvr_values

    def _is_problem_cvr(self, cvr_value: Optional[float], denominator: int) -> bool:
        """
        Проверяет, является ли CVR проблемным согласно установленным критериям
        
        Критерии проблемы:
        1. CVR < 20% (низкая конверсия)
        2. Знаменатель ≥ 5 (достаточно данных для анализа)
        
        Args:
            cvr_value: Значение CVR в процентах (может быть None)
            denominator: Знаменатель для расчета CVR (количество записей на предыдущем этапе)
            
        Returns:
            True если CVR является проблемным, False иначе
        """
        # Если нет данных или недостаточно записей - не считаем проблемой
        if cvr_value is None or denominator < 5:
            return False
        # Проблема если конверсия меньше 20%
        return cvr_value < 20.0

    def _get_latest_funnel_data(self, history: List[Dict], profile: Dict) -> Optional[Dict]:
        """
        Извлекает последние данные воронки для проведения анализа
        
        Алгоритм:
        1. Группирует историю по неделям и каналам
        2. Выбирает последнюю неделю с данными
        3. Суммирует показатели по всем каналам
        4. Возвращает агрегированные данные для анализа
        
        Args:
            history: История данных пользователя из базы
            profile: Профиль пользователя с настройками
            
        Returns:
            Словарь с агрегированными данными последней недели или None
        """
        if not history:
            return None

        # Группируем записи по неделям, затем по каналам внутри каждой недели
        weeks = {}
        for row in history:
            week = row['week_start']
            if week not in weeks:
                weeks[week] = {}

            channel = row['channel_name']
            if channel not in weeks[week]:
                weeks[week][channel] = row

        # Выбираем самую последнюю неделю с данными
        latest_week = max(weeks.keys())
        latest_week_data = weeks[latest_week]

        # Определяем тип воронки из профиля пользователя
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
        Подготавливает полный пакет контекстных данных для генерации рекомендаций через ChatGPT
        
        Собирает:
        - Полный профиль пользователя (роль, локации, зарплата, компетенции и др.)
        - Историю рефлексий за последние 2 недели
        - Снапшот текущего состояния воронки
        - Найденные проблемы CVR
        - Соответствующие гипотезы для решения
        
        Args:
            user_id: Идентификатор пользователя
            problems: Список обнаруженных проблем CVR с привязанными гипотезами
            
        Returns:
            Структурированный словарь с полным контекстом для AI анализа
        """
        # Загружаем профиль пользователя и историю рефлексий
        profile = get_profile(user_id)
        reflection_history = get_reflection_history(user_id, 14)  # За последние 2 недели

        # Собираем все уникальные гипотезы из найденных проблем
        # Используем set для исключения дублирования
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
                "current_location": profile.get('current_location', 'Не указано'),
                "target_location": profile.get('target_location', 'Не указано'),
                "deadline_weeks": profile.get('deadline_weeks', 'Не указано'),
                "funnel_type": profile.get('preferred_funnel_type', 'active'),
                "role_synonyms": profile.get('role_synonyms_json'),
                "salary_min": profile.get('salary_min'),
                "salary_max": profile.get('salary_max'),
                "salary_currency": profile.get('salary_currency'),
                "salary_period": profile.get('salary_period'),
                "company_types": profile.get('company_types_json'),
                "industries": profile.get('industries_json'),
                "competencies": profile.get('competencies_json'),
                "superpowers": profile.get('superpowers_json'),
                "constraints": profile.get('constraints_text'),
                "linkedin": profile.get('linkedin_url')
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
        Генерирует детальный промпт для ChatGPT с полным контекстом пользователя
        
        Создает структурированный промпт, включающий:
        - Базовую информацию о профиле (роль, локации, сроки)
        - Расширенные данные (зарплата, компетенции, ограничения)
        - Проблемные области воронки с конкретными показателями
        - Доступные гипотезы с описанием действий и эффектов
        - Четкие инструкции по формату ответа
        
        Args:
            chatgpt_data: Структурированные данные анализа с профилем и проблемами
            
        Returns:
            Готовый промпт для отправки в ChatGPT API
        """
        profile = chatgpt_data["user_profile"]
        problems = chatgpt_data["problems"]
        hypotheses = chatgpt_data["hypotheses"]
        funnel_snapshot = chatgpt_data["funnel_snapshot"]

        prompt = f"""Привет! Ты HackOFFer AI-ментор по поиску работы. Проанализируй воронку кандидата, его LinkedIn страницу и дай 10 персональных рекомендаций.

ПРОФИЛЬ КАНДИДАТА:
• Роль: {profile['role']}
• Уровень: {profile['level']}
• Текущая локация: {profile['current_location']}
• Локация поиска: {profile['target_location']}
• Срок поиска: {profile['deadline_weeks']} недель
• Тип воронки: {"Активный поиск (подает заявки)" if profile['funnel_type'] == 'active' else "Пассивный поиск (находят его)"}

        # Добавляем дополнительную информацию профиля
        if profile.get('role_synonyms'):
            import json
            synonyms = json.loads(profile['role_synonyms']) if isinstance(profile['role_synonyms'], str) else profile['role_synonyms']
            if synonyms:
                prompt += f"\n• Синонимы ролей: {', '.join(synonyms)}"

        if profile.get('salary_min') and profile.get('salary_max'):
            currency = profile.get('salary_currency', 'EUR')
            period = profile.get('salary_period', 'год')
            if profile['salary_min'] == profile['salary_max']:
                prompt += f"\n• Зарплата: {profile['salary_min']:.0f} {currency}/{period}"
            else:
                prompt += f"\n• Диапазон ЗП: {profile['salary_min']:.0f}-{profile['salary_max']:.0f} {currency}/{period}"

        if profile.get('company_types'):
            import json
            types = json.loads(profile['company_types']) if isinstance(profile['company_types'], str) else profile['company_types']
            if types:
                prompt += f"\n• Типы компаний: {', '.join(types)}"

        if profile.get('industries'):
            import json
            industries = json.loads(profile['industries']) if isinstance(profile['industries'], str) else profile['industries']
            if industries:
                prompt += f"\n• Индустрии: {', '.join(industries)}"

        if profile.get('competencies'):
            import json
            competencies = json.loads(profile['competencies']) if isinstance(profile['competencies'], str) else profile['competencies']
            if competencies:
                prompt += f"\n• Ключевые компетенции: {', '.join(competencies)}"

        if profile.get('superpowers'):
            import json
            superpowers = json.loads(profile['superpowers']) if isinstance(profile['superpowers'], str) else profile['superpowers']
            if superpowers:
                prompt += f"\n• Карта суперсил: {', '.join(superpowers[:3])}{'...' if len(superpowers) > 3 else ''}"

        if profile.get('constraints'):
            prompt += f"\n• Доп. ограничения: {profile['constraints'][:100]}{'...' if len(profile['constraints']) > 100 else ''}"

        if profile.get('linkedin'):
            prompt += f"\n• LinkedIn: {profile['linkedin']}"

        prompt += f"\n\nПРОБЛЕМНЫЕ ОБЛАСТИ (CVR < 20% при знаменателе ≥5):"

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
- Конкретной и выполнимой
- Привязанной к его роли ({profile['role']}) и уровню ({profile['level']})
- Нацеленной на улучшение конкретного CVR
- С примером или шаблоном где возможно

Начинай каждую рекомендацию с номера (1-10) и эмодзи."""

        return prompt

    async def get_chatgpt_recommendations(self, chatgpt_data: Dict[str, any]) -> Optional[str]:
        """
        Асинхронно получает персонализированные рекомендации от ChatGPT API
        
        Выполняет:
        1. Проверку доступности OpenAI API
        2. Генерацию промпта с полным контекстом
        3. Отправку запроса к ChatGPT с настройками модели
        4. Обработку ответа и возврат рекомендаций
        
        Fallback: если API недоступен, возвращает None (промпт можно использовать вручную)
        
        Args:
            chatgpt_data: Подготовленные данные для анализа
            
        Returns:
            Строка с AI рекомендациями или None при недоступности API/ошибке
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
    Основная асинхронная функция для полного цикла CVR анализа и генерации рекомендаций
    
    Выполняет последовательно:
    1. Обнаружение проблем в воронке пользователя
    2. Подбор соответствующих гипотез для решения
    3. Подготовку контекстных данных для AI
    4. Генерацию персонализированных рекомендаций
    
    Args:
        user_id: Идентификатор пользователя в системе
        use_api: Флаг использования OpenAI API (True) или генерации только промпта (False)
        
    Returns:
        Результат анализа с одним из статусов:
        - "problems_found": найдены проблемы, есть рекомендации
        - "no_problems": воронка в норме, проблем не обнаружено
        - None: критическая ошибка анализа
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
    
    Запускает асинхронный анализ в новом event loop или через ThreadPoolExecutor
    если уже находимся внутри существующего loop.
    
    Используется в местах, где нужен синхронный вызов анализа CVR.
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        Результат анализа (аналогично analyze_and_recommend_async)
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