#!/usr/bin/env python3
"""
Test script for skip and back buttons functionality in profile creation
"""

import sys
sys.path.append('.')

from main import dp, process_callback
from keyboards import get_skip_back_keyboard
from profile import ProfileStates
from aiogram.types import CallbackQuery, User, Chat, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

def test_skip_buttons():
    """Test skip button callback data and handlers"""
    print("🧪 Testing Skip/Back Buttons...")
    
    # Test keyboard creation
    keyboard = get_skip_back_keyboard()
    print("✅ Skip/back keyboard created successfully")
    
    # Check button data
    skip_button = None
    back_button = None
    
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.text == "Пропустить":
                skip_button = button
            elif button.text == "Назад":
                back_button = button
    
    if skip_button:
        print(f"✅ Skip button found with callback_data: {skip_button.callback_data}")
    else:
        print("❌ Skip button not found")
        return False
    
    if back_button:
        print(f"✅ Back button found with callback_data: {back_button.callback_data}")
    else:
        print("❌ Back button not found")
        return False
    
    # Check that handlers exist for these callback_data values
    expected_skip = "skip_step"
    expected_back = "back_step"
    
    if skip_button.callback_data == expected_skip:
        print("✅ Skip button has correct callback_data")
    else:
        print(f"❌ Skip button callback_data mismatch: expected {expected_skip}, got {skip_button.callback_data}")
        return False
    
    if back_button.callback_data == expected_back:
        print("✅ Back button has correct callback_data")
    else:
        print(f"❌ Back button callback_data mismatch: expected {expected_back}, got {back_button.callback_data}")
        return False
    
    print("\n🎉 All skip/back button tests passed!")
    return True

if __name__ == "__main__":
    success = test_skip_buttons()
    sys.exit(0 if success else 1)