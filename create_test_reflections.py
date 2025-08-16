#!/usr/bin/env python3
"""Создание тестовых данных для истории рефлексий"""

import sqlite3
import json
from datetime import datetime, timedelta

def create_test_reflections():
    """Создать тестовые данные рефлексий"""
    conn = sqlite3.connect('funnel_coach.db')
    cursor = conn.cursor()
    
    # Создаем тестовые данные для пользователя 1234567
    test_data = [
        {
            'user_id': 1234567,
            'funnel_type': 'active',
            'channel': 'LinkedIn',
            'week_start': '2025-08-12',
            'section_stage': 'responses',
            'events_count': 3,
            'rating_overall': 8,
            'strengths': 'Хорошие ответы от крупных компаний',
            'weaknesses': 'Мало откликов от стартапов',
            'rating_mood': 7,
            'reject_reasons_json': json.dumps(['Не подходит опыт', 'Слишком высокие требования'])
        },
        {
            'user_id': 1234567,
            'funnel_type': 'active', 
            'channel': 'HH.ru',
            'week_start': '2025-08-05',
            'section_stage': 'screenings',
            'events_count': 2,
            'rating_overall': 6,
            'strengths': 'Интересные задачи на скрининге',
            'weaknesses': 'Долгие ожидания ответов',
            'rating_mood': 5,
            'reject_reasons_json': json.dumps(['Технические вопросы'])
        },
        {
            'user_id': 1234567,
            'funnel_type': 'active',
            'channel': 'Referrals', 
            'week_start': '2025-07-29',
            'section_stage': 'offers',
            'events_count': 1,
            'rating_overall': 9,
            'strengths': 'Отличное предложение зарплаты',
            'weaknesses': 'Удаленная работа не предлагалась',
            'rating_mood': 8,
            'reject_reasons_json': json.dumps([])
        },
        {
            'user_id': 1234567,
            'funnel_type': 'active',
            'channel': 'LinkedIn',
            'week_start': '2025-07-22',
            'section_stage': 'rejections',
            'events_count': 2,
            'rating_overall': 4,
            'strengths': 'Получил обратную связь',
            'weaknesses': 'Не прошел технические интервью',
            'rating_mood': 3,
            'reject_reasons_json': json.dumps(['Недостаточно опыта', 'Не прошел тех задание'])
        }
    ]
    
    # Удаляем существующие тестовые данные 
    cursor.execute("DELETE FROM event_feedback WHERE user_id = ?", (1234567,))
    
    # Вставляем новые тестовые данные
    for data in test_data:
        cursor.execute("""
            INSERT INTO event_feedback (
                user_id, funnel_type, channel, week_start, section_stage,
                events_count, rating_overall, strengths, weaknesses, 
                rating_mood, reject_reasons_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['user_id'], data['funnel_type'], data['channel'], 
            data['week_start'], data['section_stage'], data['events_count'],
            data['rating_overall'], data['strengths'], data['weaknesses'],
            data['rating_mood'], data['reject_reasons_json']
        ))
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM event_feedback WHERE user_id = ?", (1234567,))
    count = cursor.fetchone()[0]
    
    print(f"Создано {count} тестовых записей рефлексий для пользователя 1234567")
    
    # Показываем созданные записи
    cursor.execute("""
        SELECT section_stage, channel, week_start, rating_overall, strengths
        FROM event_feedback 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    """, (1234567,))
    
    records = cursor.fetchall()
    print("\nСозданные записи:")
    for i, record in enumerate(records, 1):
        print(f"{i}. {record[0]} • {record[1]} • {record[2]} • Оценка: {record[3]} • {record[4][:30]}...")
    
    conn.close()

if __name__ == "__main__":
    create_test_reflections()