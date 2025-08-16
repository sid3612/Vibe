"""
Inline keyboards for profile setup and management
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_level_keyboard():
    """Keyboard for selecting experience level"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("Junior", callback_data="level_junior"),
        InlineKeyboardButton("Middle", callback_data="level_middle"),
        InlineKeyboardButton("Senior", callback_data="level_senior"),
        InlineKeyboardButton("Lead", callback_data="level_lead"),
        InlineKeyboardButton("Своё", callback_data="level_custom")
    ]
    
    keyboard.add(*buttons[:2])  # Junior, Middle
    keyboard.add(*buttons[2:4])  # Senior, Lead
    keyboard.add(buttons[4])     # Своё
    
    return keyboard

def get_company_types_keyboard(selected: list = None):
    """Keyboard for selecting company types (multi-select)"""
    if selected is None:
        selected = []
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    types = [
        ("SMB", "company_smb"),
        ("Scale-up", "company_scaleup"),
        ("Enterprise", "company_enterprise"),
        ("Consulting", "company_consulting"),
        ("Своё", "company_custom")
    ]
    
    for name, callback in types:
        text = f"✅ {name}" if callback.split('_')[1] in selected else name
        keyboard.add(InlineKeyboardButton(text, callback_data=callback))
    
    keyboard.add(
        InlineKeyboardButton("Готово", callback_data="company_done"),
        InlineKeyboardButton("Пропустить", callback_data="skip_step")
    )
    
    return keyboard

def get_skip_back_keyboard():
    """Standard skip/back keyboard for optional fields"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Пропустить", callback_data="skip_step"),
        InlineKeyboardButton("Назад", callback_data="back_step")
    )
    return keyboard

def get_back_keyboard():
    """Just back button for required fields"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_step"))
    return keyboard

def get_profile_actions_keyboard():
    """Main profile actions after viewing"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Редактировать", callback_data="profile_edit"),
        InlineKeyboardButton("Удалить", callback_data="profile_delete")
    )
    keyboard.add(InlineKeyboardButton("Назад в меню", callback_data="main_menu"))
    return keyboard

def get_profile_edit_fields_keyboard():
    """Select field to edit"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
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
    
    for name, callback in fields:
        keyboard.add(InlineKeyboardButton(name, callback_data=callback))
    
    keyboard.add(InlineKeyboardButton("Назад", callback_data="profile_view"))
    return keyboard

def get_confirm_delete_keyboard():
    """Confirm profile deletion"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Да, удалить", callback_data="confirm_delete"),
        InlineKeyboardButton("Отмена", callback_data="profile_view")
    )
    return keyboard

def get_final_review_keyboard():
    """Final review options before saving"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Сохранить профиль", callback_data="save_profile"),
        InlineKeyboardButton("Исправить поле", callback_data="review_edit"),
        InlineKeyboardButton("Отмена", callback_data="cancel_profile")
    )
    return keyboard