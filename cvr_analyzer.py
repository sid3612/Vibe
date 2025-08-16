#!/usr/bin/env python3
"""
Модуль для анализа CVR данных и интеграции с ChatGPT

Этот модуль предназначен для следующей итерации:
- Анализ производительности пользователя по CVR метрикам
- Сравнение с бенчмарками
- Подготовка персонализированных рекомендаций
- Интеграция с ChatGPT API для генерации советов
"""

from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

class CVRAnalyzer:
    """Анализатор CVR метрик для персонализированных рекомендаций"""
    
    # Бенчмарки индустрии (примерные значения)
    INDUSTRY_BENCHMARKS = {
        'cvr1_responses': {'low': 5, 'good': 15, 'excellent': 25},
        'cvr2_screenings': {'low': 20, 'good': 40, 'excellent': 60},
        'cvr3_onsites': {'low': 30, 'good': 60, 'excellent': 80},
        'cvr4_offers': {'low': 15, 'good': 35, 'excellent': 55}
    }
    
    def __init__(self):
        self.user_data = None
        self.analysis_results = None
    
    def analyze_user_performance(self, user_id: int) -> Dict:
        """
        Проанализировать производительность пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Подробный анализ производительности
        """
        from db import get_user_history
        from metrics import calculate_metrics_for_history
        
        history = get_user_history(user_id)
        if not history:
            return {"error": "Нет данных для анализа"}
        
        # Рассчитываем метрики
        metrics = []
        for row in history:
            metric = {
                'week': row['week_start'],
                'channel': row['channel_name'],
                'cvr1': self._safe_divide(row['responses'], row.get('applications', row.get('views', 0))) * 100,
                'cvr2': self._safe_divide(row['screenings'], row['responses']) * 100,
                'cvr3': self._safe_divide(row['onsites'], row['screenings']) * 100,
                'cvr4': self._safe_divide(row['offers'], row['onsites']) * 100
            }
            metrics.append(metric)
        
        # Анализируем производительность
        analysis = {
            'user_id': user_id,
            'analysis_date': datetime.now().isoformat(),
            'total_weeks': len(set(row['week_start'] for row in history)),
            'channels_used': list(set(row['channel_name'] for row in history)),
            'cvr_performance': self._analyze_cvr_performance(metrics),
            'trends': self._analyze_trends(metrics),
            'recommendations': self._generate_recommendations(metrics),
            'problem_areas': self._identify_problems(metrics),
            'strengths': self._identify_strengths(metrics)
        }
        
        self.analysis_results = analysis
        return analysis
    
    def prepare_chatgpt_context(self, user_id: int) -> Optional[Dict]:
        """
        Подготовить контекст для ChatGPT API
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с контекстом для ChatGPT
        """
        if not self.analysis_results or self.analysis_results['user_id'] != user_id:
            self.analyze_user_performance(user_id)
        
        if not self.analysis_results or 'error' in self.analysis_results:
            return None
        
        context = {
            'system_prompt': self._build_system_prompt(),
            'user_data': self._format_user_data(),
            'questions': self._generate_coaching_questions(),
            'expected_response_format': self._get_response_format()
        }
        
        return context
    
    def _safe_divide(self, numerator: int, denominator: int) -> float:
        """Безопасное деление с обработкой деления на ноль"""
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def _analyze_cvr_performance(self, metrics: List[Dict]) -> Dict:
        """Анализ производительности CVR относительно бенчмарков"""
        if not metrics:
            return {}
        
        # Усредняем метрики по всем неделям и каналам
        avg_cvr1 = sum(m['cvr1'] for m in metrics) / len(metrics)
        avg_cvr2 = sum(m['cvr2'] for m in metrics if m['cvr2'] > 0) / max(1, len([m for m in metrics if m['cvr2'] > 0]))
        avg_cvr3 = sum(m['cvr3'] for m in metrics if m['cvr3'] > 0) / max(1, len([m for m in metrics if m['cvr3'] > 0]))
        avg_cvr4 = sum(m['cvr4'] for m in metrics if m['cvr4'] > 0) / max(1, len([m for m in metrics if m['cvr4'] > 0]))
        
        performance = {
            'cvr1_responses': {
                'value': round(avg_cvr1, 1),
                'benchmark': self._get_performance_level(avg_cvr1, 'cvr1_responses'),
                'industry_avg': self.INDUSTRY_BENCHMARKS['cvr1_responses']['good']
            },
            'cvr2_screenings': {
                'value': round(avg_cvr2, 1),
                'benchmark': self._get_performance_level(avg_cvr2, 'cvr2_screenings'),
                'industry_avg': self.INDUSTRY_BENCHMARKS['cvr2_screenings']['good']
            },
            'cvr3_onsites': {
                'value': round(avg_cvr3, 1),
                'benchmark': self._get_performance_level(avg_cvr3, 'cvr3_onsites'),
                'industry_avg': self.INDUSTRY_BENCHMARKS['cvr3_onsites']['good']
            },
            'cvr4_offers': {
                'value': round(avg_cvr4, 1),
                'benchmark': self._get_performance_level(avg_cvr4, 'cvr4_offers'),
                'industry_avg': self.INDUSTRY_BENCHMARKS['cvr4_offers']['good']
            }
        }
        
        return performance
    
    def _get_performance_level(self, value: float, metric_type: str) -> str:
        """Определить уровень производительности относительно бенчмарков"""
        benchmarks = self.INDUSTRY_BENCHMARKS[metric_type]
        
        if value >= benchmarks['excellent']:
            return 'excellent'
        elif value >= benchmarks['good']:
            return 'good'
        elif value >= benchmarks['low']:
            return 'low'
        else:
            return 'critical'
    
    def _analyze_trends(self, metrics: List[Dict]) -> Dict:
        """Анализ трендов по неделям"""
        if len(metrics) < 2:
            return {"trend": "insufficient_data"}
        
        # Группируем по неделям и усредняем
        weekly_data = {}
        for metric in metrics:
            week = metric['week']
            if week not in weekly_data:
                weekly_data[week] = []
            weekly_data[week].append(metric)
        
        weekly_averages = {}
        for week, week_metrics in weekly_data.items():
            weekly_averages[week] = {
                'cvr1': sum(m['cvr1'] for m in week_metrics) / len(week_metrics),
                'cvr2': sum(m['cvr2'] for m in week_metrics) / len(week_metrics),
                'cvr3': sum(m['cvr3'] for m in week_metrics) / len(week_metrics),
                'cvr4': sum(m['cvr4'] for m in week_metrics) / len(week_metrics)
            }
        
        # Анализируем тренд (простое сравнение первой и последней недели)
        weeks = sorted(weekly_averages.keys())
        if len(weeks) >= 2:
            first_week = weekly_averages[weeks[0]]
            last_week = weekly_averages[weeks[-1]]
            
            trends = {}
            for cvr in ['cvr1', 'cvr2', 'cvr3', 'cvr4']:
                change = last_week[cvr] - first_week[cvr]
                if abs(change) < 2:
                    trends[cvr] = 'stable'
                elif change > 0:
                    trends[cvr] = 'improving'
                else:
                    trends[cvr] = 'declining'
            
            return trends
        
        return {"trend": "stable"}
    
    def _generate_recommendations(self, metrics: List[Dict]) -> List[str]:
        """Генерация базовых рекомендаций на основе метрик"""
        recommendations = []
        
        if not metrics:
            return ["Начните отслеживать данные для получения рекомендаций"]
        
        avg_cvr1 = sum(m['cvr1'] for m in metrics) / len(metrics)
        avg_cvr2 = sum(m['cvr2'] for m in metrics if m['cvr2'] > 0) / max(1, len([m for m in metrics if m['cvr2'] > 0]))
        
        if avg_cvr1 < 10:
            recommendations.append("Улучшите качество резюме и сопроводительных писем")
        if avg_cvr2 < 30:
            recommendations.append("Подготовьтесь лучше к телефонным интервью и скринингам")
        
        return recommendations or ["Продолжайте отслеживать метрики для персонализированных советов"]
    
    def _identify_problems(self, metrics: List[Dict]) -> List[str]:
        """Определение проблемных областей"""
        problems = []
        
        if not metrics:
            return problems
        
        performance = self._analyze_cvr_performance(metrics)
        
        for stage, data in performance.items():
            if data['benchmark'] == 'critical':
                stage_name = {
                    'cvr1_responses': 'получение откликов',
                    'cvr2_screenings': 'прохождение скрининга',
                    'cvr3_onsites': 'получение приглашений на онсайт',
                    'cvr4_offers': 'получение офферов'
                }.get(stage, stage)
                problems.append(f"Критически низкие показатели: {stage_name}")
        
        return problems
    
    def _identify_strengths(self, metrics: List[Dict]) -> List[str]:
        """Определение сильных сторон"""
        strengths = []
        
        if not metrics:
            return strengths
        
        performance = self._analyze_cvr_performance(metrics)
        
        for stage, data in performance.items():
            if data['benchmark'] == 'excellent':
                stage_name = {
                    'cvr1_responses': 'получение откликов',
                    'cvr2_screenings': 'прохождение скрининга', 
                    'cvr3_onsites': 'получение приглашений на онсайт',
                    'cvr4_offers': 'получение офферов'
                }.get(stage, stage)
                strengths.append(f"Отличные показатели: {stage_name}")
        
        return strengths
    
    def _build_system_prompt(self) -> str:
        """Построение системного промпта для ChatGPT"""
        return """
Ты опытный карьерный коуч, специализирующийся на поиске работы в IT.
Твоя задача - анализировать воронку поиска работы пользователя и давать персонализированные рекомендации.

Фокусируйся на:
1. Конкретных метриках CVR (Conversion Rate)
2. Сравнении с индустриальными бенчмарками
3. Практических советах для улучшения
4. Приоритизации проблемных областей

Отвечай на русском языке, структурированно и с конкретными шагами.
"""
    
    def _format_user_data(self) -> str:
        """Форматирование данных пользователя для ChatGPT"""
        if not self.analysis_results:
            return "Данные пользователя недоступны"
        
        return json.dumps(self.analysis_results, ensure_ascii=False, indent=2)
    
    def _generate_coaching_questions(self) -> List[str]:
        """Генерация вопросов для коучинга"""
        return [
            "Какие 3 главные проблемы вы видите в моей воронке поиска работы?",
            "Какие конкретные шаги мне предпринять для улучшения CVR?",
            "На чем сосредоточиться в первую очередь?",
            "Какие инструменты или ресурсы вы рекомендуете?"
        ]
    
    def _get_response_format(self) -> str:
        """Ожидаемый формат ответа от ChatGPT"""
        return """
Структурируй ответ в следующем формате:
1. АНАЛИЗ ТЕКУЩЕЙ СИТУАЦИИ
2. ПРИОРИТЕТНЫЕ ПРОБЛЕМЫ (топ-3)
3. КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ (с шагами)
4. ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ
5. ПЛАН НА СЛЕДУЮЩИЕ 2-4 НЕДЕЛИ
"""

# Функция для быстрого анализа
def analyze_user_cvr(user_id: int) -> Dict:
    """Быстрый анализ CVR пользователя"""
    analyzer = CVRAnalyzer()
    return analyzer.analyze_user_performance(user_id)

if __name__ == "__main__":
    print("CVR Analyzer готов к использованию")
    print("Модуль предназначен для интеграции с ChatGPT в следующей итерации")