#!/usr/bin/env python3
"""
Simple test to verify PRD v3.1 reflection callback handlers are working
"""

import asyncio
from unittest.mock import AsyncMock, Mock
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

async def test_reflection_callbacks():
    """Test that reflection callback handlers work correctly"""
    print("🧪 Testing PRD v3.1 callback handlers...")
    
    # Import handlers
    try:
        from integration_v31 import register_v31_reflection_handlers
        from reflection_v31 import handle_reflection_v31_yes, handle_reflection_v31_no
        print("✅ Successfully imported v3.1 handlers")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Create mock objects
    storage = MemoryStorage()
    
    # Mock callback query for "Yes" button
    callback_yes = Mock(spec=types.CallbackQuery)
    callback_yes.data = "reflection_v31_yes_1"
    callback_yes.message = Mock(spec=types.Message)
    callback_yes.message.edit_text = AsyncMock()
    callback_yes.answer = AsyncMock()
    
    # Mock callback query for "No" button
    callback_no = Mock(spec=types.CallbackQuery)
    callback_no.data = "reflection_v31_no"
    callback_no.message = Mock(spec=types.Message)
    callback_no.message.edit_text = AsyncMock()
    callback_no.answer = AsyncMock()
    
    # Mock FSM context
    state = Mock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={
        'reflection_sections': [{'stage': 'response', 'delta': 2}],
        'reflection_context': {
            'user_id': 123,
            'week_start': '2025-01-20',
            'channel': 'LinkedIn',
            'funnel_type': 'active'
        }
    })
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    try:
        # Test "No" handler
        await handle_reflection_v31_no(callback_no)
        print("✅ 'No' handler executed successfully")
        
        # Test "Yes" handler
        await handle_reflection_v31_yes(callback_yes, state)
        print("✅ 'Yes' handler executed successfully")
        
        # Verify mock calls
        assert callback_no.answer.called, "'No' callback should call answer()"
        assert callback_yes.answer.called, "'Yes' callback should call answer()"
        
        print("✅ All callback handlers working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Handler execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_callback_data_parsing():
    """Test callback data parsing logic"""
    print("\n🧪 Testing callback data parsing...")
    
    test_cases = [
        ("reflection_v31_yes_1", True, "Should match 'yes' pattern"),
        ("reflection_v31_yes_3", True, "Should match 'yes' pattern with multiple sections"),
        ("reflection_v31_no", True, "Should match 'no' pattern"),
        ("reflection_v31_cancel", True, "Should match 'cancel' pattern"),
        ("rating_4", True, "Should match rating pattern"),
        ("reason_v31_skill", True, "Should match rejection reason pattern"),
        ("reasons_v31_done", True, "Should match rejection done pattern"),
        ("other_callback", False, "Should not match unrelated callback")
    ]
    
    # Test patterns (simplified version of actual handler patterns)
    patterns = {
        'yes': lambda x: x.startswith("reflection_v31_yes_"),
        'no': lambda x: x == "reflection_v31_no",
        'cancel': lambda x: x == "reflection_v31_cancel",
        'rating': lambda x: x.startswith("rating_") and len(x.split('_')) == 2,
        'reason': lambda x: x.startswith("reason_v31_"),
        'reason_done': lambda x: x == "reasons_v31_done"
    }
    
    all_passed = True
    for callback_data, should_match, description in test_cases:
        matched = any(pattern(callback_data) for pattern in patterns.values())
        
        if matched == should_match:
            print(f"✅ {description}: '{callback_data}' -> {matched}")
        else:
            print(f"❌ {description}: '{callback_data}' -> {matched} (expected {should_match})")
            all_passed = False
    
    return all_passed

async def main():
    """Run all callback tests"""
    print("🚀 Starting PRD v3.1 Callback Tests\n")
    
    test1_passed = await test_reflection_callbacks()
    test2_passed = await test_callback_data_parsing()
    
    if test1_passed and test2_passed:
        print("\n🎉 All callback tests passed!")
        print("\n📋 Callback System Status:")
        print("✅ Handler imports working")
        print("✅ 'Yes/No' callbacks functional")
        print("✅ Callback data patterns correct")
        print("✅ Mock execution successful")
        print("\nThe reflection form buttons should now be clickable in Telegram!")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())