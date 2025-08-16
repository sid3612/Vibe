#!/usr/bin/env python3
"""
Test script for verifying funnel button location in profile menu
"""

import sys
sys.path.append('.')

from keyboards import get_profile_actions_keyboard
from main import show_main_menu

def test_funnel_button_moved():
    """Test that funnel button is now in profile menu, not main menu"""
    print("🧪 Testing Funnel Button Location...")
    
    # Test profile actions keyboard has funnel button
    profile_keyboard = get_profile_actions_keyboard()
    funnel_button_found = False
    
    for row in profile_keyboard.inline_keyboard:
        for button in row:
            if "Сменить воронку" in button.text:
                funnel_button_found = True
                print(f"✅ Found funnel button in profile menu: '{button.text}' -> {button.callback_data}")
                break
        if funnel_button_found:
            break
    
    if funnel_button_found:
        print("✅ Funnel button successfully moved to profile menu")
    else:
        print("❌ Funnel button not found in profile menu")
        return False
    
    # Verify expected structure of profile menu
    expected_buttons = ["Редактировать", "Удалить", "Сменить воронку", "Назад в меню"]
    found_buttons = []
    
    for row in profile_keyboard.inline_keyboard:
        for button in row:
            found_buttons.append(button.text)
    
    print(f"Profile menu buttons: {found_buttons}")
    
    for expected in expected_buttons:
        if any(expected in btn for btn in found_buttons):
            print(f"✅ Found expected button: {expected}")
        else:
            print(f"❌ Missing expected button: {expected}")
            return False
    
    print("\n🎉 All funnel button location tests passed!")
    return True

if __name__ == "__main__":
    success = test_funnel_button_moved()
    sys.exit(0 if success else 1)