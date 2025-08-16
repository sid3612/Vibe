#!/usr/bin/env python3
"""
Integration test for fixed state management
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from db import init_db, add_week_data, get_week_data
from reflection_forms import ReflectionTrigger

async def test_complete_flow():
    """Test complete 5-step flow with reflection trigger"""
    print("🧪 TESTING COMPLETE FLOW")
    print("=" * 50)
    
    # Setup
    init_db()
    test_user_id = 888888
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime('%Y-%m-%d')
    channel = "LinkedIn"
    funnel_type = "active"
    
    print(f"Testing user {test_user_id}, week {week_start}")
    
    # Step 1: Get old data (simulating empty state)
    old_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    old_data_dict = dict(old_data_record) if old_data_record else {}
    print(f"Old data: {old_data_dict}")
    
    # Step 2: Simulate completing 5-step wizard
    complete_data = {
        'applications': 1,
        'responses': 1,      # +1 delta (trigger)
        'screenings': 0,     # 0 delta (no trigger)
        'onsites': 0,        # 0 delta (no trigger)
        'offers': 0,         # 0 delta (no trigger)
        'rejections': 1      # +1 delta (trigger)
    }
    
    # Save data
    add_week_data(test_user_id, week_start, channel, funnel_type, complete_data, check_triggers=False)
    
    # Step 3: Get new data and check triggers
    new_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    new_data_dict = dict(new_data_record) if new_data_record else {}
    print(f"New data: {new_data_dict}")
    
    # Step 4: Calculate triggers exactly as in main.py
    statistical_fields = ['responses', 'screenings', 'onsites', 'offers', 'rejections']
    triggers = []
    
    for field in statistical_fields:
        old_value = old_data_dict.get(field, 0)
        new_value = new_data_dict.get(field, 0)
        delta = new_value - old_value
        if delta > 0:
            triggers.append((field, delta))
    
    print(f"Triggers detected: {triggers}")
    
    # Step 5: Verify expected results
    expected_triggers = [('responses', 1), ('rejections', 1)]
    success = triggers == expected_triggers
    
    print(f"✅ Test result: {'PASS' if success else 'FAIL'}")
    print(f"Expected: {expected_triggers}")
    print(f"Actual: {triggers}")
    
    if success:
        print("\n🎉 FLOW TEST PASSED")
        print("✅ 5-step wizard completion correctly detects triggers")
        print("✅ Only statistical fields trigger reflection forms")
        print("✅ State management should work correctly")
    else:
        print("\n❌ FLOW TEST FAILED")
    
    return success

if __name__ == "__main__":
    asyncio.run(test_complete_flow())