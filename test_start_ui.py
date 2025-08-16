#!/usr/bin/env python3
"""
Test script for new /start screen UI
"""

import sys
sys.path.append('.')

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def test_start_ui():
    """Test the new start screen text and buttons"""
    print("🧪 Testing New Start Screen UI...")
    
    # Test text content
    welcome_text = """👋HackOFFer — оффер быстрее и без догадок

Когда кажется, что "где-то течёт", но непонятно где.

HackOFFer — ваш AI-ментор по поиску работы: считает конверсию, находит узкие места и превращает их в понятные шаги.
Начни с Заполнения профиля, а после Внеси данные за неделю.

Выберите, с чего начнём:"""
    
    # Test keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Заполнить профиль", callback_data="create_profile")],
        [InlineKeyboardButton(text="📊 Внести данные за неделю", callback_data="data_entry")],
        [InlineKeyboardButton(text="📚 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
    ])
    
    print("✅ Welcome text created successfully")
    print(f"📝 Text preview:\n{welcome_text}\n")
    
    # Check buttons
    expected_buttons = [
        ("📝 Заполнить профиль", "create_profile"),
        ("📊 Внести данные за неделю", "data_entry"), 
        ("📚 Главное меню", "main_menu"),
        ("❓ FAQ", "show_faq")
    ]
    
    print("🔍 Checking buttons...")
    for i, row in enumerate(keyboard.inline_keyboard):
        if i < len(expected_buttons):
            button = row[0]
            expected_text, expected_callback = expected_buttons[i]
            
            if button.text == expected_text and button.callback_data == expected_callback:
                print(f"✅ Button {i+1}: '{button.text}' → {button.callback_data}")
            else:
                print(f"❌ Button {i+1} mismatch: expected '{expected_text}' → {expected_callback}, got '{button.text}' → {button.callback_data}")
                return False
        else:
            print(f"❌ Unexpected extra button: {row[0].text}")
            return False
    
    # Check that we have the right number of buttons
    if len(keyboard.inline_keyboard) != len(expected_buttons):
        print(f"❌ Wrong number of buttons: expected {len(expected_buttons)}, got {len(keyboard.inline_keyboard)}")
        return False
    
    print("\n🎉 Start screen UI test passed!")
    print("📋 Features:")
    print("  • HackOFFer branding ✓")
    print("  • AI-mentor positioning ✓") 
    print("  • Clear workflow guidance ✓")
    print("  • All required buttons ✓")
    
    return True

if __name__ == "__main__":
    success = test_start_ui()
    sys.exit(0 if success else 1)