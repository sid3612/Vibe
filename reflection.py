"""
Reflection form system for job search event logging (PRD v3.1)
Auto-triggers after counter increases, collects detailed feedback
"""

import json
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_db_connection

class ReflectionStates(StatesGroup):
    stage_type = State()
    rating = State()
    strengths = State()
    weaknesses = State()
    motivation = State()
    rejection_reason = State()
    rejection_custom = State()

class ReflectionForm:
    def __init__(self):
        self.pending_forms = {}  # user_id -> queue of forms to fill
        
    def should_trigger_reflection(self, user_id: int, old_data: dict, new_data: dict) -> bool:
        """Check if reflection form should be triggered based on counter increases"""
        # Calculate deltas for each counter (excluding applications/views)
        trigger_fields = ['responses', 'screenings', 'onsites', 'offers', 'rejections']
        
        total_delta = 0
        for field in trigger_fields:
            old_val = old_data.get(field, 0) if old_data else 0
            new_val = new_data.get(field, 0)
            delta = new_val - old_val
            if delta > 0:
                total_delta += delta
        
        return total_delta >= 1
    
    def create_reflection_queue(self, user_id: int, old_data: dict, new_data: dict):
        """Create queue of reflection forms based on counter increases"""
        trigger_fields = ['responses', 'screenings', 'onsites', 'offers', 'rejections']
        
        queue = []
        for field in trigger_fields:
            old_val = old_data.get(field, 0) if old_data else 0
            new_val = new_data.get(field, 0)
            delta = new_val - old_val
            
            # Add forms for each increase
            for _ in range(delta):
                queue.append({
                    'stage_hint': field,
                    'created_at': new_data.get('week_start', ''),
                    'channel': new_data.get('channel', ''),
                    'funnel_type': new_data.get('funnel_type', 'active')
                })
        
        self.pending_forms[user_id] = queue
        return len(queue)

    def get_stage_type_keyboard(self):
        """Get keyboard for stage type selection"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✉️ Ответ", callback_data="stage_response"),
                InlineKeyboardButton(text="📞 Скрининг", callback_data="stage_screening")
            ],
            [
                InlineKeyboardButton(text="🧑‍💼 Онсайт", callback_data="stage_onsite"),
                InlineKeyboardButton(text="🏁 Оффер", callback_data="stage_offer")
            ],
            [
                InlineKeyboardButton(text="❌ Отказ без интервью", callback_data="stage_reject_no_interview"),
                InlineKeyboardButton(text="❌❌ Отказ после интервью", callback_data="stage_reject_after_interview")
            ],
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="reflection_cancel")]
        ])
        return keyboard

    def get_rating_keyboard(self):
        """Get 1-5 rating keyboard"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
                InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
                InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
                InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
                InlineKeyboardButton(text="5️⃣", callback_data="rating_5")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="reflection_back")]
        ])
        return keyboard

    def get_skip_keyboard(self):
        """Get keyboard with skip option"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="reflection_skip")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="reflection_back")]
        ])
        return keyboard

    def get_rejection_reasons_keyboard(self):
        """Get keyboard for rejection reasons (multi-select)"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Нет нужного навыка", callback_data="reject_skill"),
                InlineKeyboardButton(text="Нет культурного совпадения", callback_data="reject_culture")
            ],
            [
                InlineKeyboardButton(text="Локация/виза", callback_data="reject_location"),
                InlineKeyboardButton(text="Язык", callback_data="reject_language")
            ],
            [
                InlineKeyboardButton(text="Зарплата/бюджет", callback_data="reject_salary"),
                InlineKeyboardButton(text="Нет доменного опыта", callback_data="reject_domain")
            ],
            [
                InlineKeyboardButton(text="Сроки/доступность", callback_data="reject_timing"),
                InlineKeyboardButton(text="Другое", callback_data="reject_other")
            ],
            [InlineKeyboardButton(text="✅ Готово", callback_data="reject_done")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="reflection_back")]
        ])
        return keyboard

    def get_rejection_stage_keyboard(self):
        """Get keyboard for rejection stage selection"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 После скрининга", callback_data="reject_after_screening"),
                InlineKeyboardButton(text="🧑‍💼 После онсайта", callback_data="reject_after_onsite")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="reflection_back")]
        ])
        return keyboard

# Database functions for reflection logs
def init_reflection_db():
    """Initialize reflection logs table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reflection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            funnel_type TEXT NOT NULL,
            stage_type TEXT NOT NULL,
            rating INTEGER,
            strengths TEXT,
            weaknesses TEXT,
            motivation INTEGER,
            rejection_reasons TEXT,
            rejection_stage TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_reflection_log(user_id: int, reflection_data: dict):
    """Save reflection log to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO reflection_logs (
            user_id, week_start, channel_name, funnel_type, stage_type,
            rating, strengths, weaknesses, motivation, rejection_reasons, rejection_stage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        reflection_data.get('week_start'),
        reflection_data.get('channel'),
        reflection_data.get('funnel_type'),
        reflection_data.get('stage_type'),
        reflection_data.get('rating'),
        reflection_data.get('strengths'),
        reflection_data.get('weaknesses'),
        reflection_data.get('motivation'),
        json.dumps(reflection_data.get('rejection_reasons', [])),
        reflection_data.get('rejection_stage')
    ))
    
    conn.commit()
    conn.close()

def get_user_reflection_logs(user_id: int, limit: int = 10):
    """Get user's recent reflection logs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM reflection_logs 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results] if results else []

# Global reflection form instance
reflection_form = ReflectionForm()

async def prompt_reflection_form(message: types.Message, user_id: int, old_data: dict, new_data: dict):
    """Prompt user to fill reflection form after counter increases"""
    if not reflection_form.should_trigger_reflection(user_id, old_data, new_data):
        return False
    
    # Create queue
    form_count = reflection_form.create_reflection_queue(user_id, old_data, new_data)
    
    # Ask user if they want to fill forms
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Да", callback_data="reflection_start"),
        InlineKeyboardButton("❌ Нет", callback_data="reflection_decline")
    )
    
    prompt_text = f"""
🔄 Изменения в счётчиках обнаружены!

Заполнить форму рефлексии сейчас?

📝 Количество форм: {form_count}
💡 Это поможет улучшить вашу воронку поиска работы
"""
    
    await message.answer(prompt_text, reply_markup=keyboard)
    return True

async def start_reflection_form(callback_query: types.CallbackQuery, state: FSMContext):
    """Start the reflection form process"""
    user_id = callback_query.from_user.id
    
    if user_id not in reflection_form.pending_forms or not reflection_form.pending_forms[user_id]:
        await callback_query.answer("Нет форм для заполнения")
        return
    
    # Get first form from queue
    current_form = reflection_form.pending_forms[user_id][0]
    remaining_forms = len(reflection_form.pending_forms[user_id])
    
    await state.update_data(current_form=current_form, selected_rejection_reasons=[])
    
    form_text = f"""
📝 Форма рефлексии ({remaining_forms} осталось)

Что произошло на этом этапе?
Выберите тип события:
"""
    
    await callback_query.message.edit_text(
        form_text, 
        reply_markup=reflection_form.get_stage_type_keyboard()
    )
    await ReflectionStates.stage_type.set()

async def process_stage_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Process stage type selection"""
    stage_type = callback_query.data.replace("stage_", "")
    await state.update_data(stage_type=stage_type)
    
    # Map stage types to display names
    stage_names = {
        'response': 'Ответ',
        'screening': 'Скрининг', 
        'onsite': 'Онсайт',
        'offer': 'Оффер',
        'reject_no_interview': 'Отказ без интервью',
        'reject_after_interview': 'Отказ после интервью'
    }
    
    stage_name = stage_names.get(stage_type, stage_type)
    
    # Handle rejection cases
    if stage_type in ['reject_no_interview', 'reject_after_interview']:
        if stage_type == 'reject_after_interview':
            # Ask for rejection stage
            await callback_query.message.edit_text(
                f"❌ {stage_name}\n\nПосле какого этапа произошел отказ?",
                reply_markup=reflection_form.get_rejection_stage_keyboard()
            )
            return
        else:
            # Skip rating for rejections without interview
            await state.update_data(rating=None)
            await callback_query.message.edit_text(
                f"❌ {stage_name}\n\nУкажите причины отказа (можно выбрать несколько):",
                reply_markup=reflection_form.get_rejection_reasons_keyboard()
            )
            await ReflectionStates.rejection_reason.set()
            return
    
    # Regular stages - ask for rating
    await callback_query.message.edit_text(
        f"✅ {stage_name}\n\nКак прошло?\n1 — очень плохо … 5 — отлично",
        reply_markup=reflection_form.get_rating_keyboard()
    )
    await ReflectionStates.rating.set()

async def process_rejection_stage(callback_query: types.CallbackQuery, state: FSMContext):
    """Process rejection stage selection"""
    rejection_stage = callback_query.data.replace("reject_after_", "")
    await state.update_data(rejection_stage=rejection_stage, rating=None)
    
    await callback_query.message.edit_text(
        "❌ Отказ после интервью\n\nУкажите причины отказа (можно выбрать несколько):",
        reply_markup=reflection_form.get_rejection_reasons_keyboard()
    )
    await ReflectionStates.rejection_reason.set()

async def process_rating(callback_query: types.CallbackQuery, state: FSMContext):
    """Process rating selection"""
    rating = int(callback_query.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    
    await callback_query.message.edit_text(
        f"Оценка: {rating}/5\n\nОтмеченные сильные стороны (необязательно):\n\nНапишите текст или нажмите 'Пропустить'",
        reply_markup=reflection_form.get_skip_keyboard()
    )
    await ReflectionStates.strengths.set()

async def process_rejection_reasons(callback_query: types.CallbackQuery, state: FSMContext):
    """Process rejection reasons selection"""
    data = await state.get_data()
    selected_reasons = data.get('selected_rejection_reasons', [])
    
    if callback_query.data == "reject_done":
        # Finish selection
        await state.update_data(rejection_reasons=selected_reasons)
        await ask_motivation(callback_query, state)
        return
    elif callback_query.data == "reject_other":
        # Ask for custom reason
        await callback_query.message.edit_text(
            "Укажите другую причину отказа:",
            reply_markup=reflection_form.get_skip_keyboard()
        )
        await ReflectionStates.rejection_custom.set()
        return
    
    # Toggle reason selection
    reason = callback_query.data.replace("reject_", "")
    reason_names = {
        'skill': 'Нет нужного навыка',
        'culture': 'Нет культурного совпадения',
        'location': 'Локация/виза',
        'language': 'Язык',
        'salary': 'Зарплата/бюджет',
        'domain': 'Нет доменного опыта',
        'timing': 'Сроки/доступность'
    }
    
    reason_name = reason_names.get(reason, reason)
    
    if reason_name in selected_reasons:
        selected_reasons.remove(reason_name)
    else:
        selected_reasons.append(reason_name)
    
    await state.update_data(selected_rejection_reasons=selected_reasons)
    
    # Update display
    selected_text = "\n".join(f"✓ {r}" for r in selected_reasons) if selected_reasons else "Ничего не выбрано"
    
    await callback_query.message.edit_text(
        f"Причины отказа:\n{selected_text}\n\nВыберите причины или нажмите 'Готово':",
        reply_markup=reflection_form.get_rejection_reasons_keyboard()
    )

async def ask_motivation(callback_query: types.CallbackQuery, state: FSMContext):
    """Ask for motivation rating"""
    await callback_query.message.edit_text(
        "Самочувствие и мотивация:\n1 — выжат в ноль … 5 — на подъёме",
        reply_markup=reflection_form.get_rating_keyboard()
    )
    await ReflectionStates.motivation.set()

async def process_motivation(callback_query: types.CallbackQuery, state: FSMContext):
    """Process motivation rating and save form"""
    motivation = int(callback_query.data.replace("rating_", ""))
    user_id = callback_query.from_user.id
    
    # Get all form data
    data = await state.get_data()
    current_form = data.get('current_form', {})
    
    # Prepare reflection data
    reflection_data = {
        'week_start': current_form.get('created_at'),
        'channel': current_form.get('channel'),
        'funnel_type': current_form.get('funnel_type'),
        'stage_type': data.get('stage_type'),
        'rating': data.get('rating'),
        'strengths': data.get('strengths'),
        'weaknesses': data.get('weaknesses'),
        'motivation': motivation,
        'rejection_reasons': data.get('rejection_reasons', []),
        'rejection_stage': data.get('rejection_stage')
    }
    
    # Save reflection log
    save_reflection_log(user_id, reflection_data)
    
    # Remove completed form from queue
    if user_id in reflection_form.pending_forms:
        reflection_form.pending_forms[user_id].pop(0)
        remaining = len(reflection_form.pending_forms[user_id])
        
        if remaining > 0:
            # Ask about next form
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ Продолжить", callback_data="reflection_continue"),
                InlineKeyboardButton("❌ Завершить", callback_data="reflection_finish")
            )
            
            await callback_query.message.edit_text(
                f"✅ Форма сохранена!\n\nОсталось форм: {remaining}\nПродолжить заполнение?",
                reply_markup=keyboard
            )
        else:
            # All forms completed
            await callback_query.message.edit_text("🎉 Все формы рефлексии заполнены!\nСпасибо за детальную обратную связь.")
            await state.finish()
    else:
        await callback_query.message.edit_text("✅ Форма рефлексии сохранена!")
        await state.finish()

# Text message handlers for optional fields
async def process_strengths_text(message: types.Message, state: FSMContext):
    """Process strengths text input"""
    await state.update_data(strengths=message.text.strip())
    
    await message.answer(
        "Отмеченные слабые стороны / пробелы (необязательно):\n\nНапишите текст или нажмите 'Пропустить'",
        reply_markup=reflection_form.get_skip_keyboard()
    )
    await ReflectionStates.weaknesses.set()

async def process_weaknesses_text(message: types.Message, state: FSMContext):
    """Process weaknesses text input"""
    await state.update_data(weaknesses=message.text.strip())
    await ask_motivation_from_text(message, state)

async def process_rejection_custom_text(message: types.Message, state: FSMContext):
    """Process custom rejection reason"""
    data = await state.get_data()
    selected_reasons = data.get('selected_rejection_reasons', [])
    selected_reasons.append(message.text.strip())
    
    await state.update_data(rejection_reasons=selected_reasons)
    await ask_motivation_from_text(message, state)

async def ask_motivation_from_text(message: types.Message, state: FSMContext):
    """Ask for motivation rating from text handler"""
    await message.answer(
        "Самочувствие и мотивация:\n1 — выжат в ноль … 5 — на подъёме",
        reply_markup=reflection_form.get_rating_keyboard()
    )
    await ReflectionStates.motivation.set()

# Manual reflection command
async def cmd_log_event(message: types.Message, state: FSMContext):
    """Manual event logging command"""
    user_id = message.from_user.id
    
    # Create a single manual form
    reflection_form.pending_forms[user_id] = [{
        'stage_hint': 'manual',
        'created_at': '',
        'channel': '',
        'funnel_type': 'manual'
    }]
    
    await message.answer(
        "📝 Ручное заполнение формы рефлексии\n\nЧто произошло на этом этапе?",
        reply_markup=reflection_form.get_stage_type_keyboard()
    )
    await ReflectionStates.stage_type.set()

# Initialize reflection database on import
init_reflection_db()