"""
PRD v3.1 Implementation - Single Reflection Form MVP
Simplified reflection system with one combined form for all increased stages
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from db import get_db_connection

class ReflectionV31States(StatesGroup):
    """FSM states for PRD v3.1 reflection form"""
    # Single form with multiple sections
    section_rating = State()
    section_reject_type = State()  # New state for rejection type
    section_strengths = State() 
    section_weaknesses = State()
    section_mood = State()
    section_reject_reasons = State()
    section_reject_other = State()

class ReflectionV31System:
    """PRD v3.1 Reflection System - Single Form MVP"""
    
    @staticmethod
    def init_event_feedback_table():
        """Initialize event_feedback table according to PRD v3.1"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def check_reflection_trigger(user_id: int, week_start: str, channel: str, 
                               funnel_type: str, old_data: dict, new_data: dict) -> List[Dict]:
        """
        Check if reflection form should be triggered according to PRD v3.1
        Only triggers on: Responses, Screenings, Onsites, Offers, Rejections (+≥1)
        Returns list of sections (stages) with delta > 0
        """
        # Trigger fields according to PRD v3.1
        trigger_fields = {
            'responses': 'response',
            'screenings': 'screening', 
            'onsites': 'onsite',
            'offers': 'offer',
            'rejections': 'reject_no_interview'  # Will handle rejection types in form
        }
        
        sections = []
        total_delta = 0
        
        for field, stage in trigger_fields.items():
            old_value = old_data.get(field, 0)
            new_value = new_data.get(field, 0)
            delta = new_value - old_value
            
            if delta >= 1:
                sections.append({
                    'stage': stage,
                    'field': field,
                    'delta': delta,
                    'stage_display': ReflectionV31System.get_stage_display(stage)
                })
                total_delta += delta
        
        return sections if total_delta >= 1 else []
    
    @staticmethod
    def get_stage_display(stage: str) -> str:
        """Get display text for stage"""
        stage_map = {
            'response': '✉️ Ответ',
            'screening': '📞 Скрининг',
            'onsite': '🧑‍💼 Онсайт', 
            'offer': '🏁 Оффер',
            'reject_no_interview': '❌ Реджект без интервью',
            'reject_after_interview': '❌❌ Реджект после интервью'
        }
        return stage_map.get(stage, stage)
    
    @staticmethod
    async def offer_reflection_form(message: types.Message, user_id: int, week_start: str, 
                                  channel: str, funnel_type: str, sections: List[Dict]):
        """Show reflection form offer according to PRD v3.1"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"reflection_v31_yes_{len(sections)}")],
            [InlineKeyboardButton(text="Нет", callback_data="reflection_v31_no")]
        ])
        
        # Create sections summary
        sections_text = ", ".join([s['stage_display'] for s in sections])
        
        await message.answer(
            f"📝 Заполнить форму рефлексии сейчас?\n\n"
            f"Обнаружены изменения в этапах:\n{sections_text}",
            reply_markup=keyboard
        )
        
        # Note: State will be managed by the calling handler
    
    @staticmethod
    def get_combined_form_keyboard(sections: List[Dict]) -> InlineKeyboardMarkup:
        """Get keyboard for combined reflection form"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сохранить", callback_data="reflection_v31_save")],
            [InlineKeyboardButton(text="Отмена", callback_data="reflection_v31_cancel")]
        ])
    
    @staticmethod
    def get_rating_keyboard() -> InlineKeyboardMarkup:
        """Get 1-5 rating keyboard"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
                InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
                InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
                InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
                InlineKeyboardButton(text="5️⃣", callback_data="rating_5")
            ]
        ])
    
    @staticmethod
    def get_rejection_reasons_keyboard() -> InlineKeyboardMarkup:
        """Get rejection reasons keyboard for multi-select"""
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
        
        keyboard = []
        for reason_code, reason_text in reasons:
            keyboard.append([InlineKeyboardButton(
                text=f"☐ {reason_text}", 
                callback_data=f"reason_v31_{reason_code}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="Готово", callback_data="reasons_v31_done")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def save_reflection_data(user_id: int, week_start: str, channel: str, funnel_type: str,
                           sections: List[Dict], form_data: Dict) -> bool:
        """Save completed reflection form data to event_feedback table"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Save one record per section
            for section in sections:
                stage = section['stage']
                events_count = section['delta']
                
                # Extract form data for this section
                section_data = form_data.get(f"section_{stage}", {})
                
                cursor.execute("""
                    INSERT INTO event_feedback 
                    (user_id, funnel_type, channel, week_start, section_stage, events_count,
                     rating_overall, strengths, weaknesses, rating_mood, 
                     reject_after_stage, reject_reasons_json, reject_reason_other)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, funnel_type, channel, week_start, stage, events_count,
                    section_data.get('rating_overall'),
                    section_data.get('strengths'),
                    section_data.get('weaknesses'), 
                    section_data.get('rating_mood'),
                    section_data.get('reject_after_stage'),
                    json.dumps(section_data.get('reject_reasons', [])) if section_data.get('reject_reasons') else None,
                    section_data.get('reject_reason_other')
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving reflection data: {e}")
            return False

# Handlers for PRD v3.1 reflection system
async def handle_reflection_v31_yes(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle 'Yes' for reflection form offer"""
    if not callback_query.message:
        await callback_query.answer("Ошибка: сообщение недоступно")
        return
        
    data = await state.get_data()
    sections = data.get('reflection_sections', [])
    context = data.get('reflection_context', {})
    
    if not sections:
        await callback_query.answer("Ошибка: нет данных о секциях")
        return
    
    # Start combined form - show first section
    if callback_query.message and hasattr(callback_query.message, 'edit_text'):
        await start_combined_reflection_form(callback_query.message, state, sections, context)
    await callback_query.answer()

async def handle_reflection_v31_no(callback_query: types.CallbackQuery):
    """Handle 'No' for reflection form offer"""
    if callback_query.message and hasattr(callback_query.message, 'edit_text'):
        await callback_query.message.edit_text("Хорошо, форма рефлексии пропущена.")
    await callback_query.answer()

async def start_combined_reflection_form(message: types.Message, state: FSMContext, 
                                       sections: List[Dict], context: Dict):
    """Start the combined reflection form for all sections"""
    # Initialize form data structure
    form_data = {}
    for section in sections:
        form_data[f"section_{section['stage']}"] = {
            'stage': section['stage'],
            'delta': section['delta'],
            'stage_display': section.get('stage_display', ReflectionV31System.get_stage_display(section['stage']))
        }
    
    await state.update_data(
        current_form_data=form_data,
        current_sections=sections,
        current_section_index=0,
        reflection_context=context
    )
    
    # Start with first section
    await process_next_section(message, state)

async def process_next_section(message: types.Message, state: FSMContext):
    """Process the next section in the combined form"""
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    
    if section_index >= len(sections):
        # All sections completed - save and finish
        await save_and_complete_form(message, state)
        return
    
    current_section = sections[section_index]
    stage_display = current_section.get('stage_display', ReflectionV31System.get_stage_display(current_section['stage']))
    delta = current_section['delta']
    
    # Show section header and ask for rating
    context = data.get('reflection_context', {})
    funnel_type = context.get('funnel_type', '')
    week_start = context.get('week_start', '')
    channel = context.get('channel', '')
    
    header_text = f"📝 Форма рефлексии\n\n"
    header_text += f"Неделя: {week_start} • Канал: {channel} • Тип: {funnel_type}\n\n"
    header_text += f"Секция {section_index + 1}/{len(sections)}: {stage_display} (+{delta})\n\n"
    header_text += f"Как прошло? Оцените от 1 (очень плохо) до 5 (отлично):"
    
    await message.edit_text(header_text, reply_markup=ReflectionV31System.get_rating_keyboard())
    await state.set_state(ReflectionV31States.section_rating)

async def handle_section_rating(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle rating selection for current section"""
    if not callback_query.data or not callback_query.message:
        await callback_query.answer("Ошибка обработки")
        return
        
    rating = int(callback_query.data.split('_')[1])
    
    # Save rating to current section
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['rating_overall'] = rating
    
    await state.update_data(current_form_data=form_data)
    
    # Check if this is a rejection section - ask for rejection type first
    if current_section['stage'] == 'reject_no_interview':
        reject_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Реджект без интервью", callback_data="reject_type_no_interview")],
            [InlineKeyboardButton(text="Реджект после интервью с рекрутером", callback_data="reject_type_recruiter")],
            [InlineKeyboardButton(text="Реджект после тех интервью", callback_data="reject_type_technical")]
        ])
        
        if hasattr(callback_query.message, 'edit_text'):
            await callback_query.message.edit_text(
                f"Оценка: {rating}/5\n\n"
                f"Тип отказа?",
                reply_markup=reject_type_keyboard
            )
        await state.set_state(ReflectionV31States.section_reject_type)
    else:
        # For non-rejection sections, proceed to strengths
        skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_strengths")]
        ])
        
        if hasattr(callback_query.message, 'edit_text'):
            await callback_query.message.edit_text(
                f"Оценка: {rating}/5\n\n"
                f"Отмеченные сильные стороны:",
                reply_markup=skip_keyboard
            )
        await state.set_state(ReflectionV31States.section_strengths)
    
    await callback_query.answer()

async def handle_section_reject_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle rejection type selection"""
    if not callback_query.data or not callback_query.message:
        await callback_query.answer("Ошибка обработки")
        return
        
    # Extract rejection type from callback data
    reject_type_map = {
        "reject_type_no_interview": "Реджект без интервью",
        "reject_type_recruiter": "Реджект после интервью с рекрутером", 
        "reject_type_technical": "Реджект после тех интервью"
    }
    
    reject_type = reject_type_map.get(callback_query.data, "Неизвестный тип")
    
    # Save rejection type to current section
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['reject_type'] = reject_type
    
    await state.update_data(current_form_data=form_data)
    
    # Now proceed to strengths question
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_strengths")]
    ])
    
    if hasattr(callback_query.message, 'edit_text'):
        await callback_query.message.edit_text(
            f"Тип отказа: {reject_type}\n\n"
            f"Отмеченные сильные стороны:",
            reply_markup=skip_keyboard
        )
    await state.set_state(ReflectionV31States.section_strengths)
    await callback_query.answer()

async def handle_skip_strengths(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle skip strengths button"""
    await save_section_field(state, 'strengths', None)
    await ask_weaknesses(callback_query.message, state)
    await callback_query.answer()

async def handle_skip_weaknesses(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle skip weaknesses button"""
    await save_section_field(state, 'weaknesses', None)
    await ask_mood_rating(callback_query.message, state)
    await callback_query.answer()

async def save_section_field(state: FSMContext, field_name: str, value):
    """Save a field to the current section"""
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key][field_name] = value
    
    await state.update_data(current_form_data=form_data)

async def ask_weaknesses(message: types.Message, state: FSMContext):
    """Ask for weaknesses with skip button"""
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_weaknesses")]
    ])
    
    await message.edit_text("Отмеченные слабые стороны / пробелы:", reply_markup=skip_keyboard)
    await state.set_state(ReflectionV31States.section_weaknesses)

async def ask_mood_rating(message: types.Message, state: FSMContext):
    """Ask for mood rating"""
    await message.edit_text(
        "Самочувствие и мотивация после этого этапа (1-5):",
        reply_markup=ReflectionV31System.get_rating_keyboard()
    )
    await state.set_state(ReflectionV31States.section_mood)

async def handle_section_strengths(message: types.Message, state: FSMContext):
    """Handle strengths input for current section"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст")
        return
        
    strengths = message.text.strip()
    
    # Save strengths to current section
    await save_section_field(state, 'strengths', strengths)
    
    # Ask for weaknesses with skip button
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_weaknesses")]
    ])
    
    await message.answer("Отмеченные слабые стороны / пробелы:", reply_markup=skip_keyboard)
    await state.set_state(ReflectionV31States.section_weaknesses)

async def handle_section_weaknesses(message: types.Message, state: FSMContext):
    """Handle weaknesses input for current section"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст или 'пропустить'")
        return
        
    weaknesses = message.text.strip() if message.text.lower() != 'пропустить' else None
    
    # Save weaknesses to current section
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['weaknesses'] = weaknesses
    
    await state.update_data(current_form_data=form_data)
    
    # Ask for mood rating
    await message.answer(
        "Самочувствие и мотивация после этого этапа (1 - выжат в ноль, 5 - на подъёме):",
        reply_markup=ReflectionV31System.get_rating_keyboard()
    )
    await state.set_state(ReflectionV31States.section_mood)

async def handle_section_mood(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle mood rating for current section"""
    if not callback_query.data or not callback_query.message:
        await callback_query.answer("Ошибка обработки")
        return
        
    mood_rating = int(callback_query.data.split('_')[1])
    
    # Save mood rating to current section
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['rating_mood'] = mood_rating
    
    await state.update_data(current_form_data=form_data)
    
    # Check if this was a rejection stage
    if 'reject' in current_section['stage']:
        if hasattr(callback_query.message, 'edit_text'):
            await callback_query.message.edit_text(
                f"Самочувствие и мотивация: {mood_rating}/5\n\n"
                f"Выберите причины отказа (можно выбрать несколько):",
                reply_markup=ReflectionV31System.get_rejection_reasons_keyboard()
            )
        await state.update_data(selected_rejection_reasons=[])
        await state.set_state(ReflectionV31States.section_reject_reasons)
    else:
        # Move to next section
        if callback_query.message and hasattr(callback_query.message, 'edit_text'):
            await move_to_next_section(callback_query.message, state)
    
    await callback_query.answer()

async def handle_rejection_reasons(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle rejection reasons selection (multi-select)"""
    if not callback_query.data or not callback_query.message:
        await callback_query.answer("Ошибка обработки")
        return
        
    if callback_query.data == "reasons_v31_done":
        # Check if "other" was selected and needs text input
        data = await state.get_data()
        selected_reasons = data.get('selected_rejection_reasons', [])
        
        if 'other' in selected_reasons:
            if hasattr(callback_query.message, 'edit_text'):
                await callback_query.message.edit_text("Опишите другую причину отказа:")
            await state.set_state(ReflectionV31States.section_reject_other)
        else:
            # Save rejection reasons and move to next section
            if callback_query.message and hasattr(callback_query.message, 'edit_text'):
                await save_rejection_reasons_and_continue(callback_query.message, state, selected_reasons)
        await callback_query.answer()
        return
    
    # Toggle reason selection
    reason_code = callback_query.data.split('_')[2]  # reason_v31_CODE
    data = await state.get_data()
    selected_reasons = data.get('selected_rejection_reasons', [])
    
    if reason_code in selected_reasons:
        selected_reasons.remove(reason_code)
    else:
        selected_reasons.append(reason_code)
    
    await state.update_data(selected_rejection_reasons=selected_reasons)
    
    # Update keyboard to show selections
    keyboard = ReflectionV31System.get_rejection_reasons_keyboard()
    # Update button text to show selection state
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.callback_data and button.callback_data.startswith('reason_v31_'):
                code = button.callback_data.split('_')[2]
                if code in selected_reasons:
                    button.text = button.text.replace('☐', '☑️')
    
    if hasattr(callback_query.message, 'edit_reply_markup'):
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    await callback_query.answer()

async def handle_rejection_other(message: types.Message, state: FSMContext):
    """Handle other rejection reason text input"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите описание причины отказа")
        return
        
    other_reason = message.text.strip()
    
    data = await state.get_data()
    selected_reasons = data.get('selected_rejection_reasons', [])
    
    # Save rejection data
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['reject_reasons'] = selected_reasons
    form_data[section_key]['reject_reason_other'] = other_reason
    
    await state.update_data(current_form_data=form_data)
    
    # Move to next section - send new message instead of editing
    await message.answer("✅ Причина отказа сохранена. Переходим к следующей секции...")
    await move_to_next_section_new_message(message, state)

async def save_rejection_reasons_and_continue(message: types.Message, state: FSMContext, selected_reasons: List[str]):
    """Save rejection reasons and continue to next section"""
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    form_data = data.get('current_form_data', {})
    
    current_section = sections[section_index]
    section_key = f"section_{current_section['stage']}"
    form_data[section_key]['reject_reasons'] = selected_reasons
    
    await state.update_data(current_form_data=form_data)
    
    # Move to next section
    await move_to_next_section(message, state)

async def move_to_next_section(message: types.Message, state: FSMContext):
    """Move to the next section in the form"""
    data = await state.get_data()
    section_index = data.get('current_section_index', 0)
    
    # Increment section index
    await state.update_data(current_section_index=section_index + 1)
    
    # Process next section
    await process_next_section(message, state)

async def move_to_next_section_new_message(message: types.Message, state: FSMContext):
    """Move to the next section in the form - using new message instead of edit"""
    data = await state.get_data()
    section_index = data.get('current_section_index', 0)
    
    # Increment section index
    await state.update_data(current_section_index=section_index + 1)
    
    # Process next section with new message
    await process_next_section_new_message(message, state)

async def process_next_section_new_message(message: types.Message, state: FSMContext):
    """Process the next section in the combined form - using new message"""
    data = await state.get_data()
    sections = data.get('current_sections', [])
    section_index = data.get('current_section_index', 0)
    
    if section_index >= len(sections):
        # All sections completed - save and finish
        await save_and_complete_form_new_message(message, state)
        return
    
    current_section = sections[section_index]
    stage_display = current_section.get('stage_display', ReflectionV31System.get_stage_display(current_section['stage']))
    delta = current_section['delta']
    
    # Show section header and ask for rating
    context = data.get('reflection_context', {})
    funnel_type = context.get('funnel_type', '')
    week_start = context.get('week_start', '')
    channel = context.get('channel', '')
    
    header_text = f"📝 Форма рефлексии\n\n"
    header_text += f"Неделя: {week_start} • Канал: {channel} • Тип: {funnel_type}\n\n"
    header_text += f"Секция {section_index + 1}/{len(sections)}: {stage_display} (+{delta})\n\n"
    header_text += f"Как прошло? Оцените от 1 (очень плохо) до 5 (отлично):"
    
    await message.answer(header_text, reply_markup=ReflectionV31System.get_rating_keyboard())
    await state.set_state(ReflectionV31States.section_rating)

async def save_and_complete_form_new_message(message: types.Message, state: FSMContext):
    """Save the completed form and finish - using new message"""
    data = await state.get_data()
    form_data = data.get('current_form_data', {})
    sections = data.get('current_sections', [])
    context = data.get('reflection_context', {})
    
    # Save to database
    success = ReflectionV31System.save_reflection_data(
        context['user_id'],
        context['week_start'], 
        context['channel'],
        context['funnel_type'],
        sections,
        form_data
    )
    
    if success:
        await message.answer("✅ Форма рефлексии сохранена!")
        # Show main menu after successful save
        from main import show_main_menu
        user_id = context['user_id']
        await show_main_menu(user_id, message)
    else:
        await message.answer("❌ Ошибка при сохранении формы рефлексии")
    
    # Clear state
    await state.clear()

async def save_and_complete_form(message: types.Message, state: FSMContext):
    """Save the completed form and finish"""
    data = await state.get_data()
    form_data = data.get('current_form_data', {})
    sections = data.get('current_sections', [])
    context = data.get('reflection_context', {})
    
    # Save to database
    success = ReflectionV31System.save_reflection_data(
        context['user_id'],
        context['week_start'], 
        context['channel'],
        context['funnel_type'],
        sections,
        form_data
    )
    
    if success:
        await message.answer("✅ Форма рефлексии сохранена!")
        # Show main menu after successful save
        from main import show_main_menu
        user_id = context['user_id']
        await show_main_menu(user_id, message)
    else:
        await message.answer("❌ Ошибка при сохранении формы рефлексии")
    
    # Clear state
    await state.clear()

async def handle_reflection_v31_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle form cancellation"""
    if not callback_query.message:
        await callback_query.answer("Ошибка: сообщение недоступно")
        return
        
    if hasattr(callback_query.message, 'edit_text'):
        await callback_query.message.edit_text("Форма рефлексии отменена.")
    await state.clear()
    await callback_query.answer()