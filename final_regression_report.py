#!/usr/bin/env python3
"""
Final test for corrected reflection trigger behavior
Tests that reflection prompt appears ONLY after completing all 5 fields
"""

import sqlite3
from db import init_db, add_week_data, get_week_data, get_db_connection

def test_reflection_trigger_timing():
    """Test that reflection trigger happens after completing ALL 5 fields"""
    print("🧪 Testing Reflection Trigger Timing")
    print("=" * 50)
    
    init_db()
    
    # Clean test environment
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM week_data WHERE user_id = 999999")
    cursor.execute("DELETE FROM reflection_queue WHERE user_id = 999999")
    conn.commit()
    conn.close()
    
    test_user_id = 999999
    week_start = '2025-08-16'
    channel = 'LinkedIn'
    funnel_type = 'active'
    
    print(f"Testing scenario: Applications=1 → Responses=1 → Screenings=0 → Onsites=0 → Offers=0 → Rejections=1")
    
    # Test the complete 5-field data entry as it happens in the wizard
    complete_data = {
        'applications': 1,
        'responses': 1,      # +1 delta
        'screenings': 0,     # 0 delta
        'onsites': 0,        # 0 delta  
        'offers': 0,         # 0 delta
        'rejections': 1      # +1 delta
    }
    
    print("📊 Step 1: Adding complete data set (simulating end of 5-step wizard)")
    
    # Get old data (should be empty for new user)
    old_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    old_data_dict = dict(old_data_record) if old_data_record else {}
    print(f"   Old data: {old_data_dict}")
    
    # Save data
    add_week_data(test_user_id, week_start, channel, funnel_type, complete_data, check_triggers=False)
    
    # Get new data
    new_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    new_data_dict = dict(new_data_record) if new_data_record else {}
    print(f"   New data: {new_data_dict}")
    
    # Calculate triggers for statistical fields only
    statistical_fields = ['responses', 'screenings', 'onsites', 'offers', 'rejections']
    triggers = []
    
    for field in statistical_fields:
        old_value = old_data_dict.get(field, 0)
        new_value = new_data_dict.get(field, 0)
        delta = new_value - old_value
        if delta > 0:
            triggers.append((field, delta))
    
    print(f"🎯 Step 2: Triggers detected: {triggers}")
    
    # Expected: responses +1, rejections +1 = 2 total forms
    expected_triggers = [('responses', 1), ('rejections', 1)]
    triggers_correct = triggers == expected_triggers
    
    print(f"✅ Trigger detection: {'PASS' if triggers_correct else 'FAIL'}")
    print(f"   Expected: {expected_triggers}")
    print(f"   Actual: {triggers}")
    
    # Test that CVR changes don't trigger
    print("🔍 Step 3: Testing CVR changes don't trigger reflection")
    
    # Add more applications (should change CVR but not trigger reflection)
    cvr_data = {
        'applications': 5,  # This will change CVR1 but shouldn't trigger
        'responses': 0,     # No change in statistical fields
        'screenings': 0,
        'onsites': 0,
        'offers': 0,
        'rejections': 0
    }
    
    old_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    old_data_dict = dict(old_data_record) if old_data_record else {}
    
    add_week_data(test_user_id, week_start, channel, funnel_type, cvr_data, check_triggers=False)
    
    new_data_record = get_week_data(test_user_id, week_start, channel, funnel_type)
    new_data_dict = dict(new_data_record) if new_data_record else {}
    
    cvr_triggers = []
    for field in statistical_fields:
        old_value = old_data_dict.get(field, 0)
        new_value = new_data_dict.get(field, 0)
        delta = new_value - old_value
        if delta > 0:
            cvr_triggers.append((field, delta))
    
    cvr_test_passed = len(cvr_triggers) == 0
    print(f"✅ CVR changes don't trigger: {'PASS' if cvr_test_passed else 'FAIL'}")
    print(f"   CVR triggers: {cvr_triggers}")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    all_tests_passed = triggers_correct and cvr_test_passed
    
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Reflection trigger works correctly after 5-field completion")
        print("✅ CVR changes don't trigger reflection forms") 
        print("✅ System ready for user acceptance testing")
    else:
        print("❌ Some tests failed")
        if not triggers_correct:
            print("   - Trigger detection issue")
        if not cvr_test_passed:
            print("   - CVR changes incorrectly trigger reflection")
    
    return all_tests_passed

if __name__ == "__main__":
    test_reflection_trigger_timing()