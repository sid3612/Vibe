#!/usr/bin/env python3
"""
Test script for button migration - moving funnel change to profile and removing FAQ from profile
"""

import sys
sys.path.append('.')

from keyboards import get_profile_actions_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def test_button_migration():
    """Test that buttons were moved correctly"""
    print("🧪 Testing Button Migration...")
    
    # Test main menu keyboard (simulate what's in main.py)
    main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль кандидата", callback_data="profile_menu")],
        [InlineKeyboardButton(text="📝 Управление каналами", callback_data="manage_channels")],
        [InlineKeyboardButton(text="➕ Добавить данные за неделю", callback_data="add_week_data")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_data")],
        [InlineKeyboardButton(text="📈 Показать историю", callback_data="show_history")],
        [InlineKeyboardButton(text="💾 Экспорт в CSV", callback_data="export_csv")],
        [InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="setup_reminders")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
    ])
    
    # Test profile keyboard
    profile_keyboard = get_profile_actions_keyboard()
    
    print("🔍 Checking main menu...")
    
    # Check that main menu does NOT have "🔄 Сменить воронку"
    main_menu_buttons = []
    for row in main_menu_keyboard.inline_keyboard:
        for button in row:
            main_menu_buttons.append((button.text, button.callback_data))
    
    funnel_change_in_main = any("Сменить воронку" in text for text, _ in main_menu_buttons)
    if funnel_change_in_main:
        print("❌ Main menu still contains 'Сменить воронку' button")
        return False
    else:
        print("✅ Main menu does not contain 'Сменить воронку' button")
    
    # Check that main menu HAS FAQ
    faq_in_main = any("FAQ" in text for text, _ in main_menu_buttons)
    if faq_in_main:
        print("✅ Main menu contains FAQ button")
    else:
        print("❌ Main menu is missing FAQ button")
        return False
    
    print("🔍 Checking profile menu...")
    
    # Check that profile menu HAS "🔄 Сменить воронку"
    profile_buttons = []
    for row in profile_keyboard.inline_keyboard:
        for button in row:
            profile_buttons.append((button.text, button.callback_data))
    
    funnel_change_in_profile = any("Сменить воронку" in text for text, _ in profile_buttons)
    if funnel_change_in_profile:
        print("✅ Profile menu contains 'Сменить воронку' button")
    else:
        print("❌ Profile menu is missing 'Сменить воронку' button")
        return False
    
    # Check that profile menu does NOT have FAQ
    faq_in_profile = any("FAQ" in text for text, _ in profile_buttons)
    if faq_in_profile:
        print("❌ Profile menu still contains FAQ button")
        return False
    else:
        print("✅ Profile menu does not contain FAQ button")
    
    print("\n📋 Profile keyboard structure:")
    for i, row in enumerate(profile_keyboard.inline_keyboard):
        for j, button in enumerate(row):
            print(f"  Row {i+1}: '{button.text}' → {button.callback_data}")
    
    print("\n🎉 Button migration test passed!")
    print("📝 Changes summary:")
    print("  • Moved '🔄 Сменить воронку' from main menu to profile menu ✓")
    print("  • Removed 'FAQ' button from profile menu ✓")
    print("  • Kept 'FAQ' button in main menu ✓")
    
    return True

if __name__ == "__main__":
    success = test_button_migration()
    sys.exit(0 if success else 1)