"""
Inline keyboards for profile setup and management
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_level_keyboard():
    """Keyboard for selecting experience level"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Junior", callback_data="level_junior"),
            InlineKeyboardButton(text="Middle", callback_data="level_middle")
        ],
        [
            InlineKeyboardButton(text="Senior", callback_data="level_senior"),
            InlineKeyboardButton(text="Lead", callback_data="level_lead")
        ],
        [
            InlineKeyboardButton(text="Своё", callback_data="level_custom")
        ]
    ])
    
    return keyboard

def get_company_types_keyboard(selected: list = None):
    """Keyboard for selecting company types (multi-select)"""
    if selected is None:
        selected = []
    
    types = [
        ("SMB", "company_SMB"),
        ("Scale-up", "company_Scale-up"),
        ("Enterprise", "company_Enterprise"),
        ("Consulting", "company_Consulting")
    ]
    
    keyboard_rows = []
    for name, callback in types:
        company_name = callback.replace("company_", "")
        text = f"✅ {name}" if company_name in selected else name
        keyboard_rows.append([InlineKeyboardButton(text=text, callback_data=callback)])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="Готово", callback_data="company_done"),
        InlineKeyboardButton(text="Пропустить", callback_data="skip_step")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_skip_back_keyboard():
    """Standard skip/back keyboard for optional fields"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="skip_step"),
            InlineKeyboardButton(text="Назад", callback_data="back_step")
        ]
    ])

def get_back_keyboard():
    """Just back button for required fields"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_step")]
    ])

def get_profile_actions_keyboard():
    """Main profile actions after viewing"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Редактировать", callback_data="profile_edit"),
            InlineKeyboardButton(text="Удалить", callback_data="profile_delete")
        ],
        [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
    ])

def get_profile_edit_fields_keyboard():
    """Select field to edit"""
    fields = [
        ("Роль", "edit_role"),
        ("Текущая локация", "edit_current_location"),
        ("Локация поиска", "edit_target_location"),
        ("Уровень", "edit_level"),
        ("Срок (недели)", "edit_deadline"),
        ("Синонимы ролей", "edit_synonyms"),
        ("Зарплата", "edit_salary"),
        ("Типы компаний", "edit_company_types"),
        ("Индустрии", "edit_industries"),
        ("Компетенции", "edit_competencies"),
        ("Суперсилы", "edit_superpowers"),
        ("Ограничения", "edit_constraints")
    ]
    
    keyboard_rows = []
    for name, callback in fields:
        keyboard_rows.append([InlineKeyboardButton(text=name, callback_data=callback)])
    
    keyboard_rows.append([InlineKeyboardButton(text="Назад", callback_data="profile_view")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_confirm_delete_keyboard():
    """Confirm profile deletion"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data="confirm_delete"),
            InlineKeyboardButton(text="Отмена", callback_data="profile_view")
        ]
    ])

def get_funnel_type_keyboard():
    """Keyboard for selecting funnel type"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧑‍💻 Активный поиск (я подаюсь)", callback_data="funnel_active")],
        [InlineKeyboardButton(text="👀 Пассивный поиск (мне пишут)", callback_data="funnel_passive")],
        [InlineKeyboardButton(text="Назад", callback_data="back_step")]
    ])

def get_final_review_keyboard():
    """Final review options before saving"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сохранить профиль", callback_data="save_profile")],
        [InlineKeyboardButton(text="Исправить поле", callback_data="review_edit")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_profile")]
    ])