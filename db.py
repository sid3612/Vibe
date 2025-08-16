import sqlite3
import json
from datetime import datetime
from config import DATABASE_NAME

def get_db_connection():
    """Получить подключение к базе данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            active_funnel TEXT DEFAULT 'active',
            reminder_frequency TEXT DEFAULT 'off',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица каналов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, channel_name)
        )
    """)
    
    # Таблица данных по неделям
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS week_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week_start TEXT,
            channel_name TEXT,
            funnel_type TEXT,
            applications INTEGER DEFAULT 0,
            responses INTEGER DEFAULT 0,
            screenings INTEGER DEFAULT 0,
            onsites INTEGER DEFAULT 0,
            offers INTEGER DEFAULT 0,
            rejections INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            incoming INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, week_start, channel_name, funnel_type)
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str):
    """Добавить пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def get_user_funnels(user_id: int) -> dict:
    """Получить информацию о воронках пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT active_funnel, reminder_frequency
        FROM users
        WHERE user_id = ?
    """, (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'active_funnel': result['active_funnel'],
            'reminder_frequency': result['reminder_frequency']
        }
    return {'active_funnel': 'active', 'reminder_frequency': 'off'}

def set_active_funnel(user_id: int, funnel_type: str):
    """Установить активный тип воронки"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET active_funnel = ?
        WHERE user_id = ?
    """, (funnel_type, user_id))
    
    conn.commit()
    conn.close()

def get_user_channels(user_id: int) -> list:
    """Получить список каналов пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT channel_name
        FROM user_channels
        WHERE user_id = ?
        ORDER BY created_at
    """, (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [row['channel_name'] for row in results]

def add_channel(user_id: int, channel_name: str) -> bool:
    """Добавить канал"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO user_channels (user_id, channel_name)
            VALUES (?, ?)
        """, (user_id, channel_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_channel(user_id: int, channel_name: str):
    """Удалить канал"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Удаляем канал
    cursor.execute("""
        DELETE FROM user_channels
        WHERE user_id = ? AND channel_name = ?
    """, (user_id, channel_name))
    
    # Удаляем связанные данные
    cursor.execute("""
        DELETE FROM week_data
        WHERE user_id = ? AND channel_name = ?
    """, (user_id, channel_name))
    
    conn.commit()
    conn.close()

def add_week_data(user_id: int, week_start: str, channel: str, funnel_type: str, data: dict):
    """Добавить данные за неделю"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Подготавливаем данные для вставки
    if funnel_type == 'active':
        cursor.execute("""
            INSERT OR REPLACE INTO week_data 
            (user_id, week_start, channel_name, funnel_type, 
             applications, responses, screenings, onsites, offers, rejections, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id, week_start, channel, funnel_type,
            data.get('applications', 0),
            data.get('responses', 0),
            data.get('screenings', 0),
            data.get('onsites', 0),
            data.get('offers', 0),
            data.get('rejections', 0)
        ))
    else:  # passive
        cursor.execute("""
            INSERT OR REPLACE INTO week_data 
            (user_id, week_start, channel_name, funnel_type, 
             views, incoming, screenings, onsites, offers, rejections, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id, week_start, channel, funnel_type,
            data.get('views', 0),
            data.get('incoming', 0),
            data.get('screenings', 0),
            data.get('onsites', 0),
            data.get('offers', 0),
            data.get('rejections', 0)
        ))
    
    conn.commit()
    conn.close()

def get_week_data(user_id: int, week_start: str, channel: str, funnel_type: str) -> dict:
    """Получить данные за неделю"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM week_data
        WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
    """, (user_id, week_start, channel, funnel_type))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return {}

def update_week_field(user_id: int, week_start: str, channel: str, field: str, value: int) -> bool:
    """Обновить конкретное поле данных за неделю"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, существует ли запись
    cursor.execute("""
        SELECT id FROM week_data
        WHERE user_id = ? AND week_start = ? AND channel_name = ?
    """, (user_id, week_start, channel))
    
    if not cursor.fetchone():
        conn.close()
        return False
    
    # Обновляем поле
    sql = f"""
        UPDATE week_data
        SET {field} = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND week_start = ? AND channel_name = ?
    """
    
    cursor.execute(sql, (value, user_id, week_start, channel))
    conn.commit()
    conn.close()
    
    return True

def get_user_history(user_id: int) -> list:
    """Получить историю данных пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT *
        FROM week_data
        WHERE user_id = ?
        ORDER BY week_start DESC, channel_name
    """, (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def set_user_reminders(user_id: int, frequency: str):
    """Установить частоту напоминаний пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET reminder_frequency = ?
        WHERE user_id = ?
    """, (frequency, user_id))
    
    conn.commit()
    conn.close()

def get_users_for_reminders(frequency: str) -> list:
    """Получить пользователей для отправки напоминаний"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, username
        FROM users
        WHERE reminder_frequency = ?
    """, (frequency,))
    
    results = cursor.fetchall()
    conn.close()
    
    return [{'user_id': row['user_id'], 'username': row['username']} for row in results]
