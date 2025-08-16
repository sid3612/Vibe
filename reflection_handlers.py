"""
Reflection form handlers - Complete FSM workflow for reflection forms
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
import json
from reflection_forms import (
    ReflectionStates, ReflectionQueue, 
    get_stage_type_keyboard, get_rating_keyboard, get_rejection_reasons_keyboard,
    start_next_reflection_form
)

async def process_stage_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Process stage type selection"""
    stage_mapping = {
        "stage_response": "✉️ Ответ",
        "stage_screening": "📞 Скрининг", 
        "stage_onsite": "🧑‍💼 Онсайт",
        "stage_offer": "🏁 Оффер",
        "stage_rejection_early": "❌ Отказ без интервью",
        "stage_rejection_late": "❌❌ Отказ после интервью"
    }
    
    selected_stage = stage_mapping.get(callback_query.data)
    await state.update_data(selected_stage_type=selected_stage)
    
    # Show CVR info and related hypotheses
    data = await state.get_data()
    funnel_type = data['funnel_type']
    stage = data['stage']
    
    cvr_info = ""
    if funnel_type == 'active':
        if 'Ответ' in selected_stage:
            cvr_info = "💡 CVR1 = Ответы/Подачи → связанные гипотезы: H1, H2"
        elif 'Скрининг' in selected_stage:
            cvr_info = "💡 CVR2 = Скрининги/Ответы → связанные гипотезы: H2, H3"
        elif 'Онсайт' in selected_stage:
            cvr_info = "💡 CVR3 = Онсайты/Скрининги → связанные гипотезы: H3, H4"
        elif 'Оффер' in selected_stage:
            cvr_info = "💡 CVR4 = Офферы/Онсайты → связанная гипотеза: H5"
        elif 'Отказ' in selected_stage:
            cvr_info = "💡 Отказы не влияют на CVR"
    
    await callback_query.message.edit_text(
        f"Выбран этап: {selected_stage}\n{cvr_info}\n\nОцените, как прошло (1-5):",
        reply_markup=get_rating_keyboard()
    )
    await ReflectionStates.rating.set()

async def process_rating(callback_query: types.CallbackQuery, state: FSMContext):
    """Process rating selection"""
    rating = int(callback_query.data.split('_')[1])
    await state.update_data(rating=rating)
    
    await callback_query.message.edit_text(
        f"Оценка: {rating}/5\n\n"
        "Опишите ваши сильные стороны в этом интервью (или отправьте 'пропустить'):"
    )
    await ReflectionStates.strengths.set()

async def process_strengths(message: types.Message, state: FSMContext):
    """Process strengths input"""
    strengths = message.text.strip() if message.text.lower() != 'пропустить' else None
    await state.update_data(strengths=strengths)
    
    await message.answer(
        "Опишите слабые стороны или пробелы, которые выявились (или отправьте 'пропустить'):"
    )
    await ReflectionStates.weaknesses.set()

async def process_weaknesses(message: types.Message, state: FSMContext):
    """Process weaknesses input"""
    weaknesses = message.text.strip() if message.text.lower() != 'пропустить' else None
    await state.update_data(weaknesses=weaknesses)
    
    await message.answer(
        "Оцените ваше самочувствие и мотивацию после этого этапа (1-5):",
        reply_markup=get_rating_keyboard()
    )
    await ReflectionStates.mood_motivation.set()

async def process_mood_rating(callback_query: types.CallbackQuery, state: FSMContext):
    """Process mood and motivation rating"""
    mood_rating = int(callback_query.data.split('_')[1])
    await state.update_data(mood_motivation=mood_rating)
    
    data = await state.get_data()
    selected_stage = data.get('selected_stage_type', '')
    
    # Check if this was a rejection - if so, ask for reasons
    if 'Отказ' in selected_stage:
        await callback_query.message.edit_text(
            f"Самочувствие и мотивация: {mood_rating}/5\n\n"
            "Выберите причины отказа (можно выбрать несколько):",
            reply_markup=get_rejection_reasons_keyboard()
        )
        await state.update_data(selected_rejection_reasons=[])
        await ReflectionStates.rejection_reason.set()
    else:
        # Complete the form
        await complete_reflection_form(callback_query.message, state)

async def process_rejection_reason(callback_query: types.CallbackQuery, state: FSMContext):
    """Process rejection reason selection (multi-select)"""
    if callback_query.data == "reasons_done":
        # Check if "other" was selected and needs text input
        data = await state.get_data()
        selected_reasons = data.get('selected_rejection_reasons', [])
        
        if 'other' in selected_reasons:
            await callback_query.message.edit_text(
                "Опишите другую причину отказа:"
            )
            await ReflectionStates.rejection_other.set()
        else:
            await complete_reflection_form(callback_query.message, state)
        return
    
    # Toggle reason selection
    reason_code = callback_query.data.split('_')[1]
    data = await state.get_data()
    selected_reasons = data.get('selected_rejection_reasons', [])
    
    if reason_code in selected_reasons:
        selected_reasons.remove(reason_code)
    else:
        selected_reasons.append(reason_code)
    
    await state.update_data(selected_rejection_reasons=selected_reasons)
    
    # Update keyboard to show selected state
    keyboard = get_rejection_reasons_keyboard()
    reason_names = {
        "skill": "Нет нужного навыка",
        "culture": "Нет культурного совпадения", 
        "location": "Локация/виза",
        "language": "Язык",
        "salary": "Зарплата/бюджет",
        "domain": "Нет доменного опыта",
        "timing": "Сроки/доступность",
        "other": "Другое"
    }
    
    # Recreate keyboard with selection state
    new_keyboard = types.InlineKeyboardMarkup()
    for code, name in reason_names.items():
        checkbox = "☑️" if code in selected_reasons else "☐"
        new_keyboard.add(types.InlineKeyboardButton(f"{checkbox} {name}", callback_data=f"reason_{code}"))
    
    new_keyboard.add(types.InlineKeyboardButton("✅ Готово", callback_data="reasons_done"))
    
    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)

async def process_rejection_other(message: types.Message, state: FSMContext):
    """Process other rejection reason text"""
    other_reason = message.text.strip()
    await state.update_data(rejection_other_text=other_reason)
    
    await complete_reflection_form(message, state)

async def complete_reflection_form(message: types.Message, state: FSMContext):
    """Complete and save reflection form"""
    data = await state.get_data()
    
    # Prepare form data for saving
    form_data = {
        'stage_type': data.get('selected_stage_type'),
        'rating': data.get('rating'),
        'strengths': data.get('strengths'),
        'weaknesses': data.get('weaknesses'), 
        'mood_motivation': data.get('mood_motivation'),
        'rejection_reasons': data.get('selected_rejection_reasons', []),
        'rejection_other': data.get('rejection_other_text'),
        'completed_at': str(datetime.now())
    }
    
    # Save completed form
    form_id = data['form_id']
    ReflectionQueue.complete_form(form_id, form_data)
    
    # Show completion message
    summary_text = f"""
✅ Форма рефлексии сохранена!

📊 Ваши ответы:
• Этап: {data.get('selected_stage_type')}
• Оценка: {data.get('rating')}/5
• Самочувствие: {data.get('mood_motivation')}/5
    """
    
    if data.get('strengths'):
        summary_text += f"\n• Сильные стороны: {data.get('strengths')[:50]}{'...' if len(data.get('strengths', '')) > 50 else ''}"
    
    if data.get('weaknesses'):
        summary_text += f"\n• Слабые стороны: {data.get('weaknesses')[:50]}{'...' if len(data.get('weaknesses', '')) > 50 else ''}"
    
    await message.answer(summary_text.strip())
    
    # Check if there are more forms to fill
    user_id = message.from_user.id
    pending_count = len(ReflectionQueue.get_pending_forms(user_id))
    
    if pending_count > 0:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(f"▶ Заполнить следующую ({pending_count} осталось)", 
                                     callback_data="continue_forms"),
            types.InlineKeyboardButton("⏸ Остановить", callback_data="stop_forms")
        )
        
        await message.answer(
            f"У вас осталось {pending_count} незаполненных форм.",
            reply_markup=keyboard
        )
    else:
        await message.answer("🎉 Все формы рефлексии заполнены!")
    
    await state.finish()

async def handle_continue_forms(callback_query: types.CallbackQuery, state: FSMContext):
    """Continue filling remaining forms"""
    await callback_query.message.edit_text("▶ Переходим к следующей форме...")
    await start_next_reflection_form(callback_query.message, callback_query.from_user.id, state)

async def handle_stop_forms(callback_query: types.CallbackQuery):
    """Stop filling forms for now"""
    await callback_query.message.edit_text(
        "⏸ Заполнение форм остановлено.\n"
        "Вы можете продолжить в любое время командой /pending_forms"
    )

async def handle_skip_form(callback_query: types.CallbackQuery, state: FSMContext):
    """Skip current form"""
    data = await state.get_data()
    form_id = data['form_id']
    
    ReflectionQueue.skip_form(form_id)
    
    await callback_query.message.edit_text("⏭ Форма пропущена.")
    
    # Check for next form
    user_id = callback_query.from_user.id
    pending_count = len(ReflectionQueue.get_pending_forms(user_id))
    
    if pending_count > 0:
        await start_next_reflection_form(callback_query.message, user_id, state)
    else:
        await callback_query.message.answer("✅ Больше нет форм для заполнения.")
        await state.finish()

async def handle_cancel_form(callback_query: types.CallbackQuery, state: FSMContext):
    """Cancel all remaining forms"""
    await callback_query.message.edit_text(
        "🗑 Заполнение форм отменено.\n"
        "Все незаполненные формы остались в очереди. "
        "Используйте /pending_forms чтобы вернуться к ним позже."
    )
    await state.finish()