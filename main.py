import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db, add_user, get_user_funnels, set_active_funnel, get_user_channels, add_channel, remove_channel, add_week_data, get_week_data, update_week_field, get_user_history, set_user_reminders, save_profile, get_profile, delete_profile, record_payment_click, get_payment_statistics
from metrics import calculate_cvr_metrics, format_metrics_table, format_history_table
from export import generate_csv_export
from faq import get_faq_text
from reminders import setup_reminders, send_reminder
from profile import (ProfileStates, format_profile_display)
import json
from validators import parse_salary_string, parse_list_input, validate_superpowers
from keyboards import get_level_keyboard, get_company_types_keyboard, get_skip_back_keyboard, get_back_keyboard, get_profile_actions_keyboard, get_profile_edit_fields_keyboard, get_confirm_delete_keyboard, get_final_review_keyboard, get_funnel_type_keyboard
from cvr_autoanalyzer import analyze_and_recommend_async
# Removed old reflection system imports - now using PRD v3.1
# from reflection_forms import ReflectionTrigger, ReflectionQueue
# from integration_v3 import register_reflection_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class FunnelStates(StatesGroup):
    waiting_for_channel_name = State()
    waiting_for_week_data = State()
    waiting_for_field_update = State()
    waiting_for_reminder_settings = State()
    # New step-by-step states
    choosing_channel = State()
    entering_applications = State()
    entering_responses = State()
    entering_screenings = State()
    entering_onsites = State()
    entering_offers = State()
    entering_rejections = State()
    # Edit data states
    edit_choosing_week = State()
    edit_choosing_channel = State()
    edit_choosing_field = State()
    edit_entering_value = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Добавляем пользователя в БД
    add_user(user_id, username)
    
    welcome_text = """👋HackOFFer — оффер быстрее и без догадок

Когда кажется, что "где-то течёт", но непонятно где.

HackOFFer — ваш AI-ментор по поиску работы: считает конверсию, находит узкие места и превращает их в понятные шаги.
Начни с Заполнения профиля, а после Внеси данные за неделю.

Выберите, с чего начнём:"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Заполнить профиль", callback_data="create_profile")],
        [InlineKeyboardButton(text="📊 Внести данные за неделю", callback_data="data_entry")],
        [InlineKeyboardButton(text="🎯 AI-анализ конверсии", callback_data="cvr_analysis")],
        [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="payment_click")],
        [InlineKeyboardButton(text="📚 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Обработчик команды /menu"""
    await show_main_menu(message.from_user.id, message)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
🆘 Помощь по использованию бота

Основные функции:
• Выбор типа воронки (активная/пассивная)
• Управление каналами поиска
• Ввод еженедельных данных
• Просмотр истории и метрик
• Экспорт данных в CSV
• Настройка напоминаний

Для начала работы используйте /start или /menu
"""
    await message.answer(help_text)

@dp.message(Command("faq"))
async def cmd_faq(message: types.Message):
    """Обработчик команды /faq"""
    faq_text = get_faq_text()
    await message.answer(faq_text, parse_mode="HTML")

# Profile commands
@dp.message(Command("profile_setup"))
async def cmd_profile_setup(message: types.Message, state: FSMContext):
    """Start profile setup wizard"""
    await message.answer(
        "📋 Мастер создания профиля\n\n"
        "Начнем с основных полей. Введите вашу роль (например, Python Developer):"
    )
    await state.set_state(ProfileStates.role)

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Show current profile"""
    user_id = message.from_user.id
    profile_data = get_profile(user_id)
    
    if not profile_data:
        await message.answer(
            "У вас еще нет профиля. Хотите создать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Создать профиль", callback_data="create_profile")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
            ])
        )
        return
    
    profile_text = format_profile_display(profile_data)
    await message.answer(f"```\n{profile_text}\n```", 
                        parse_mode="MarkdownV2", 
                        reply_markup=get_profile_actions_keyboard())

@dp.message(Command("profile_edit"))
async def cmd_profile_edit(message: types.Message):
    """Edit profile fields"""
    user_id = message.from_user.id
    profile_data = get_profile(user_id)
    
    if not profile_data:
        await message.answer("Сначала создайте профиль командой /profile_setup")
        return
    
    await message.answer("Выберите поле для редактирования:", 
                        reply_markup=get_profile_edit_fields_keyboard())

@dp.message(Command("profile_delete"))
async def cmd_profile_delete(message: types.Message):
    """Delete profile confirmation"""
    user_id = message.from_user.id
    profile_data = get_profile(user_id)
    
    if not profile_data:
        await message.answer("У вас нет профиля для удаления")
        return
    
    await message.answer(
        "⚠️ Вы уверены, что хотите удалить свой профиль? Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard()
    )

async def handle_cvr_analysis_button(query: CallbackQuery, user_id: int):
    """
    Обработчик кнопки "Анализ CVR" - запуск анализа по запросу пользователя
    """
    await query.answer("Анализирую ваши данные...")
    
    # Запускаем анализ CVR
    cvr_analysis = await analyze_and_recommend_async(user_id, use_api=True)
    
    if cvr_analysis.get("status") == "problems_found":
        await send_cvr_recommendations(query.message, user_id, cvr_analysis)
    elif cvr_analysis.get("status") == "no_problems":
        await query.message.edit_text(
            "🎉 **Анализ CVR завершен**\n\n"
            "Отличные новости! Ваши показатели конверсии в норме. "
            "Все CVR находятся на достаточном уровне для получения статистически значимых результатов.\n\n"
            "Продолжайте в том же духе! 💪",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
    elif cvr_analysis.get("status") == "insufficient_data":
        await query.message.edit_text(
            "📊 **Анализ CVR**\n\n"
            "Недостаточно данных для анализа конверсии. "
            "Для точного анализа CVR нужно:\n\n"
            "• Минимум 5 записей в знаменателе каждого этапа\n"
            "• Данные за последние недели\n"
            "• Заполненный профиль кандидата\n\n"
            "Добавьте больше данных и попробуйте снова.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить данные", callback_data="add_week_data")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
    else:
        # Ошибка анализа
        error_msg = cvr_analysis.get("message", "Неизвестная ошибка")
        await query.message.edit_text(
            f"❌ **Ошибка анализа CVR**\n\n{error_msg}\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )

async def send_cvr_recommendations(message, user_id: int, cvr_analysis: dict):
    """
    Отправляет пользователю рекомендации на основе анализа CVR
    Iteration 4: Автодетект проблем и ChatGPT рекомендации
    """
    problems = cvr_analysis.get("problems", [])
    chatgpt_prompt = cvr_analysis.get("chatgpt_prompt", "")
    ai_recommendations = cvr_analysis.get("ai_recommendations")
    
    # Формируем сообщение о найденных проблемах
    problems_text = "🔍 **Автоанализ CVR обнаружил проблемы:**\n\n"
    
    for i, problem in enumerate(problems, 1):
        cvr_name = problem['cvr_name']
        cvr_value = problem['cvr_value']
        denominator = problem['denominator']
        
        problems_text += f"{i}. **{cvr_name}**: {cvr_value:.1f}% (обработано: {denominator})\n"
        
        # Добавляем соответствующие гипотезы
        hypotheses = problem.get('hypotheses', [])
        if hypotheses:
            problems_text += f"   💡 Релевантные направления: "
            h_titles = [h.get('title', h.get('id', 'Unknown')) for h in hypotheses]
            problems_text += ", ".join(h_titles) + "\n"
        problems_text += "\n"
    
    # Отправляем анализ проблем
    await message.answer(problems_text, parse_mode="Markdown")
    
    # Если есть AI рекомендации, отправляем их
    if ai_recommendations:
        await message.answer(
            "🤖 **Персональные рекомендации от AI:**",
            parse_mode="Markdown"
        )
        
        # Отправляем рекомендации частями, если они слишком длинные
        max_length = 4000  # Telegram ограничение
        if len(ai_recommendations) > max_length:
            parts = [ai_recommendations[i:i+max_length] for i in range(0, len(ai_recommendations), max_length)]
            for i, part in enumerate(parts, 1):
                await message.answer(part, parse_mode="Markdown")
                if i < len(parts):
                    await asyncio.sleep(0.5)  # Небольшая пауза между частями
        else:
            await message.answer(ai_recommendations, parse_mode="Markdown")
    
    # Если нет AI рекомендаций, показываем промпт для ChatGPT
    elif chatgpt_prompt:
        await message.answer(
            "🤖 **Готов промпт для получения персональных рекомендаций:**\n\n"
            "Скопируйте этот текст и отправьте в ChatGPT для получения 10 персональных рекомендаций:",
            parse_mode="Markdown"
        )
        
        # Отправляем промпт частями, если он слишком длинный
        max_length = 4000  # Telegram ограничение
        if len(chatgpt_prompt) > max_length:
            parts = [chatgpt_prompt[i:i+max_length] for i in range(0, len(chatgpt_prompt), max_length)]
            for i, part in enumerate(parts, 1):
                await message.answer(f"```\n{part}\n```", parse_mode="Markdown")
                if i < len(parts):
                    await asyncio.sleep(0.5)  # Небольшая пауза между частями
        else:
            await message.answer(f"```\n{chatgpt_prompt}\n```", parse_mode="Markdown")
    
    # Возвращаемся в главное меню
    await show_main_menu(user_id, message)

async def show_main_menu(user_id: int, message_or_query):
    """Показать главное меню"""
    user_data = get_user_funnels(user_id)
    current_funnel = "🧑‍💻 Активный поиск" if user_data.get('active_funnel') == 'active' else "👀 Пассивный поиск"
    
    menu_text = f"""
📊 Главное меню

Текущая воронка: {current_funnel}
Каналов настроено: {len(get_user_channels(user_id))}

Выберите действие:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль кандидата", callback_data="profile_menu")],
        [InlineKeyboardButton(text="🔄 Сменить воронку", callback_data="change_funnel")],
        [InlineKeyboardButton(text="📝 Управление каналами", callback_data="manage_channels")],
        [InlineKeyboardButton(text="➕ Добавить данные за неделю", callback_data="add_week_data")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_data")],
        [InlineKeyboardButton(text="🎯 AI-анализ конверсии", callback_data="cvr_analysis")],
        [InlineKeyboardButton(text="📈 Показать историю", callback_data="show_history")],
        [InlineKeyboardButton(text="💾 Экспорт в CSV", callback_data="export_csv")],
        [InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="setup_reminders")],
        [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="payment_click")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
    ])
    
    # Check if it's a callback query that can be edited
    if hasattr(message_or_query, 'message') and hasattr(message_or_query, 'edit_text'):
        try:
            await message_or_query.edit_text(menu_text, reply_markup=keyboard)
        except:
            # If edit fails, send new message
            await message_or_query.message.answer(menu_text, reply_markup=keyboard)
    else:
        # It's a regular message, send new message
        await message_or_query.answer(menu_text, reply_markup=keyboard)

# Define callback filters to exclude reflection v3.1 form callbacks but allow basic navigation 
@dp.callback_query(~F.data.startswith("rating_") & ~F.data.startswith("reason_v31_") & ~F.data.startswith("reasons_v31_") & ~F.data.startswith("skip_strengths") & ~F.data.startswith("skip_weaknesses") & ~F.data.startswith("skip_form") & ~F.data.startswith("reject_type_") & ~F.data.startswith("reflection_v31_"))
async def process_callback(query: CallbackQuery, state: FSMContext):
    """Обработчик основных callback запросов (исключая reflection v3.1)"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "funnel_active":
        # Check if we're in profile creation state
        current_state = await state.get_state()
        if current_state == ProfileStates.funnel_type:
            await state.update_data(preferred_funnel_type="active")
            await query.answer("Выбран активный поиск")
            await start_optional_fields_flow(query.message, state)
        else:
            set_active_funnel(user_id, "active")
            await query.answer("Выбрана активная воронка")
            await show_main_menu(user_id, query.message)
        
    elif data == "funnel_passive":
        # Check if we're in profile creation state
        current_state = await state.get_state()
        if current_state == ProfileStates.funnel_type:
            await state.update_data(preferred_funnel_type="passive")
            await query.answer("Выбран пассивный поиск")
            await start_optional_fields_flow(query.message, state)
        else:
            set_active_funnel(user_id, "passive")
            await query.answer("Выбрана пассивная воронка")
            await show_main_menu(user_id, query.message)
        
    elif data == "main_menu":
        await show_main_menu(user_id, query.message)
    
    elif data == "cvr_analysis":
        await handle_cvr_analysis_button(query, user_id)
        
    elif data == "payment_click":
        # Записываем клик в статистику
        record_payment_click(user_id)
        
        # Получаем статистику для отображения
        stats = get_payment_statistics()
        
        # Показываем сообщение о бета-версии
        await query.message.edit_text(
            "🎉 **Временная бесплатная бета-версия**\n\n"
            "HackOFFer пока работает в режиме бесплатного тестирования! "
            "Все функции доступны без ограничений.\n\n"
            "🚀 Мы собираем обратную связь от пользователей для улучшения продукта.\n\n"
            "💡 Если у вас есть предложения или вопросы — пишите через /feedback\n\n"
            f"📊 Интерес к продукту: {stats['unique_users']} пользователей",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 На главную", callback_data="start_page")]
            ])
        )
        await query.answer("Спасибо за интерес к продукту!")
        
    elif data == "change_funnel":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧑‍💻 Активный поиск (я подаюсь)", callback_data="funnel_active")],
            [InlineKeyboardButton(text="👀 Пассивный поиск (мне пишут)", callback_data="funnel_passive")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])
        await query.message.edit_text("Выберите тип воронки:", reply_markup=keyboard)
        
    elif data == "manage_channels":
        await show_channels_menu(user_id, query.message)
        
    elif data == "add_channel":
        await query.message.edit_text("Введите название канала (например, LinkedIn, HH.ru, Referrals):")
        await state.set_state(FunnelStates.waiting_for_channel_name)
        await state.update_data(callback_query_message_id=query.message.message_id)
        
    elif data.startswith("remove_channel_"):
        channel_name = data.replace("remove_channel_", "")
        remove_channel(user_id, channel_name)
        await query.answer(f"Канал '{channel_name}' удален")
        await show_channels_menu(user_id, query.message)
        
    elif data == "add_week_data":
        channels = get_user_channels(user_id)
        if not channels:
            await query.answer("Сначала добавьте хотя бы один канал")
            await show_channels_menu(user_id, query.message)
        else:
            await show_step_by_step_input(user_id, query.message, state)
            
    elif data == "edit_data":
        await show_step_by_step_edit(user_id, query.message, state)
        
    elif data == "show_history":
        await show_history_menu(user_id, query.message)
        
    elif data == "data_history":
        await show_user_history(user_id, query.message)
        
    elif data == "reflection_history":
        await show_reflection_history(user_id, query.message)
        
    elif data == "export_csv":
        csv_data = generate_csv_export(user_id)
        if csv_data:
            file = types.BufferedInputFile(csv_data.encode('utf-8'), filename=f"funnel_data_{user_id}.csv")
            await query.message.answer_document(file, caption="📊 Экспорт данных воронки")
        else:
            await query.answer("Нет данных для экспорта")
            
    elif data == "setup_reminders":
        await show_reminder_buttons(user_id, query.message)
        
    elif data.startswith("reminder_"):
        frequency = data.replace("reminder_", "")
        set_user_reminders(user_id, frequency)
        
        if frequency == 'off':
            text = "⏰ Напоминания отключены"
        elif frequency == 'daily':
            text = "⏰ Напоминания настроены: ежедневно в 18:00"
        else:
            text = "⏰ Напоминания настроены: еженедельно по понедельникам в 10:00"
            
        await query.answer(text)
        await show_main_menu(user_id, query.message)
    
    # Profile menu handlers
    elif data == "profile_menu":
        profile_data = get_profile(user_id)
        if not profile_data:
            await query.message.edit_text(
                "У вас еще нет профиля. Хотите создать?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Создать профиль", callback_data="create_profile")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
                ])
            )
        else:
            profile_text = format_profile_display(profile_data)
            await query.message.edit_text(f"```\n{profile_text}\n```", 
                                        parse_mode="MarkdownV2", 
                                        reply_markup=get_profile_actions_keyboard())
    
    elif data == "create_profile":
        await query.message.edit_text(
            "📋 Мастер создания профиля\n\n"
            "Роль — на какую позицию вы ищете работу:\n"
            "Пример: Product Manager, Data Analyst"
        )
        await state.set_state(ProfileStates.role)
    
    elif data == "profile_delete":
        await query.message.edit_text(
            "⚠️ Вы уверены, что хотите удалить свой профиль? Это действие нельзя отменить.",
            reply_markup=get_confirm_delete_keyboard()
        )
    
    elif data == "confirm_delete":
        deleted = delete_profile(user_id)
        if deleted:
            await query.answer("Профиль удален")
            await show_main_menu(user_id, query.message)
        else:
            await query.answer("Ошибка при удалении профиля")
    
    elif data == "profile_view":
        profile_data = get_profile(user_id)
        if profile_data:
            profile_text = format_profile_display(profile_data)
            await query.message.edit_text(f"```\n{profile_text}\n```", 
                                        parse_mode="MarkdownV2", 
                                        reply_markup=get_profile_actions_keyboard())
        else:
            await query.answer("Профиль не найден")
    
    # Profile level selection handlers
    elif data.startswith("level_"):
        current_state = await state.get_state()
        if current_state == ProfileStates.level.state:
            level_value = data.replace("level_", "")
            if level_value == "custom":
                await query.message.edit_text("Введите ваш уровень:")
                await state.set_state(ProfileStates.level_custom)
            else:
                level_map = {
                    "junior": "Junior",
                    "middle": "Middle", 
                    "senior": "Senior",
                    "lead": "Lead"
                }
                await state.update_data(level=level_map[level_value])
                await query.message.edit_text("Срок — сколько недель планируете уделить активному поиску (1-52):\nПример: 12")
                await state.set_state(ProfileStates.deadline_weeks)
        await query.answer()
    
    # Skip handlers for optional fields
    elif data == "skip_step":
        current_state = await state.get_state()
        
        if current_state == ProfileStates.role_synonyms:
            await start_salary_flow(query.message, state)
        elif current_state == ProfileStates.salary_min:
            await start_company_types_flow(query.message, state)
        elif current_state == ProfileStates.company_types:
            await start_industries_flow(query.message, state)
        elif current_state == ProfileStates.industries:
            await start_competencies_flow(query.message, state)
        elif current_state == ProfileStates.competencies:
            await start_superpowers_flow(query.message, state)
        elif current_state == ProfileStates.superpowers:
            await start_constraints_flow(query.message, state)
        elif current_state == ProfileStates.constraints:
            await start_linkedin_flow(query.message, state)
        elif current_state == ProfileStates.linkedin:
            await finish_profile_creation(query.message, state)
        
        await query.answer("Пропущено")
    
    # Back handlers for optional fields
    elif data == "back_step":
        current_state = await state.get_state()
        
        if current_state == ProfileStates.role_synonyms:
            # Go back to funnel type selection
            await query.message.edit_text(
                "📊 Выберите ваш основной тип поиска работы:\n\n"
                "🧑‍💻 <b>Активный поиск</b> - вы подаёте заявки на вакансии\n"
                "👀 <b>Пассивный поиск</b> - работодатели находят вас через профиль\n\n"
                "Этот выбор определит, какую воронку вы будете использовать по умолчанию.",
                reply_markup=get_funnel_type_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(ProfileStates.funnel_type)
        elif current_state == ProfileStates.salary_min:
            await start_optional_fields_flow(query.message, state)
        elif current_state == ProfileStates.company_types:
            await start_salary_flow(query.message, state)
        elif current_state == ProfileStates.industries:
            await start_company_types_flow(query.message, state)
        elif current_state == ProfileStates.competencies:
            await start_industries_flow(query.message, state)
        elif current_state == ProfileStates.superpowers:
            await start_competencies_flow(query.message, state)
        elif current_state == ProfileStates.constraints:
            await start_superpowers_flow(query.message, state)
        elif current_state == ProfileStates.linkedin:
            await start_constraints_flow(query.message, state)
        
        await query.answer("Назад")
        
    elif data.startswith("select_channel_"):
        channel = data.replace("select_channel_", "")
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        # Получаем текущую неделю для отображения
        from datetime import datetime, timedelta
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime('%Y-%m-%d')
        week_end = (monday + timedelta(days=6)).strftime('%Y-%m-%d')
        
        await state.update_data(selected_channel=channel, funnel_type=funnel_type)
        
        if funnel_type == 'active':
            field_name = "количество подач резюме (Applications)"
        else:
            field_name = "количество просмотров профиля (Views)"
        
        text = f"📊 Канал: {channel}\n📅 Неделя: {week_start} - {week_end}\n\nВведите {field_name}:"
        await query.message.edit_text(text)
        await state.set_state(FunnelStates.entering_applications)
        
    elif data.startswith("edit_week_"):
        week = data.replace("edit_week_", "")
        await state.update_data(selected_week=week)
        
        # Получаем каналы для этой недели
        history = get_user_history(user_id)
        week_channels = list(set([row['channel_name'] for row in history if row['week_start'] == week]))
        
        text = f"✏️ Неделя: {week}\n\nВыберите канал:"
        
        keyboard_buttons = []
        for channel in week_channels:
            keyboard_buttons.append([InlineKeyboardButton(text=channel, callback_data=f"edit_channel_{channel}")])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_data")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await query.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(FunnelStates.edit_choosing_channel)
        
    elif data.startswith("edit_channel_"):
        channel = data.replace("edit_channel_", "")
        await state.update_data(selected_edit_channel=channel)
        
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        if funnel_type == 'active':
            fields = [
                ('applications', 'Подачи'),
                ('responses', 'Ответы'),
                ('screenings', 'Скрининги'),
                ('onsites', 'Онсайты'),
                ('offers', 'Офферы'),
                ('rejections', 'Отказ')
            ]
        else:
            fields = [
                ('views', 'Просмотры'),
                ('incoming', 'Входящие'),
                ('screenings', 'Скрининги'),
                ('onsites', 'Онсайты'),
                ('offers', 'Офферы'),
                ('rejections', 'Отказ')
            ]
        
        text = f"✏️ Канал: {channel}\n\nВыберите поле для редактирования:"
        
        keyboard_buttons = []
        for field_key, field_name in fields:
            keyboard_buttons.append([InlineKeyboardButton(text=field_name, callback_data=f"edit_field_{field_key}")])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_data")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await query.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(FunnelStates.edit_choosing_field)
        
    elif data.startswith("edit_field_"):
        field = data.replace("edit_field_", "")
        await state.update_data(selected_field=field)
        
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        field_names = {
            'applications': 'подачи', 'responses': 'ответы', 'screenings': 'скрининги',
            'onsites': 'онсайты', 'offers': 'офферы', 'rejections': 'реджекты',
            'views': 'просмотры', 'incoming': 'входящие'
        }
        
        field_name = field_names.get(field, field)
        text = f"✏️ Введите новое значение для {field_name}:"
        
        await query.message.edit_text(text)
        await state.set_state(FunnelStates.edit_entering_value)
        
    elif data == "start_page":
        # Возврат на стартовую страницу
        welcome_text = """👋HackOFFer — оффер быстрее и без догадок

Когда кажется, что "где-то течёт", но непонятно где.

HackOFFer — ваш AI-ментор по поиску работы: считает конверсию, находит узкие места и превращает их в понятные шаги.
Начни с Заполнения профиля, а после Внеси данные за неделю.

Выберите, с чего начнём:"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Заполнить профиль", callback_data="create_profile")],
            [InlineKeyboardButton(text="📊 Внести данные за неделю", callback_data="data_entry")],
            [InlineKeyboardButton(text="🎯 AI-анализ конверсии", callback_data="cvr_analysis")],
            [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="payment_click")],
            [InlineKeyboardButton(text="📚 Главное меню", callback_data="main_menu")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
        ])
        
        await query.message.edit_text(welcome_text, reply_markup=keyboard)
        
    elif data == "show_faq":
        faq_text = get_faq_text()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
        ])
        await query.message.edit_text(faq_text, reply_markup=keyboard, parse_mode="HTML")
        
    elif data == "data_entry":
        # Переход к вводу данных - проверяем наличие профиля
        profile_data = get_profile(user_id)
        if not profile_data:
            await query.message.edit_text(
                "⚠️ Для ввода данных сначала нужно создать профиль.\n\nПрофиль определяет тип воронки (активный/пассивный поиск) для правильного сбора метрик.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать профиль", callback_data="create_profile")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
                ])
            )
        else:
            # Показываем выбор каналов для ввода данных
            channels = get_user_channels(user_id)
            if not channels:
                await query.message.edit_text(
                    "⚠️ У вас нет настроенных каналов для ввода данных.\n\n"
                    "Сначала добавьте хотя бы один канал через 'Управление каналами'.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📝 Управление каналами", callback_data="manage_channels")],
                        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
                    ])
                )
                return
            
            text = "📊 Выберите канал для ввода данных:"
            keyboard_buttons = []
            for channel in channels:
                keyboard_buttons.append([InlineKeyboardButton(text=channel, callback_data=f"select_channel_{channel}")])
            
            keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await query.message.edit_text(text, reply_markup=keyboard)
            await state.set_state(FunnelStates.choosing_channel)

async def show_channels_menu(user_id: int, message):
    """Показать меню управления каналами"""
    channels = get_user_channels(user_id)
    
    text = "📝 Управление каналами\n\n"
    if channels:
        text += "Ваши каналы:\n"
        for channel in channels:
            text += f"• {channel}\n"
    else:
        text += "У вас пока нет добавленных каналов."
    
    keyboard_buttons = []
    keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")])
    
    if channels:
        for channel in channels:
            keyboard_buttons.append([InlineKeyboardButton(text=f"❌ {channel}", callback_data=f"remove_channel_{channel}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.edit_text(text, reply_markup=keyboard)

async def show_reflection_history(user_id: int, message):
    """Показать историю рефлексий пользователя"""
    from db import get_reflection_history
    import json
    
    history_data = get_reflection_history(user_id, 10)
    
    if not history_data:
        text = "💭 История рефлексий\n\nИстория рефлексий пуста. Добавьте данные и заполните форму рефлексии для создания истории."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к истории", callback_data="show_history")]
        ])
        await message.edit_text(text, reply_markup=keyboard)
        return
    
    text = "💭 История рефлексий (последние 10)\n\n"
    
    for i, reflection in enumerate(history_data, 1):
        # Парсим дату
        created_at = reflection['created_at']
        if 'T' in created_at:
            date_part = created_at.split('T')[0]
        else:
            date_part = created_at.split(' ')[0]
        
        # Формируем заголовок
        stage_name = {
            'responses': 'Ответы',
            'screenings': 'Скрининги', 
            'onsites': 'Онсайты',
            'offers': 'Офферы',
            'rejections': 'Реджекты'
        }.get(reflection['section_stage'], reflection['section_stage'])
        
        text += f"{i}. {stage_name} • {reflection['channel']} • {date_part}\n"
        text += f"   События: {reflection['events_count']}\n"
        
        if reflection['rating_overall']:
            text += f"   Оценка: {reflection['rating_overall']}/10\n"
        
        if reflection['strengths']:
            text += f"   💪 {reflection['strengths'][:50]}{'...' if len(reflection['strengths']) > 50 else ''}\n"
        
        if reflection['weaknesses']:
            text += f"   📝 {reflection['weaknesses'][:50]}{'...' if len(reflection['weaknesses']) > 50 else ''}\n"
        
        if reflection['reject_reasons_json']:
            try:
                reasons = json.loads(reflection['reject_reasons_json'])
                if reasons:
                    text += f"   ❌ Причины: {', '.join(reasons[:2])}{'...' if len(reasons) > 2 else ''}\n"
            except:
                pass
        
        text += "\n"
    
    if len(text) > 4000:
        text = text[:3950] + "\n... (показаны не все записи)"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к истории", callback_data="show_history")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard)

async def show_week_data_input(user_id: int, message, state: FSMContext):
    """Показать форму ввода данных за неделю"""
    user_data = get_user_funnels(user_id)
    funnel_type = user_data.get('active_funnel', 'active')
    channels = get_user_channels(user_id)
    
    if funnel_type == 'active':
        fields = ['applications', 'responses', 'screenings', 'onsites', 'offers', 'rejections']
        field_names = ['Подачи', 'Ответы', 'Скрининги', 'Онсайты', 'Офферы', 'Реджекты']
    else:
        fields = ['views', 'incoming', 'screenings', 'onsites', 'offers', 'rejections']
        field_names = ['Просмотры', 'Входящие', 'Скрининги', 'Онсайты', 'Офферы', 'Реджекты']
    
    text = f"""
📊 Ввод данных за неделю ({funnel_type.upper()})

Введите данные в формате:
Канал: {field_names[0]} {field_names[1]} {field_names[2]} {field_names[3]} {field_names[4]} {field_names[5]}

Пример:
LinkedIn: 10 3 2 1 1 0
HH.ru: 15 5 3 2 0 2

Ваши каналы: {', '.join(channels)}
"""
    
    await message.edit_text(text)
    await state.set_state(FunnelStates.waiting_for_week_data)

async def show_history_menu(user_id: int, message):
    """Показать меню истории"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 История данных", callback_data="data_history")],
        [InlineKeyboardButton(text="💭 История рефлексий", callback_data="reflection_history")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
    ])
    
    text = "📈 Выберите тип истории:"
    await message.edit_text(text, reply_markup=keyboard)

async def show_user_history(user_id: int, message):
    """Показать историю данных пользователя"""
    history_data = get_user_history(user_id)
    user_data = get_user_funnels(user_id)
    funnel_type = user_data.get('active_funnel', 'active')
    
    if not history_data:
        text = "📊 История данных\n\nДанных пока нет. Добавьте данные за неделю для просмотра истории."
    else:
        text = format_history_table(history_data, funnel_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к истории", callback_data="show_history")]
    ])
    
    await message.edit_text(f"```\n{text}\n```", reply_markup=keyboard, parse_mode="MarkdownV2")

async def show_reminder_settings(user_id: int, message, state: FSMContext):
    """Показать настройки напоминаний"""
    text = """
⏰ Настройка напоминаний

Выберите частоту напоминаний:
• daily - ежедневно в 18:00
• weekly - еженедельно по понедельникам в 10:00
• off - отключить напоминания

Введите частоту:
"""
    await message.edit_text(text)
    await state.set_state(FunnelStates.waiting_for_reminder_settings)

async def show_step_by_step_input(user_id: int, message, state: FSMContext):
    """Показать пошаговый ввод данных"""
    channels = get_user_channels(user_id)
    
    text = "📊 Добавление данных за неделю\n\nВыберите канал:"
    
    keyboard_buttons = []
    for channel in channels:
        keyboard_buttons.append([InlineKeyboardButton(text=channel, callback_data=f"select_channel_{channel}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.edit_text(text, reply_markup=keyboard)
    await state.set_state(FunnelStates.choosing_channel)

async def show_step_by_step_edit(user_id: int, message, state: FSMContext):
    """Показать пошаговое редактирование данных"""
    history = get_user_history(user_id)
    if not history:
        await message.edit_text("📝 Нет данных для редактирования\n\nСначала добавьте данные за неделю", 
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                   [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
                               ]))
        return
    
    # Получаем уникальные недели
    weeks = list(set([row['week_start'] for row in history]))
    weeks.sort(reverse=True)
    
    text = "✏️ Редактирование данных\n\nВыберите неделю:"
    
    keyboard_buttons = []
    for week in weeks[:10]:  # Показываем последние 10 недель
        keyboard_buttons.append([InlineKeyboardButton(text=f"📅 {week}", callback_data=f"edit_week_{week}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.edit_text(text, reply_markup=keyboard)
    await state.set_state(FunnelStates.edit_choosing_week)

async def show_reminder_buttons(user_id: int, message):
    """Показать кнопки настройки напоминаний"""
    text = """
⏰ Настройка напоминаний

Выберите частоту напоминаний:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневно в 18:00", callback_data="reminder_daily")],
        [InlineKeyboardButton(text="📆 Еженедельно (понедельник 10:00)", callback_data="reminder_weekly")],
        [InlineKeyboardButton(text="🔕 Отключить", callback_data="reminder_off")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard)

@dp.message(FunnelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    """Обработка названия канала"""
    channel_name = message.text.strip()
    user_id = message.from_user.id
    
    if len(channel_name) > 50:
        await message.answer("Название канала слишком длинное (максимум 50 символов)")
        return
    
    if add_channel(user_id, channel_name):
        await message.answer(f"✅ Канал '{channel_name}' добавлен!")
        await state.clear()
        # Показываем меню каналов новым сообщением
        channels = get_user_channels(user_id)
        text = "📝 Управление каналами\n\n"
        if channels:
            text += "Ваши каналы:\n"
            for channel in channels:
                text += f"• {channel}\n"
        else:
            text += "У вас пока нет добавленных каналов."
        
        keyboard_buttons = []
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")])
        
        if channels:
            for channel in channels:
                keyboard_buttons.append([InlineKeyboardButton(text=f"❌ {channel}", callback_data=f"remove_channel_{channel}")])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("❌ Канал с таким названием уже существует")

@dp.message(FunnelStates.waiting_for_week_data)
async def process_week_data(message: types.Message, state: FSMContext):
    """Обработка данных за неделю"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        lines = text.split('\n')
        current_week = datetime.now().strftime('%Y-%m-%d')
        
        # Найти понедельник текущей недели
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime('%Y-%m-%d')
        
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        success_count = 0
        for line in lines:
            if ':' not in line:
                continue
                
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
                
            channel = parts[0].strip()
            values_str = parts[1].strip()
            values = [int(x) for x in values_str.split()]
            
            if funnel_type == 'active':
                if len(values) == 6:
                    data = {
                        'applications': values[0],
                        'responses': values[1],
                        'screenings': values[2],
                        'onsites': values[3],
                        'offers': values[4],
                        'rejections': values[5]
                    }
                    # Get old data before adding new
                    old_data_dict = {}
                    existing_data = get_week_data(user_id, week_start, channel, funnel_type)
                    if existing_data:
                        old_data_dict = dict(existing_data)
                    
                    add_week_data(user_id, week_start, channel, funnel_type, data, check_triggers=False)
                    success_count += 1
                    
                    # Calculate new data after addition for trigger checking
                    new_data_dict = old_data_dict.copy()
                    for key, value in data.items():
                        new_data_dict[key] = new_data_dict.get(key, 0) + value
                    
                    # Check for reflection triggers
                    triggers = ReflectionTrigger.check_triggers(user_id, week_start, channel, funnel_type, old_data_dict, new_data_dict)
                    if triggers:
                        await ReflectionTrigger.offer_reflection_form(message, user_id, week_start, channel, funnel_type, triggers)
            else:  # passive
                if len(values) == 6:
                    data = {
                        'views': values[0],
                        'incoming': values[1],
                        'screenings': values[2],
                        'onsites': values[3],
                        'offers': values[4],
                        'rejections': values[5]
                    }
                    # Get old data before adding new
                    old_data_dict = {}
                    existing_data = get_week_data(user_id, week_start, channel, funnel_type)
                    if existing_data:
                        old_data_dict = dict(existing_data)
                    
                    add_week_data(user_id, week_start, channel, funnel_type, data, check_triggers=False)
                    success_count += 1
                    
                    # Calculate new data after addition for trigger checking
                    new_data_dict = old_data_dict.copy()
                    for key, value in data.items():
                        new_data_dict[key] = new_data_dict.get(key, 0) + value
                    
                    # Check for reflection triggers (excluding views for passive)
                    triggers = ReflectionTrigger.check_triggers(user_id, week_start, channel, funnel_type, old_data_dict, new_data_dict)
                    if triggers:
                        await ReflectionTrigger.offer_reflection_form(message, user_id, week_start, channel, funnel_type, triggers)
        
        if success_count > 0:
            await message.answer(f"✅ Добавлено {success_count} записей за неделю {week_start}")
            await state.clear()
            # Показываем главное меню новым сообщением
            user_data = get_user_funnels(user_id)
            current_funnel = "🧑‍💻 Активный поиск" if user_data.get('active_funnel') == 'active' else "👀 Пассивный поиск"
            
            menu_text = f"""
📊 Главное меню

Текущая воронка: {current_funnel}
Каналов настроено: {len(get_user_channels(user_id))}

Выберите действие:
"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Сменить воронку", callback_data="change_funnel")],
                [InlineKeyboardButton(text="📝 Управление каналами", callback_data="manage_channels")],
                [InlineKeyboardButton(text="➕ Добавить данные за неделю", callback_data="add_week_data")],
                [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_data")],
                [InlineKeyboardButton(text="📈 Показать историю", callback_data="show_history")],
                [InlineKeyboardButton(text="💾 Экспорт в CSV", callback_data="export_csv")],
                [InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="setup_reminders")],
                [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
            ])
            
            await message.answer(menu_text, reply_markup=keyboard)
        else:
            await message.answer("❌ Не удалось обработать данные. Проверьте формат ввода.")
            
    except ValueError:
        await message.answer("❌ Ошибка в формате данных. Используйте только числа для значений.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

# Step-by-step input handlers
@dp.message(FunnelStates.entering_applications)
async def process_applications(message: types.Message, state: FSMContext):
    """Обработка ввода первого поля"""
    try:
        value = int(message.text.strip())
        data = await state.get_data()
        funnel_type = data.get('funnel_type', 'active')
        
        if funnel_type == 'active':
            await state.update_data(applications=value)
            field_name = "количество ответов от компаний (Responses)"
        else:
            await state.update_data(views=value)
            field_name = "количество обращений от компаний (Incoming)"
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите {field_name}:")
        await state.set_state(FunnelStates.entering_responses)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_responses)
async def process_responses(message: types.Message, state: FSMContext):
    """Обработка ввода второго поля"""
    try:
        value = int(message.text.strip())
        data = await state.get_data()
        funnel_type = data.get('funnel_type', 'active')
        
        if funnel_type == 'active':
            await state.update_data(responses=value)
        else:
            await state.update_data(incoming=value)
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество первичных звонков/скринингов (Screenings):")
        await state.set_state(FunnelStates.entering_screenings)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_screenings)
async def process_screenings(message: types.Message, state: FSMContext):
    """Обработка ввода скринингов"""
    try:
        value = int(message.text.strip())
        await state.update_data(screenings=value)
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество основных интервью (Onsites)\n(Если у одной компании несколько интервью — считайте это за 1):")
        await state.set_state(FunnelStates.entering_onsites)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_onsites)
async def process_onsites(message: types.Message, state: FSMContext):
    """Обработка ввода онсайтов"""
    try:
        value = int(message.text.strip())
        await state.update_data(onsites=value)
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество полученных офферов (Offers):")
        await state.set_state(FunnelStates.entering_offers)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_offers)
async def process_offers(message: types.Message, state: FSMContext):
    """Обработка ввода офферов"""
    try:
        value = int(message.text.strip())
        await state.update_data(offers=value)
            
        await message.answer(f"✅ Сохранено\n\nНаконец, введите количество отказов (Rejections):")
        await state.set_state(FunnelStates.entering_rejections)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_rejections)
async def process_rejections(message: types.Message, state: FSMContext):
    """Обработка завершающего ввода"""
    try:
        value = int(message.text.strip())
        user_id = message.from_user.id
        data = await state.get_data()
        
        # Получаем текущую неделю
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime('%Y-%m-%d')
        
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        # Формируем финальные данные
        if funnel_type == 'active':
            week_data = {
                'applications': data.get('applications', 0),
                'responses': data.get('responses', 0),
                'screenings': data.get('screenings', 0),
                'onsites': data.get('onsites', 0),
                'offers': data.get('offers', 0),
                'rejections': value
            }
        else:
            week_data = {
                'views': data.get('views', 0),
                'incoming': data.get('incoming', 0),
                'screenings': data.get('screenings', 0),
                'onsites': data.get('onsites', 0),
                'offers': data.get('offers', 0),
                'rejections': value
            }
        
        # Сохраняем данные и проверяем триггеры рефлексии после завершения всего мастера
        channel = data.get('selected_channel')
        
        # Get old data before adding new for reflection trigger calculation
        old_data_dict = {}
        existing_data = get_week_data(user_id, week_start, channel, funnel_type)
        if existing_data:
            old_data_dict = dict(existing_data)
        
        # Save the data
        add_week_data(user_id, week_start, channel, funnel_type, week_data, check_triggers=False)
        
        # Calculate new totals after data addition
        new_data_record = get_week_data(user_id, week_start, channel, funnel_type)
        new_data_dict = dict(new_data_record) if new_data_record else {}
        
        await message.answer(f"✅ Данные успешно сохранены для канала {channel} за неделю {week_start}!")
        
        # Check for reflection triggers using PRD v3.1 system
        from reflection_v31 import ReflectionV31System
        
        sections = ReflectionV31System.check_reflection_trigger(user_id, week_start, channel, funnel_type, old_data_dict, new_data_dict)
        
        if sections:
            # Store state data for reflection form before offering
            await state.update_data(
                reflection_sections=sections,
                reflection_context={
                    'user_id': user_id,
                    'week_start': week_start,
                    'channel': channel,
                    'funnel_type': funnel_type
                }
            )
            # Offer reflection form using PRD v3.1 system
            await ReflectionV31System.offer_reflection_form(message, user_id, week_start, channel, funnel_type, sections)
            # НЕ очищаем state здесь - это будет сделано в обработчиках кнопок
        else:
            # Clear state and show main menu after data addition
            await state.clear()
            await show_main_menu(user_id, message)
        
    except ValueError:
        # Only respond with error if still in the rejections state
        await message.answer("❌ Введите число от 0 до 999 для отклонений")

@dp.message(FunnelStates.edit_entering_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    """Обработка редактирования значения"""
    try:
        value = int(message.text.strip())
        user_id = message.from_user.id
        data = await state.get_data()
        
        week = data.get('selected_week')
        channel = data.get('selected_edit_channel')
        field = data.get('selected_field')
        
        if update_week_field(user_id, week, channel, field, value):
            await message.answer(f"✅ Обновлено: {week} {channel} {field} = {value}")
        else:
            await message.answer("❌ Не удалось обновить данные")
            
        await state.clear()
        await show_main_menu(user_id, message)
        
    except ValueError:
        await message.answer("❌ Введите число для редактирования")

async def show_main_menu_new_message(user_id: int, message):
    """Deprecated - use show_main_menu instead"""
    await show_main_menu(user_id, message)
    current_funnel = "🧑‍💻 Активный поиск" if user_data.get('active_funnel') == 'active' else "👀 Пассивный поиск"
    
    menu_text = f"""
📊 Главное меню

Текущая воронка: {current_funnel}
Каналов настроено: {len(get_user_channels(user_id))}

Выберите действие:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить воронку", callback_data="change_funnel")],
        [InlineKeyboardButton(text="📝 Управление каналами", callback_data="manage_channels")],
        [InlineKeyboardButton(text="➕ Добавить данные за неделю", callback_data="add_week_data")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_data")],
        [InlineKeyboardButton(text="📈 Показать историю", callback_data="show_history")],
        [InlineKeyboardButton(text="💾 Экспорт в CSV", callback_data="export_csv")],
        [InlineKeyboardButton(text="👤 Профиль кандидата", callback_data="profile_menu")],
        [InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="setup_reminders")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
    ])
    
    await message.answer(menu_text, reply_markup=keyboard)

@dp.message(StateFilter(None))
async def handle_edit_command(message: types.Message):
    """Обработка команд редактирования данных без состояния"""
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем, является ли это командой редактирования (формат: YYYY-MM-DD channel field value)
    parts = text.split()
    if len(parts) == 4:
        try:
            week_str, channel, field, value = parts
            week_date = datetime.strptime(week_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            value = int(value)
            
            user_data = get_user_funnels(user_id)
            funnel_type = user_data.get('active_funnel', 'active')
            
            # Проверяем корректность поля
            if funnel_type == 'active':
                valid_fields = ['applications', 'responses', 'screenings', 'onsites', 'offers', 'rejections']
            else:
                valid_fields = ['views', 'incoming', 'screenings', 'onsites', 'offers', 'rejections']
            
            if field in valid_fields:
                if update_week_field(user_id, week_date, channel, field, value):
                    await message.answer(f"✅ Обновлено: {week_str} {channel} {field} = {value}")
                else:
                    await message.answer("❌ Не удалось обновить данные. Проверьте правильность недели и канала.")
            else:
                await message.answer(f"❌ Неверное поле. Доступные поля: {', '.join(valid_fields)}")
        except ValueError:
            await message.answer("❌ Неверный формат даты или значения")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")
    else:
        # Для всех других сообщений без состояния - показать главное меню
        await show_main_menu(user_id, message)

# Profile FSM state handlers
@dp.message(ProfileStates.role, F.text)
async def process_profile_role(message: types.Message, state: FSMContext):
    """Process role input"""
    role = message.text.strip()
    if not role or len(role) < 1:
        await message.answer("Роль не может быть пустой. Попробуйте еще раз:")
        return
    
    await state.update_data(role=role)
    await message.answer(
        "Текущая локация — где вы живёте сейчас:\n"
        "Пример: Лиссабон, Португалия"
    )
    await state.set_state(ProfileStates.current_location)

@dp.message(ProfileStates.current_location, F.text)
async def process_profile_current_location(message: types.Message, state: FSMContext):
    """Process current location"""
    location = message.text.strip()
    if not location:
        await message.answer("Локация не может быть пустой. Попробуйте еще раз:")
        return
    
    await state.update_data(current_location=location)
    await message.answer(
        "Локация поиска — где хотите найти работу (страна/remote):\n"
        "Пример: Германия, remote-EU"
    )
    await state.set_state(ProfileStates.target_location)

@dp.message(ProfileStates.target_location, F.text)
async def process_profile_target_location(message: types.Message, state: FSMContext):
    """Process target location"""
    location = message.text.strip()
    if not location:
        await message.answer("Локация не может быть пустой. Попробуйте еще раз:")
        return
    
    await state.update_data(target_location=location)
    await message.answer("Уровень — ваш профессиональный уровень:", reply_markup=get_level_keyboard())
    await state.set_state(ProfileStates.level)

@dp.message(ProfileStates.level_custom, F.text)
async def process_profile_level_custom(message: types.Message, state: FSMContext):
    """Process custom level input"""
    level = message.text.strip()
    if not level:
        await message.answer("Уровень не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(level=level)
    await message.answer("Срок — сколько недель планируете уделить активному поиску (1-52):\nПример: 12")
    await state.set_state(ProfileStates.deadline_weeks)

@dp.message(ProfileStates.deadline_weeks, F.text)
async def process_profile_deadline(message: types.Message, state: FSMContext):
    """Process deadline weeks"""
    try:
        weeks = int(message.text.strip())
        if weeks < 1 or weeks > 52:
            await message.answer("Срок должен быть от 1 до 52 недель. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("Введите число недель (1-52):")
        return
    
    from validators import calculate_target_end_date
    target_end_date = calculate_target_end_date(weeks)
    await state.update_data(deadline_weeks=weeks, target_end_date=target_end_date)
    
    # Ask for funnel type preference
    await message.answer(
        "📊 Выберите ваш основной тип поиска работы:\n\n"
        "🧑‍💻 <b>Активный поиск</b> - вы подаёте заявки на вакансии\n"
        "👀 <b>Пассивный поиск</b> - работодатели находят вас через профиль\n\n"
        "Этот выбор определит, какую воронку вы будете использовать по умолчанию.",
        reply_markup=get_funnel_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProfileStates.funnel_type)

# Optional fields flow functions  
async def start_optional_fields_flow(message, state: FSMContext):
    """Start the optional fields collection"""
    await message.answer(
        "Синонимы ролей — похожие названия, под которыми встречается ваша роль (до 4, через запятую):\n"
        "Пример: Product Manager, Product Owner, Growth PM, Platform PM",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.role_synonyms)

async def start_salary_flow(message, state: FSMContext):
    """Start salary expectations collection"""
    await message.answer(
        "Диапазон ЗП — зарплатные ожидания (число или диапазон + валюта + период):\n"
        "Примеры: 60000 EUR/год, 60000-70000 EUR/год, 5000-8000 USD/месяц",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.salary_min)

async def start_company_types_flow(message, state: FSMContext):
    """Start company types collection"""
    await message.answer(
        "Типы компаний — где вы хотите работать (можно выбрать несколько, через запятую):\n"
        "Варианты: SMB, Scale-up, Enterprise, Consulting\n"
        "Пример: SMB, Scale-up",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.company_types)

async def start_industries_flow(message, state: FSMContext):
    """Start industries collection"""
    await message.answer(
        "Индустрии — до 3 сфер, которые вам интересны (через запятую):\n"
        "Пример: Fintech, SaaS, AI",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.industries)

async def start_competencies_flow(message, state: FSMContext):
    """Start competencies collection"""
    await message.answer(
        "Ключевые компетенции — до 10 основных навыков/областей (через запятую):\n"
        "Пример: Product Discovery, Roadmapping, A/B-testing, Stakeholder Management",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.competencies)

async def start_superpowers_flow(message, state: FSMContext):
    """Start superpowers collection"""
    await message.answer(
        "Карта суперсил — чем вы отличаетесь и как это приносит бизнесу выгоду (через запятую):\n"
        "Пример: Сократил time-to-market на 40%, Увеличил retention на 20%",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.superpowers)

async def start_constraints_flow(message, state: FSMContext):
    """Start constraints collection"""
    await message.answer(
        "Дополнительные ограничения и рамки — ваши фильтры для поиска:\n"
        "Пример: Remote only, Компания с релизами не реже раза в месяц",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.constraints)

async def start_linkedin_flow(message, state: FSMContext):
    """Start LinkedIn URL collection"""
    await message.answer(
        "Ссылка на LinkedIn — ваш профиль в LinkedIn:\n"
        "Пример: https://linkedin.com/in/yourprofile",
        reply_markup=get_skip_back_keyboard()
    )
    await state.set_state(ProfileStates.linkedin)

async def finish_profile_creation(message, state: FSMContext):
    """Complete profile creation and save"""
    data = await state.get_data()
    
    # Build complete profile data
    profile_data = {
        'role': data['role'],
        'current_location': data['current_location'],
        'target_location': data['target_location'],
        'level': data['level'],
        'deadline_weeks': data['deadline_weeks'],
        'target_end_date': data['target_end_date'],
        'preferred_funnel_type': data.get('preferred_funnel_type', 'active')
    }
    
    # Add optional fields if present
    if data.get('role_synonyms'):
        profile_data['role_synonyms_json'] = json.dumps(data['role_synonyms'])
    if data.get('salary_min') and data.get('salary_max'):
        profile_data.update({
            'salary_min': data['salary_min'],
            'salary_max': data['salary_max'], 
            'salary_currency': data.get('salary_currency', 'EUR'),
            'salary_period': data.get('salary_period', 'год')
        })
    if data.get('company_types'):
        profile_data['company_types_json'] = json.dumps(data['company_types'])
    if data.get('industries'):
        profile_data['industries_json'] = json.dumps(data['industries'])
    if data.get('competencies'):
        profile_data['competencies_json'] = json.dumps(data['competencies'])
    if data.get('superpowers'):
        profile_data['superpowers_json'] = json.dumps(data['superpowers'])
    if data.get('constraints'):
        profile_data['constraints'] = data['constraints']
    if data.get('linkedin'):
        profile_data['linkedin'] = data['linkedin']
    
    # Save profile
    user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
    save_profile(user_id, profile_data)
    await state.clear()
    
    await message.answer(
        "✅ Профиль успешно создан!\n\n"
        "Используйте 'Профиль кандидата' в главном меню для просмотра.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Главное меню", callback_data="main_menu")]
        ])
    )

# Additional FSM handlers for optional fields
@dp.message(ProfileStates.role_synonyms, F.text)
async def process_role_synonyms(message: types.Message, state: FSMContext):
    """Process role synonyms input"""
    synonyms_text = message.text.strip()
    synonyms = [s.strip() for s in synonyms_text.split(',') if s.strip()][:4]
    await state.update_data(role_synonyms=synonyms)
    await start_salary_flow(message, state)

@dp.message(ProfileStates.salary_min, F.text)
async def process_salary(message: types.Message, state: FSMContext):
    """Process salary range or single value in single input"""
    salary_text = message.text.strip()
    
    # Parse formats like "60000 EUR/год", "60000-70000 EUR/год" or "5000-8000 USD/месяц"
    try:
        parts = salary_text.split()
        if len(parts) < 2:
            await message.answer("Введите зарплату с валютой и периодом.\nПримеры: 60000 EUR/год, 60000-70000 EUR/год")
            return
            
        range_part = parts[0]
        currency_period = ' '.join(parts[1:])
        
        # Extract currency and period
        if '/' in currency_period:
            currency, period = currency_period.split('/')
            currency = currency.strip()
            period = period.strip()
        else:
            currency = currency_period.strip() or 'EUR'
            period = 'год'
        
        # Handle both single value and range
        if '-' in range_part:
            min_val, max_val = range_part.split('-')
            salary_min = float(min_val.strip())
            salary_max = float(max_val.strip())
        else:
            # Single value - use as both min and max
            salary_min = salary_max = float(range_part.strip())
        
        await state.update_data(
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency,
            salary_period=period
        )
        await start_company_types_flow(message, state)
        
    except (ValueError, IndexError):
        await message.answer("Введите в правильном формате.\nПримеры: 60000 EUR/год, 60000-70000 EUR/год, 5000-8000 USD/месяц")

@dp.message(ProfileStates.company_types, F.text)
async def process_company_types(message: types.Message, state: FSMContext):
    """Process company types input"""
    company_types_text = message.text.strip()
    company_types = [s.strip() for s in company_types_text.split(',') if s.strip()]
    await state.update_data(company_types=company_types)
    await start_industries_flow(message, state)

@dp.message(ProfileStates.industries, F.text)
async def process_industries(message: types.Message, state: FSMContext):
    """Process industries input"""
    industries_text = message.text.strip()
    industries = [s.strip() for s in industries_text.split(',') if s.strip()][:3]
    await state.update_data(industries=industries)
    await start_competencies_flow(message, state)

@dp.message(ProfileStates.competencies, F.text)
async def process_competencies(message: types.Message, state: FSMContext):
    """Process competencies input"""
    competencies_text = message.text.strip()
    competencies = [s.strip() for s in competencies_text.split(',') if s.strip()][:10]
    await state.update_data(competencies=competencies)
    await start_superpowers_flow(message, state)

@dp.message(ProfileStates.superpowers, F.text)
async def process_superpowers(message: types.Message, state: FSMContext):
    """Process superpowers input"""
    superpowers_text = message.text.strip()
    superpowers = [s.strip() for s in superpowers_text.split(',') if s.strip()][:5]
    # Remove minimum requirement - all optional fields should be skippable
    await state.update_data(superpowers=superpowers)
    await start_constraints_flow(message, state)

@dp.message(ProfileStates.constraints, F.text)
async def process_constraints(message: types.Message, state: FSMContext):
    """Process constraints input"""
    constraints = message.text.strip()
    await state.update_data(constraints=constraints)
    await start_linkedin_flow(message, state)

@dp.message(ProfileStates.linkedin, F.text)
async def process_linkedin(message: types.Message, state: FSMContext):
    """Process LinkedIn URL input"""
    linkedin = message.text.strip()
    await state.update_data(linkedin=linkedin)
    await finish_profile_creation(message, state)

async def main():
    """Основная функция запуска бота"""
    # Инициализируем базу данных
    init_db()
    
    # Регистрируем обработчики рефлексии PRD v3.1
    from integration_v31 import register_v31_reflection_handlers
    register_v31_reflection_handlers(dp)
    
    # Настраиваем напоминания
    setup_reminders(bot)
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
