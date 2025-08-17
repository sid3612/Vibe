from typing import List, Dict, Any
import pandas as pd

def calculate_cvr_metrics(data: Dict[str, Any], funnel_type: str) -> Dict[str, str]:
    """Рассчитать CVR метрики для данных"""
    metrics = {}
    
    if funnel_type == 'active':
        # Активная воронка: Подачи → Ответы → Скрининги → Онсайты → Офферы
        applications = data.get('applications', 0)
        responses = data.get('responses', 0)
        screenings = data.get('screenings', 0)
        onsites = data.get('onsites', 0)
        offers = data.get('offers', 0)
        
        # CVR1: Ответы / Подачи
        metrics['cvr1'] = calculate_percentage(responses, applications)
        
        # CVR2: Скрининги / Ответы
        metrics['cvr2'] = calculate_percentage(screenings, responses)
        
        # CVR3: Онсайты / Скрининги
        metrics['cvr3'] = calculate_percentage(onsites, screenings)
        
        # CVR4: Офферы / Онсайты
        metrics['cvr4'] = calculate_percentage(offers, onsites)
        
    else:  # passive
        # Пассивная воронка: Просмотры → Входящие → Скрининги → Онсайты → Офферы
        views = data.get('views', 0)
        incoming = data.get('incoming', 0)
        screenings = data.get('screenings', 0)
        onsites = data.get('onsites', 0)
        offers = data.get('offers', 0)
        
        # CVR1-passive: Входящие / Просмотры
        metrics['cvr1'] = calculate_percentage(incoming, views)
        
        # CVR2-passive: Скрининги / Входящие
        metrics['cvr2'] = calculate_percentage(screenings, incoming)
        
        # CVR3-passive: Онсайты / Скрининги
        metrics['cvr3'] = calculate_percentage(onsites, screenings)
        
        # CVR4-passive: Офферы / Онсайты
        metrics['cvr4'] = calculate_percentage(offers, onsites)
    
    return metrics

def calculate_percentage(numerator: int, denominator: int) -> str:
    """Рассчитать процент с обработкой деления на ноль"""
    if denominator == 0:
        return "—"
    
    percentage = (numerator / denominator) * 100
    return f"{round(percentage)}%"

def format_metrics_table(data: List[Dict[str, Any]], funnel_type: str) -> str:
    """Форматировать таблицу метрик для Telegram (мобильный формат)"""
    if not data:
        return "Нет данных для отображения"
    
    # Группируем данные по неделям
    weeks_data = {}
    for row in data:
        week = row['week_start']
        if week not in weeks_data:
            weeks_data[week] = []
        weeks_data[week].append(row)
    
    result = []
    
    if funnel_type == 'active':
        header = "📊 АКТИВНАЯ ВОРОНКА\n"
        result.append(header)
        
        for week in sorted(weeks_data.keys(), reverse=True):
            week_data = weeks_data[week]
            result.append(f"📅 Неделя: {week}")
            result.append("-" * 35)
            
            for row in week_data:
                metrics = calculate_cvr_metrics(row, funnel_type)
                channel = row['channel_name'][:12]
                
                # Первая строка: канал и числовые данные
                data_line = f"{channel:<12} {row['applications']:2} {row['responses']:2} {row['screenings']:2} {row['onsites']:2} {row['offers']:2} {row['rejections']:2}"
                result.append(data_line)
                
                # Вторая строка: CVR метрики
                cvr_line = f"{'CVR:':<12} {metrics['cvr1']:>4} {metrics['cvr2']:>4} {metrics['cvr3']:>4} {metrics['cvr4']:>4} — —"
                result.append(cvr_line)
                result.append("")
            
            result.append("")
    
    else:  # passive
        header = "📊 ПАССИВНАЯ ВОРОНКА\n"
        result.append(header)
        
        for week in sorted(weeks_data.keys(), reverse=True):
            week_data = weeks_data[week]
            result.append(f"📅 Неделя: {week}")
            result.append("-" * 35)
            
            for row in week_data:
                metrics = calculate_cvr_metrics(row, funnel_type)
                channel = row['channel_name'][:12]
                
                # Первая строка: канал и числовые данные
                data_line = f"{channel:<12} {row['views']:2} {row['incoming']:2} {row['screenings']:2} {row['onsites']:2} {row['offers']:2} {row['rejections']:2}"
                result.append(data_line)
                
                # Вторая строка: CVR метрики
                cvr_line = f"{'CVR:':<12} {metrics['cvr1']:>4} {metrics['cvr2']:>4} {metrics['cvr3']:>4} {metrics['cvr4']:>4} — —"
                result.append(cvr_line)
                result.append("")
            
            result.append("")
    
    return "\n".join(result)

def format_history_table(data: List[Dict[str, Any]], funnel_type: str) -> str:
    """Форматировать историческую таблицу для отображения (мобильный формат)"""
    if not data:
        return "Нет данных для отображения"
    
    # Создаем DataFrame для удобства обработки
    df = pd.DataFrame(data)
    
    if funnel_type == 'active':
        # Группируем по неделям и каналам
        result = ["📈 ИСТОРИЯ - АКТИВНАЯ ВОРОНКА", ""]
        
        # Сортируем по неделям (новые сверху)
        for week in sorted(df['week_start'].unique(), reverse=True):
            week_data = df[df['week_start'] == week]
            
            result.append(f"📅 Неделя: {week}")
            result.append("-" * 35)
            
            total_apps = 0
            total_responses = 0
            total_screenings = 0
            total_onsites = 0
            total_offers = 0
            total_rejections = 0
            
            for _, row in week_data.iterrows():
                metrics = calculate_cvr_metrics(dict(row), funnel_type)
                channel = str(row['channel_name'])[:12]
                
                apps = row['applications']
                resp = row['responses']
                scr = row['screenings']
                ons = row['onsites']
                off = row['offers']
                rej = row['rejections']
                
                total_apps += apps
                total_responses += resp
                total_screenings += scr
                total_onsites += ons
                total_offers += off
                total_rejections += rej
                
                # Первая строка: канал и числовые данные
                data_line = f"{channel:<12} {apps:2} {resp:2} {scr:2} {ons:2} {off:2} {rej:2}"
                result.append(data_line)
                
                # Вторая строка: CVR метрики
                cvr_line = f"{'CVR:':<12} {metrics['cvr1']:>4} {metrics['cvr2']:>4} {metrics['cvr3']:>4} {metrics['cvr4']:>4} — —"
                result.append(cvr_line)
                result.append("")
            
            # Добавляем итоги по неделе
            if len(week_data) > 1:
                total_metrics = calculate_cvr_metrics({
                    'applications': total_apps,
                    'responses': total_responses,
                    'screenings': total_screenings,
                    'onsites': total_onsites,
                    'offers': total_offers,
                    'rejections': total_rejections
                }, funnel_type)
                
                result.append("-" * 35)
                # Итоговые данные
                total_data_line = f"{'ИТОГО':<12} {total_apps:2} {total_responses:2} {total_screenings:2} {total_onsites:2} {total_offers:2} {total_rejections:2}"
                result.append(total_data_line)
                
                # Итоговые CVR
                total_cvr_line = f"{'CVR:':<12} {total_metrics['cvr1']:>4} {total_metrics['cvr2']:>4} {total_metrics['cvr3']:>4} {total_metrics['cvr4']:>4} — —"
                result.append(total_cvr_line)
            
            result.append("")
            
    else:  # passive
        result = ["📈 ИСТОРИЯ - ПАССИВНАЯ ВОРОНКА", ""]
        
        for week in sorted(df['week_start'].unique(), reverse=True):
            week_data = df[df['week_start'] == week]
            
            result.append(f"📅 Неделя: {week}")
            result.append("-" * 35)
            
            total_views = 0
            total_incoming = 0
            total_screenings = 0
            total_onsites = 0
            total_offers = 0
            total_rejections = 0
            
            for _, row in week_data.iterrows():
                metrics = calculate_cvr_metrics(dict(row), funnel_type)
                channel = str(row['channel_name'])[:12]
                
                views = row['views']
                inc = row['incoming']
                scr = row['screenings']
                ons = row['onsites']
                off = row['offers']
                rej = row['rejections']
                
                total_views += views
                total_incoming += inc
                total_screenings += scr
                total_onsites += ons
                total_offers += off
                total_rejections += rej
                
                # Первая строка: канал и числовые данные
                data_line = f"{channel:<12} {views:2} {inc:2} {scr:2} {ons:2} {off:2} {rej:2}"
                result.append(data_line)
                
                # Вторая строка: CVR метрики
                cvr_line = f"{'CVR:':<12} {metrics['cvr1']:>4} {metrics['cvr2']:>4} {metrics['cvr3']:>4} {metrics['cvr4']:>4} — —"
                result.append(cvr_line)
                result.append("")
            
            # Добавляем итоги по неделе
            if len(week_data) > 1:
                total_metrics = calculate_cvr_metrics({
                    'views': total_views,
                    'incoming': total_incoming,
                    'screenings': total_screenings,
                    'onsites': total_onsites,
                    'offers': total_offers,
                    'rejections': total_rejections
                }, funnel_type)
                
                result.append("-" * 35)
                # Итоговые данные
                total_data_line = f"{'ИТОГО':<12} {total_views:2} {total_incoming:2} {total_screenings:2} {total_onsites:2} {total_offers:2} {total_rejections:2}"
                result.append(total_data_line)
                
                # Итоговые CVR
                total_cvr_line = f"{'CVR:':<12} {total_metrics['cvr1']:>4} {total_metrics['cvr2']:>4} {total_metrics['cvr3']:>4} {total_metrics['cvr4']:>4} — —"
                result.append(total_cvr_line)
            
            result.append("")
    
    return "\n".join(result)

def get_summary_metrics(user_id: int, weeks: int = 4) -> Dict[str, Any]:
    """Получить сводные метрики за последние N недель"""
    from db import get_user_history
    
    data = get_user_history(user_id)
    if not data:
        return {}
    
    # Фильтруем по последним неделям
    df = pd.DataFrame(data)
    df['week_start'] = pd.to_datetime(df['week_start'])
    
    # Берем последние N недель
    recent_data = df.nlargest(weeks * len(df['channel_name'].unique()), 'week_start')
    
    if recent_data.empty:
        return {}
    
    # Агрегируем данные
    funnel_type = recent_data['funnel_type'].iloc[0]
    
    if funnel_type == 'active':
        totals = {
            'applications': recent_data['applications'].sum(),
            'responses': recent_data['responses'].sum(),
            'screenings': recent_data['screenings'].sum(),
            'onsites': recent_data['onsites'].sum(),
            'offers': recent_data['offers'].sum(),
            'rejections': recent_data['rejections'].sum()
        }
    else:
        totals = {
            'views': recent_data['views'].sum(),
            'incoming': recent_data['incoming'].sum(),
            'screenings': recent_data['screenings'].sum(),
            'onsites': recent_data['onsites'].sum(),
            'offers': recent_data['offers'].sum(),
            'rejections': recent_data['rejections'].sum()
        }
    
    metrics = calculate_cvr_metrics(totals, funnel_type)
    
    return {
        'totals': totals,
        'metrics': metrics,
        'weeks_count': weeks,
        'funnel_type': funnel_type
    }
