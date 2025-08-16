"""
Reflection Forms System - PRD v3 Implementation
Automatic reflection form suggestions after counter increases
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from db import get_db_connection

class ReflectionStates(StatesGroup):
    """FSM states for reflection form"""
    stage_type = State()
    rating = State()
    strengths = State()
    weaknesses = State()
    mood_motivation = State()
    rejection_reason = State()
    rejection_other = State()

class ReflectionQueue:
    """Manage reflection form queue"""
    
    @staticmethod
    def create_queue_entries(user_id: int, week_start: str, channel: str, funnel_type: str, 
                           stage: str, delta: int) -> List[int]:
        """Create queue entries for reflection forms"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create reflection_queue table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                channel TEXT NOT NULL,
                funnel_type TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                form_data TEXT NULL
            )
        """)
        
        entry_ids = []
        for _ in range(delta):
            cursor.execute("""
                INSERT INTO reflection_queue 
                (user_id, week_start, channel, funnel_type, stage, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, (user_id, week_start, channel, funnel_type, stage))
            entry_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        return entry_ids
    
    @staticmethod
    def get_pending_forms(user_id: int) -> List[Dict]:
        """Get all pending reflection forms for user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reflection_queue 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at ASC
        """, (user_id,))
        
        forms = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return forms
    
    @staticmethod
    def get_next_form(user_id: int) -> Optional[Dict]:
        """Get next pending form for user"""
        forms = ReflectionQueue.get_pending_forms(user_id)
        return forms[0] if forms else None
    
    @staticmethod
    def complete_form(form_id: int, form_data: Dict):
        """Mark form as completed with data"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reflection_queue 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP, form_data = ?
            WHERE id = ?
        """, (json.dumps(form_data), form_id))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def skip_form(form_id: int):
        """Mark form as skipped"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reflection_queue 
            SET status = 'skipped', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (form_id,))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def void_latest_forms(user_id: int, week_start: str, channel: str, funnel_type: str, 
                         stage: str, count: int):
        """Mark latest pending forms as void due to counter decrease"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reflection_queue 
            SET status = 'void'
            WHERE user_id = ? AND week_start = ? AND channel = ? AND funnel_type = ? 
                  AND stage = ? AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, week_start, channel, funnel_type, stage, count))
        
        conn.commit()
        conn.close()

class ReflectionTrigger:
    """Handle reflection form triggers after counter changes"""
    
    # Mapping of stage names to database fields and CVR descriptions
    STAGE_MAPPING = {
        'active': {
            'responses': {
                'field': 'responses',
                'display': '✉️ Ответ',
                'cvr': 'CVR1 = Ответы/Подачи',
                'hypotheses': ['H1', 'H2']
            },
            'screenings': {
                'field': 'screenings', 
                'display': '📞 Скрининг',
                'cvr': 'CVR2 = Скрининги/Ответы',
                'hypotheses': ['H2', 'H3']
            },
            'onsites': {
                'field': 'onsites',
                'display': '🧑‍💼 Онсайт', 
                'cvr': 'CVR3 = Онсайты/Скрининги',
                'hypotheses': ['H3', 'H4']
            },
            'offers': {
                'field': 'offers',
                'display': '🏁 Оффер',
                'cvr': 'CVR4 = Офферы/Онсайты', 
                'hypotheses': ['H5']
            },
            'rejections': {
                'field': 'rejections',
                'display': '❌ Отказ',
                'cvr': 'не влияет на CVR',
                'hypotheses': []
            }
        },
        'passive': {
            'incoming': {
                'field': 'incoming',
                'display': '✉️ Входящий',
                'cvr': 'CVR1 = Входящие/Просмотры',
                'hypotheses': ['H1', 'H2']
            },
            'screenings': {
                'field': 'screenings',
                'display': '📞 Скрининг', 
                'cvr': 'CVR2 = Скрининги/Входящие',
                'hypotheses': ['H2', 'H3']
            },
            'onsites': {
                'field': 'onsites',
                'display': '🧑‍💼 Онсайт',
                'cvr': 'CVR3 = Онсайты/Скрининги', 
                'hypotheses': ['H3', 'H4']
            },
            'offers': {
                'field': 'offers',
                'display': '🏁 Оффер',
                'cvr': 'CVR4 = Офферы/Онсайты',
                'hypotheses': ['H5']
            },
            'rejections': {
                'field': 'rejections',
                'display': '❌ Отказ',
                'cvr': 'не влияет на CVR',
                'hypotheses': []
            }
        }
    }
    
    @staticmethod
    def check_triggers(user_id: int, week_start: str, channel: str, funnel_type: str,
                      old_data: Dict, new_data: Dict) -> List[Tuple[str, int]]:
        """Check which counters increased and return triggers with deltas"""
        triggers = []
        
        if funnel_type not in ReflectionTrigger.STAGE_MAPPING:
            return triggers
        
        stage_config = ReflectionTrigger.STAGE_MAPPING[funnel_type]
        
        for stage_name, config in stage_config.items():
            field = config['field']
            old_value = old_data.get(field, 0)
            new_value = new_data.get(field, 0)
            
            # Skip views/inbounds for passive funnel as specified
            if funnel_type == 'passive' and field in ['views']:
                continue
                
            delta = new_value - old_value
            if delta >= 1:
                triggers.append((stage_name, delta))
        
        return triggers
    
    @staticmethod
    async def offer_reflection_form(message: types.Message, user_id: int, week_start: str, 
                                  channel: str, funnel_type: str, triggers: List[Tuple[str, int]]):
        """Offer reflection form to user after triggers detected"""
        if not triggers:
            return
        
        # Create summary of what increased
        trigger_text = []
        for stage, delta in triggers:
            stage_config = ReflectionTrigger.STAGE_MAPPING[funnel_type][stage]
            trigger_text.append(f"{stage_config['display']}: +{delta}")
        
        text = f"""
📊 Обнаружены изменения в воронке!

📅 Неделя: {week_start}
📢 Канал: {channel}
🔄 Тип: {'Активная' if funnel_type == 'active' else 'Пассивная'} воронка

Изменения:
{chr(10).join(trigger_text)}

Заполнить форму рефлексии сейчас? Это поможет проанализировать ваш прогресс и выявить закономерности.
        """
        
        # Store trigger data in callback data
        trigger_data = {
            'week_start': week_start,
            'channel': channel, 
            'funnel_type': funnel_type,
            'triggers': triggers
        }
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("✅ Да", 
                                     callback_data=f"reflection_yes_{json.dumps(trigger_data)}"[:64]),
            types.InlineKeyboardButton("❌ Нет", 
                                     callback_data="reflection_no")
        )
        
        await message.answer(text.strip(), reply_markup=keyboard)

def get_stage_type_keyboard():
    """Get keyboard for stage type selection"""
    keyboard = types.InlineKeyboardMarkup()
    
    keyboard.add(
        types.InlineKeyboardButton("✉️ Ответ", callback_data="stage_response"),
        types.InlineKeyboardButton("📞 Скрининг", callback_data="stage_screening")
    )
    keyboard.add(
        types.InlineKeyboardButton("🧑‍💼 Онсайт", callback_data="stage_onsite"),
        types.InlineKeyboardButton("🏁 Оффер", callback_data="stage_offer")
    )
    keyboard.add(
        types.InlineKeyboardButton("❌ Отказ без интервью", callback_data="stage_rejection_early"),
        types.InlineKeyboardButton("❌❌ Отказ после интервью", callback_data="stage_rejection_late")
    )
    
    return keyboard

def get_rating_keyboard():
    """Get keyboard for 1-5 rating"""
    keyboard = types.InlineKeyboardMarkup()
    buttons = []
    for i in range(1, 6):
        buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"rating_{i}"))
    
    keyboard.add(*buttons)
    return keyboard

def get_rejection_reasons_keyboard():
    """Get keyboard for rejection reasons (multi-select)"""
    keyboard = types.InlineKeyboardMarkup()
    
    reasons = [
        ("skill", "Нет нужного навыка"),
        ("culture", "Нет культурного совпадения"), 
        ("location", "Локация/виза"),
        ("language", "Язык"),
        ("salary", "Зарплата/бюджет"),
        ("domain", "Нет доменного опыта"),
        ("timing", "Сроки/доступность"),
        ("other", "Другое")
    ]
    
    for code, text in reasons:
        keyboard.add(types.InlineKeyboardButton(f"☐ {text}", callback_data=f"reason_{code}"))
    
    keyboard.add(types.InlineKeyboardButton("✅ Готово", callback_data="reasons_done"))
    return keyboard

async def handle_reflection_yes(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle user agreeing to fill reflection form"""
    try:
        # Parse trigger data from callback
        trigger_data_str = callback_query.data.replace("reflection_yes_", "")
        trigger_data = json.loads(trigger_data_str)
        
        week_start = trigger_data['week_start']
        channel = trigger_data['channel']
        funnel_type = trigger_data['funnel_type']
        triggers = trigger_data['triggers']
        
        # Create queue entries for all triggers
        total_forms = 0
        for stage, delta in triggers:
            entry_ids = ReflectionQueue.create_queue_entries(
                callback_query.from_user.id, week_start, channel, funnel_type, stage, delta
            )
            total_forms += len(entry_ids)
        
        await callback_query.message.edit_text(
            f"✅ Создано {total_forms} форм рефлексии.\nНачинаем заполнение первой формы..."
        )
        
        # Start first form
        await start_next_reflection_form(callback_query.message, callback_query.from_user.id, state)
        
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Ошибка при создании форм: {str(e)}")

async def handle_reflection_no(callback_query: types.CallbackQuery):
    """Handle user declining reflection form"""
    await callback_query.message.edit_text(
        "📋 Формы рефлексии не созданы.\nВы можете заполнить их позже командой /log_event"
    )

async def start_next_reflection_form(message: types.Message, user_id: int, state: FSMContext):
    """Start next reflection form from queue"""
    next_form = ReflectionQueue.get_next_form(user_id)
    
    if not next_form:
        await message.answer("✅ Все формы рефлексии заполнены!")
        return
    
    # Store form context in state
    await state.update_data(
        form_id=next_form['id'],
        week_start=next_form['week_start'],
        channel=next_form['channel'],
        funnel_type=next_form['funnel_type'],
        stage=next_form['stage']
    )
    
    # Show form header and stage selection
    header_text = f"""
📋 Форма рефлексии

📅 Неделя: {next_form['week_start']}
📢 Канал: {next_form['channel']}
🔄 Тип: {'Активная' if next_form['funnel_type'] == 'active' else 'Пассивная'} воронка

Выберите тип этапа:
    """
    
    keyboard = get_stage_type_keyboard()
    keyboard.add(
        types.InlineKeyboardButton("⏭ Пропустить", callback_data="skip_form"),
        types.InlineKeyboardButton("🗑 Отменить", callback_data="cancel_form")
    )
    
    await message.answer(header_text.strip(), reply_markup=keyboard)
    await ReflectionStates.stage_type.set()

# Command handlers for manual reflection forms
async def cmd_log_event(message: types.Message, state: FSMContext):
    """Manual reflection form command"""
    await message.answer(
        "📋 Ручное создание формы рефлексии\n\n"
        "Сначала выберите неделю и канал для которых хотите создать форму."
    )
    # Implementation would continue with week/channel selection

async def cmd_pending_forms(message: types.Message, state: FSMContext):
    """Show and start filling pending forms"""
    pending = ReflectionQueue.get_pending_forms(message.from_user.id)
    
    if not pending:
        await message.answer("📋 У вас нет незаполненных форм рефлексии.")
        return
    
    await message.answer(f"📋 У вас {len(pending)} незаполненных форм рефлексии.\nНачинаем заполнение...")
    await start_next_reflection_form(message, message.from_user.id, state)

async def cmd_last_events(message: types.Message):
    """Show last reflection events"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT week_start, channel, funnel_type, stage, completed_at, form_data
        FROM reflection_queue 
        WHERE user_id = ? AND status = 'completed'
        ORDER BY completed_at DESC 
        LIMIT 10
    """, (message.from_user.id,))
    
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await message.answer("📋 У вас пока нет записей рефлексии.")
        return
    
    text = "📋 Последние события рефлексии:\n\n"
    for event in events:
        week, channel, funnel_type, stage, completed_at, form_data_str = event
        date = completed_at[:10] if completed_at else "неизвестно"
        text += f"• {date} | {week} | {channel} | {stage}\n"
    
    await message.answer(text)