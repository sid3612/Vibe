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

    # Таблица профилей кандидатов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL,
            current_location TEXT NOT NULL,
            target_location TEXT NOT NULL,
            level TEXT NOT NULL,
            deadline_weeks INTEGER NOT NULL,
            target_end_date TEXT NOT NULL,
            preferred_funnel_type TEXT NOT NULL DEFAULT 'active',

            role_synonyms_json TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_currency TEXT,
            salary_period TEXT,
            company_types_json TEXT,
            industries_json TEXT,
            competencies_json TEXT,
            superpowers_json TEXT,
            constraints_text TEXT,
            linkedin_url TEXT,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    # Add preferred_funnel_type column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN preferred_funnel_type TEXT NOT NULL DEFAULT 'active'")
        print("Added preferred_funnel_type column to profiles table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Add linkedin_url column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN linkedin_url TEXT")
        print("Added linkedin_url column to profiles table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Триггер для обновления updated_at
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS profiles_updated
        AFTER UPDATE ON profiles
        BEGIN
            UPDATE profiles SET updated_at = datetime('now') WHERE user_id = NEW.user_id;
        END;
    """)

    # PRD v3.1 - Event feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            funnel_type TEXT NOT NULL,
            channel TEXT NOT NULL,
            week_start TEXT NOT NULL,

            section_stage TEXT NOT NULL,
            events_count INTEGER NOT NULL,

            rating_overall INTEGER,
            strengths TEXT,
            weaknesses TEXT,
            rating_mood INTEGER,
            reject_after_stage TEXT,
            reject_reasons_json TEXT,
            reject_reason_other TEXT,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_feedback_ctx
        ON event_feedback(user_id, week_start, funnel_type, channel, section_stage)
    """)

    # Создание таблицы напоминаний
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
        user_id INTEGER PRIMARY KEY,
        frequency TEXT DEFAULT 'off',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Создание таблицы статистики кликов по оплате
    cursor.execute('''CREATE TABLE IF NOT EXISTS payment_clicks (
        user_id INTEGER PRIMARY KEY,
        click_count INTEGER DEFAULT 1,
        first_click_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_click_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

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
    """Получить настройки пользователя с приоритетом профиля"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Try to get funnel preference from profile first
    cursor.execute("""
        SELECT preferred_funnel_type
        FROM profiles
        WHERE user_id = ?
    """, (user_id,))

    profile_result = cursor.fetchone()

    # Get user settings
    cursor.execute("""
        SELECT active_funnel, reminder_frequency
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    user_result = cursor.fetchone()
    conn.close()

    # Use profile preference if available, otherwise user setting, otherwise default
    active_funnel = 'active'
    if profile_result and profile_result['preferred_funnel_type']:
        active_funnel = profile_result['preferred_funnel_type']
    elif user_result and user_result['active_funnel']:
        active_funnel = user_result['active_funnel']

    reminder_frequency = 'off'
    if user_result and user_result['reminder_frequency']:
        reminder_frequency = user_result['reminder_frequency']

    return {
        'active_funnel': active_funnel,
        'reminder_frequency': reminder_frequency
    }

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

def add_week_data(user_id: int, week_start: str, channel: str, funnel_type: str, data: dict, check_triggers: bool = True):
    """Добавить данные за неделю (суммируя с существующими, если есть)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get old data for trigger checking
    old_data = {}
    if check_triggers:
        cursor.execute("""
            SELECT * FROM week_data
            WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
        """, (user_id, week_start, channel, funnel_type))

        existing_row = cursor.fetchone()
        if existing_row:
            old_data = dict(existing_row)

    # Проверяем, есть ли уже данные для этой недели/канала/типа воронки
    cursor.execute("""
        SELECT * FROM week_data
        WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
    """, (user_id, week_start, channel, funnel_type))

    existing = cursor.fetchone()

    if existing:
        # Суммируем с существующими данными
        if funnel_type == 'active':
            cursor.execute("""
                UPDATE week_data 
                SET applications = applications + ?,
                    responses = responses + ?,
                    screenings = screenings + ?,
                    onsites = onsites + ?,
                    offers = offers + ?,
                    rejections = rejections + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
            """, (
                data.get('applications', 0),
                data.get('responses', 0),
                data.get('screenings', 0),
                data.get('onsites', 0),
                data.get('offers', 0),
                data.get('rejections', 0),
                user_id, week_start, channel, funnel_type
            ))
        else:  # passive
            cursor.execute("""
                UPDATE week_data 
                SET views = views + ?,
                    incoming = incoming + ?,
                    screenings = screenings + ?,
                    onsites = onsites + ?,
                    offers = offers + ?,
                    rejections = rejections + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
            """, (
                data.get('views', 0),
                data.get('incoming', 0),
                data.get('screenings', 0),
                data.get('onsites', 0),
                data.get('offers', 0),
                data.get('rejections', 0),
                user_id, week_start, channel, funnel_type
            ))
    else:
        # Вставляем новую запись
        if funnel_type == 'active':
            cursor.execute("""
                INSERT INTO week_data 
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
                INSERT INTO week_data 
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

    # Return old_data and new_data for trigger checking if requested
    if check_triggers:
        # Calculate new_data after the update
        new_data = old_data.copy() if old_data else {}
        if funnel_type == 'active':
            new_data.update({
                'applications': new_data.get('applications', 0) + data.get('applications', 0),
                'responses': new_data.get('responses', 0) + data.get('responses', 0),
                'screenings': new_data.get('screenings', 0) + data.get('screenings', 0),
                'onsites': new_data.get('onsites', 0) + data.get('onsites', 0),
                'offers': new_data.get('offers', 0) + data.get('offers', 0),
                'rejections': new_data.get('rejections', 0) + data.get('rejections', 0)
            })
        else:  # passive
            new_data.update({
                'views': new_data.get('views', 0) + data.get('views', 0),
                'incoming': new_data.get('incoming', 0) + data.get('incoming', 0),
                'screenings': new_data.get('screenings', 0) + data.get('screenings', 0),
                'onsites': new_data.get('onsites', 0) + data.get('onsites', 0),
                'offers': new_data.get('offers', 0) + data.get('offers', 0),
                'rejections': new_data.get('rejections', 0) + data.get('rejections', 0)
            })
        return old_data, new_data

    return None, None

def cleanup_duplicate_data():
    """Очистка дублированных данных - суммирование существующих дубликатов"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Находим все дубликаты
    cursor.execute("""
        SELECT user_id, week_start, channel_name, funnel_type, COUNT(*) as count
        FROM week_data
        GROUP BY user_id, week_start, channel_name, funnel_type
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()

    for dup in duplicates:
        user_id, week_start, channel_name, funnel_type, count = dup

        # Получаем все записи для этой комбинации
        cursor.execute("""
            SELECT * FROM week_data
            WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
            ORDER BY created_at
        """, (user_id, week_start, channel_name, funnel_type))

        records = cursor.fetchall()

        if len(records) > 1:
            # Суммируем все значения
            total_data = {
                'applications': sum(r['applications'] or 0 for r in records),
                'responses': sum(r['responses'] or 0 for r in records),
                'screenings': sum(r['screenings'] or 0 for r in records),
                'onsites': sum(r['onsites'] or 0 for r in records),
                'offers': sum(r['offers'] or 0 for r in records),
                'rejections': sum(r['rejections'] or 0 for r in records),
                'views': sum(r['views'] or 0 for r in records),
                'incoming': sum(r['incoming'] or 0 for r in records)
            }

            # Удаляем все старые записи
            cursor.execute("""
                DELETE FROM week_data
                WHERE user_id = ? AND week_start = ? AND channel_name = ? AND funnel_type = ?
            """, (user_id, week_start, channel_name, funnel_type))

            # Вставляем одну суммированную запись
            if funnel_type == 'active':
                cursor.execute("""
                    INSERT INTO week_data 
                    (user_id, week_start, channel_name, funnel_type, 
                     applications, responses, screenings, onsites, offers, rejections, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_id, week_start, channel_name, funnel_type,
                    total_data['applications'],
                    total_data['responses'],
                    total_data['screenings'],
                    total_data['onsites'],
                    total_data['offers'],
                    total_data['rejections']
                ))
            else:  # passive
                cursor.execute("""
                    INSERT INTO week_data 
                    (user_id, week_start, channel_name, funnel_type, 
                     views, incoming, screenings, onsites, offers, rejections, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_id, week_start, channel_name, funnel_type,
                    total_data['views'],
                    total_data['incoming'],
                    total_data['screenings'],
                    total_data['onsites'],
                    total_data['offers'],
                    total_data['rejections']
                ))

    conn.commit()
    conn.close()

    return len(duplicates)

# Profile management functions
def save_profile(user_id: int, profile_data: dict):
    """Save or update user profile"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Convert constraints key to match database column if present
    if 'constraints' in profile_data:
        profile_data['constraints_text'] = profile_data.pop('constraints')

    # Check if profile exists
    cursor.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()

    if exists:
        # Update existing profile
        cursor.execute("""
            UPDATE profiles SET 
                role = ?, current_location = ?, target_location = ?, level = ?,
                deadline_weeks = ?, target_end_date = ?, preferred_funnel_type = ?, role_synonyms_json = ?,
                salary_min = ?, salary_max = ?, salary_currency = ?, salary_period = ?,
                company_types_json = ?, industries_json = ?, competencies_json = ?,
                superpowers_json = ?, constraints_text = ?, linkedin_url = ?
            WHERE user_id = ?
        """, (
            profile_data['role'], profile_data['current_location'], profile_data['target_location'],
            profile_data['level'], profile_data['deadline_weeks'], profile_data['target_end_date'],
            profile_data.get('preferred_funnel_type', 'active'), profile_data.get('role_synonyms_json'), 
            profile_data.get('salary_min'), profile_data.get('salary_max'), profile_data.get('salary_currency'),
            profile_data.get('salary_period'), profile_data.get('company_types_json'),
            profile_data.get('industries_json'), profile_data.get('competencies_json'),
            profile_data.get('superpowers_json'), profile_data.get('constraints_text'),
            profile_data.get('linkedin_url'), user_id
        ))
    else:
        # Insert new profile
        cursor.execute("""
            INSERT INTO profiles (
                user_id, role, current_location, target_location, level,
                deadline_weeks, target_end_date, preferred_funnel_type, role_synonyms_json,
                salary_min, salary_max, salary_currency, salary_period,
                company_types_json, industries_json, competencies_json,
                superpowers_json, constraints_text, linkedin_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, profile_data['role'], profile_data['current_location'],
            profile_data['target_location'], profile_data['level'],
            profile_data['deadline_weeks'], profile_data['target_end_date'],
            profile_data.get('preferred_funnel_type', 'active'), profile_data.get('role_synonyms_json'), 
            profile_data.get('salary_min'), profile_data.get('salary_max'), profile_data.get('salary_currency'),
            profile_data.get('salary_period'), profile_data.get('company_types_json'),
            profile_data.get('industries_json'), profile_data.get('competencies_json'),
            profile_data.get('superpowers_json'), profile_data.get('constraints_text'),
            profile_data.get('linkedin_url')
        ))

    conn.commit()

    # Set the user's active funnel to match their profile preference
    funnel_type = profile_data.get('preferred_funnel_type', 'active')
    set_active_funnel(user_id, funnel_type)

    conn.close()
    return True

def get_profile(user_id: int) -> dict:
    """Get user profile"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        return dict(profile)
    return {}

def delete_profile(user_id: int) -> bool:
    """Delete user profile"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted

def get_reflection_history(user_id: int, limit: int = 10):
    """Get reflection history for user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            section_stage, events_count, funnel_type, channel, 
            week_start, rating_overall, strengths, weaknesses, 
            rating_mood, reject_after_stage, reject_reasons_json, 
            reject_reason_other, created_at
        FROM event_feedback 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))

    reflections = []
    for row in cursor.fetchall():
        reflections.append(dict(row))

    conn.close()
    return reflections

def record_payment_click(user_id: int):
    """Записать клик по кнопке оплаты"""
    conn = get_db_connection()
    c = conn.cursor()

    # Проверяем, есть ли уже запись для этого пользователя
    c.execute('SELECT click_count FROM payment_clicks WHERE user_id = ?', (user_id,))
    result = c.fetchone()

    if result:
        # Увеличиваем счётчик
        c.execute('''UPDATE payment_clicks 
                     SET click_count = click_count + 1, last_click_at = CURRENT_TIMESTAMP 
                     WHERE user_id = ?''', (user_id,))
    else:
        # Создаём новую запись
        c.execute('''INSERT INTO payment_clicks (user_id, click_count, first_click_at, last_click_at) 
                     VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)''', (user_id,))

    conn.commit()
    conn.close()

def get_payment_statistics():
    """Получить статистику кликов по оплате"""
    conn = get_db_connection()
    c = conn.cursor()

    # Общее количество уникальных пользователей, кликнувших на оплату
    c.execute('SELECT COUNT(*) FROM payment_clicks')
    unique_users = c.fetchone()[0]

    # Общее количество кликов
    c.execute('SELECT SUM(click_count) FROM payment_clicks')
    total_clicks = c.fetchone()[0] or 0

    conn.close()

    return {
        'unique_users': unique_users,
        'total_clicks': total_clicks
    }

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