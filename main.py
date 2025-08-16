import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db, add_user, get_user_funnels, set_active_funnel, get_user_channels, add_channel, remove_channel, add_week_data, get_week_data, update_week_field, get_user_history, set_user_reminders
from metrics import calculate_cvr_metrics, format_metrics_table, format_history_table
from export import generate_csv_export
from faq import get_faq_text
from reminders import setup_reminders, send_reminder

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
    
    welcome_text = """
🎯 Добро пожаловать в Job Funnel Coach!

Этот бот поможет вам отслеживать и анализировать воронки поиска работы.

Доступные команды:
/menu - Главное меню
/help - Помощь
/faq - Часто задаваемые вопросы

Выберите тип воронки для начала работы:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Активная воронка", callback_data="funnel_active")],
        [InlineKeyboardButton(text="👀 Пассивная воронка", callback_data="funnel_passive")],
        [InlineKeyboardButton(text="📊 Главное меню", callback_data="main_menu")]
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

async def show_main_menu(user_id: int, message_or_query):
    """Показать главное меню"""
    user_data = get_user_funnels(user_id)
    current_funnel = "Активная" if user_data.get('active_funnel') == 'active' else "Пассивная"
    
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
    
    if hasattr(message_or_query, 'edit_text'):
        await message_or_query.edit_text(menu_text, reply_markup=keyboard)
    else:
        await message_or_query.answer(menu_text, reply_markup=keyboard)

@dp.callback_query()
async def process_callback(query: CallbackQuery, state: FSMContext):
    """Обработчик всех callback запросов"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "funnel_active":
        set_active_funnel(user_id, "active")
        await query.answer("Выбрана активная воронка")
        await show_main_menu(user_id, query.message)
        
    elif data == "funnel_passive":
        set_active_funnel(user_id, "passive")
        await query.answer("Выбрана пассивная воронка")
        await show_main_menu(user_id, query.message)
        
    elif data == "main_menu":
        await show_main_menu(user_id, query.message)
        
    elif data == "change_funnel":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Активная воронка", callback_data="funnel_active")],
            [InlineKeyboardButton(text="👀 Пассивная воронка", callback_data="funnel_passive")],
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
        await show_user_history(user_id, query.message)
        
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
        
    elif data.startswith("select_channel_"):
        channel = data.replace("select_channel_", "")
        user_data = get_user_funnels(user_id)
        funnel_type = user_data.get('active_funnel', 'active')
        
        await state.update_data(selected_channel=channel, funnel_type=funnel_type)
        
        if funnel_type == 'active':
            field_name = "подачи (applications)"
        else:
            field_name = "просмотры (views)"
        
        text = f"📊 Канал: {channel}\n\nВведите количество {field_name}:"
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
                ('rejections', 'Реджекты')
            ]
        else:
            fields = [
                ('views', 'Просмотры'),
                ('incoming', 'Входящие'),
                ('screenings', 'Скрининги'),
                ('onsites', 'Онсайты'),
                ('offers', 'Офферы'),
                ('rejections', 'Реджекты')
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
        
    elif data == "show_faq":
        faq_text = get_faq_text()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
        ])
        await query.message.edit_text(faq_text, reply_markup=keyboard, parse_mode="HTML")

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

async def show_user_history(user_id: int, message):
    """Показать историю пользователя"""
    history_data = get_user_history(user_id)
    user_data = get_user_funnels(user_id)
    funnel_type = user_data.get('active_funnel', 'active')
    
    if not history_data:
        text = "📈 История данных\n\nДанных пока нет. Добавьте данные за неделю для просмотра истории."
    else:
        text = format_history_table(history_data, funnel_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
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
                    add_week_data(user_id, week_start, channel, funnel_type, data)
                    success_count += 1
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
                    add_week_data(user_id, week_start, channel, funnel_type, data)
                    success_count += 1
        
        if success_count > 0:
            await message.answer(f"✅ Добавлено {success_count} записей за неделю {week_start}")
            await state.clear()
            # Показываем главное меню новым сообщением
            user_data = get_user_funnels(user_id)
            current_funnel = "Активная" if user_data.get('active_funnel') == 'active' else "Пассивная"
            
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
            field_name = "ответы (responses)"
        else:
            await state.update_data(views=value)
            field_name = "входящие (incoming)"
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество {field_name}:")
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
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество скрининги (screenings):")
        await state.set_state(FunnelStates.entering_screenings)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_screenings)
async def process_screenings(message: types.Message, state: FSMContext):
    """Обработка ввода скринингов"""
    try:
        value = int(message.text.strip())
        await state.update_data(screenings=value)
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество онсайты (onsites):")
        await state.set_state(FunnelStates.entering_onsites)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_onsites)
async def process_onsites(message: types.Message, state: FSMContext):
    """Обработка ввода онсайтов"""
    try:
        value = int(message.text.strip())
        await state.update_data(onsites=value)
            
        await message.answer(f"✅ Сохранено\n\nТеперь введите количество офферы (offers):")
        await state.set_state(FunnelStates.entering_offers)
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(FunnelStates.entering_offers)
async def process_offers(message: types.Message, state: FSMContext):
    """Обработка ввода офферов"""
    try:
        value = int(message.text.strip())
        await state.update_data(offers=value)
            
        await message.answer(f"✅ Сохранено\n\nНаконец, введите количество реджекты (rejections):")
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
        
        # Сохраняем данные
        channel = data.get('selected_channel')
        add_week_data(user_id, week_start, channel, funnel_type, week_data)
        
        await message.answer(f"✅ Данные успешно сохранены для канала {channel} за неделю {week_start}!")
        await state.clear()
        
        # Показываем главное меню
        await show_main_menu_new_message(user_id, message)
        
    except ValueError:
        await message.answer("❌ Введите число")

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
        await show_main_menu_new_message(user_id, message)
        
    except ValueError:
        await message.answer("❌ Введите число")

async def show_main_menu_new_message(user_id: int, message):
    """Показать главное меню новым сообщением"""
    user_data = get_user_funnels(user_id)
    current_funnel = "Активная" if user_data.get('active_funnel') == 'active' else "Пассивная"
    
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

@dp.message()
async def handle_edit_command(message: types.Message):
    """Обработка команд редактирования данных"""
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем, является ли это командой редактирования
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
        # Показываем справку
        await message.answer("Используйте команды: /start, /menu, /help, /faq")

async def main():
    """Основная функция запуска бота"""
    # Инициализируем базу данных
    init_db()
    
    # Настраиваем напоминания
    setup_reminders(bot)
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
