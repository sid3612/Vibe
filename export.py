import csv
import io
from typing import List, Dict, Any
from db import get_user_history, get_user_funnels
from metrics import calculate_cvr_metrics

def generate_csv_export(user_id: int) -> str:
    """Генерировать CSV экспорт данных пользователя"""
    # Получаем историю пользователя
    history_data = get_user_history(user_id)
    user_data = get_user_funnels(user_id)
    
    if not history_data:
        return ""
    
    # Создаем CSV в памяти
    output = io.StringIO()
    
    funnel_type = user_data.get('active_funnel', 'active')
    
    # Определяем поля в зависимости от типа воронки
    if funnel_type == 'active':
        fieldnames = [
            'week_start', 'channel_name', 'funnel_type',
            'applications', 'responses', 'screenings', 'onsites', 'offers', 'rejections',
            'cvr1', 'cvr2', 'cvr3', 'cvr4',
            'created_at', 'updated_at'
        ]
        
        field_translations = {
            'week_start': 'Неделя',
            'channel_name': 'Канал',
            'funnel_type': 'Тип воронки',
            'applications': 'Подачи',
            'responses': 'Ответы',
            'screenings': 'Скрининги',
            'onsites': 'Онсайты',
            'offers': 'Офферы',
            'rejections': 'Реджекты',
            'cvr1': 'CVR1 (%)',
            'cvr2': 'CVR2 (%)',
            'cvr3': 'CVR3 (%)',
            'cvr4': 'CVR4 (%)',
            'created_at': 'Создано',
            'updated_at': 'Обновлено'
        }
    else:  # passive
        fieldnames = [
            'week_start', 'channel_name', 'funnel_type',
            'views', 'incoming', 'screenings', 'onsites', 'offers', 'rejections',
            'cvr1', 'cvr2', 'cvr3', 'cvr4',
            'created_at', 'updated_at'
        ]
        
        field_translations = {
            'week_start': 'Неделя',
            'channel_name': 'Канал',
            'funnel_type': 'Тип воронки',
            'views': 'Просмотры',
            'incoming': 'Входящие',
            'screenings': 'Скрининги',
            'onsites': 'Онсайты',
            'offers': 'Офферы',
            'rejections': 'Реджекты',
            'cvr1': 'CVR1-passive (%)',
            'cvr2': 'CVR2-passive (%)',
            'cvr3': 'CVR3-passive (%)',
            'cvr4': 'CVR4-passive (%)',
            'created_at': 'Создано',
            'updated_at': 'Обновлено'
        }
    
    # Создаем CSV writer с UTF-8 BOM для корректного отображения в Excel
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')
    
    # Записываем заголовок с переводом
    translated_headers = {field: field_translations.get(field, field) for field in fieldnames}
    writer.writerow(translated_headers)
    
    # Записываем данные
    for row in history_data:
        # Рассчитываем метрики для каждой строки
        metrics = calculate_cvr_metrics(row, funnel_type)
        
        # Подготавливаем строку для записи
        csv_row = {}
        for field in fieldnames:
            if field in ['cvr1', 'cvr2', 'cvr3', 'cvr4']:
                csv_row[field] = metrics.get(field, '—')
            elif field == 'funnel_type':
                csv_row[field] = 'Активная' if row[field] == 'active' else 'Пассивная'
            else:
                csv_row[field] = row.get(field, '')
        
        writer.writerow(csv_row)
    
    # Получаем содержимое CSV с UTF-8 BOM
    csv_content = output.getvalue()
    output.close()
    
    # Добавляем UTF-8 BOM для корректного отображения в Excel
    return '\ufeff' + csv_content

def generate_summary_report(user_id: int, weeks: int = 4) -> str:
    """Генерировать сводный отчет за последние N недель"""
    from metrics import get_summary_metrics
    
    summary = get_summary_metrics(user_id, weeks)
    if not summary:
        return "Нет данных для формирования отчета"
    
    output = io.StringIO()
    
    funnel_type = summary['funnel_type']
    totals = summary['totals']
    metrics = summary['metrics']
    
    # Заголовок отчета
    output.write(f"СВОДНЫЙ ОТЧЕТ ЗА {weeks} НЕДЕЛЬ\n")
    output.write(f"Тип воронки: {'Активная' if funnel_type == 'active' else 'Пассивная'}\n")
    output.write("=" * 50 + "\n\n")
    
    if funnel_type == 'active':
        output.write("ОБЩИЕ ПОКАЗАТЕЛИ:\n")
        output.write(f"Подачи: {totals['applications']}\n")
        output.write(f"Ответы: {totals['responses']}\n")
        output.write(f"Скрининги: {totals['screenings']}\n")
        output.write(f"Онсайты: {totals['onsites']}\n")
        output.write(f"Офферы: {totals['offers']}\n")
        output.write(f"Реджекты: {totals['rejections']}\n")
        
        output.write("\nMETRIKI КОНВЕРСИИ:\n")
        output.write(f"CVR1 (Ответы/Подачи): {metrics['cvr1']}\n")
        output.write(f"CVR2 (Скрининги/Ответы): {metrics['cvr2']}\n")
        output.write(f"CVR3 (Онсайты/Скрининги): {metrics['cvr3']}\n")
        output.write(f"CVR4 (Офферы/Онсайты): {metrics['cvr4']}\n")
        
    else:  # passive
        output.write("ОБЩИЕ ПОКАЗАТЕЛИ:\n")
        output.write(f"Просмотры: {totals['views']}\n")
        output.write(f"Входящие: {totals['incoming']}\n")
        output.write(f"Скрининги: {totals['screenings']}\n")
        output.write(f"Онсайты: {totals['onsites']}\n")
        output.write(f"Офферы: {totals['offers']}\n")
        output.write(f"Реджекты: {totals['rejections']}\n")
        
        output.write("\nMETRIKI КОНВЕРСИИ:\n")
        output.write(f"CVR1-passive (Входящие/Просмотры): {metrics['cvr1']}\n")
        output.write(f"CVR2-passive (Скрининги/Входящие): {metrics['cvr2']}\n")
        output.write(f"CVR3-passive (Онсайты/Скрининги): {metrics['cvr3']}\n")
        output.write(f"CVR4-passive (Офферы/Онсайты): {metrics['cvr4']}\n")
    
    # Анализ эффективности
    output.write("\nАНАЛИЗ:\n")
    offers = totals.get('offers', 0)
    if offers > 0:
        output.write(f"🎉 Получено офферов: {offers}\n")
        output.write(f"📊 Офферы за неделю в среднем: {offers / weeks:.1f}\n")
    else:
        output.write("🔍 Офферов пока нет. Продолжайте работать!\n")
    
    # Рекомендации
    if funnel_type == 'active':
        cvr1_num = float(metrics['cvr1'].replace('%', '')) if metrics['cvr1'] != '—' else 0
        cvr4_num = float(metrics['cvr4'].replace('%', '')) if metrics['cvr4'] != '—' else 0
        
        output.write("\nРЕКОМЕНДАЦИИ:\n")
        if cvr1_num < 10:
            output.write("• Низкий CVR1: улучшите качество откликов\n")
        if cvr4_num < 30:
            output.write("• Низкий CVR4: работайте над подготовкой к интервью\n")
    
    content = output.getvalue()
    output.close()
    
    return content
