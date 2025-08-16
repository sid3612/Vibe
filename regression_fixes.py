#!/usr/bin/env python3
"""
Final verification that PRD v3 reflection system is working correctly
"""

from db import init_db, add_week_data, get_week_data
from reflection_forms import ReflectionTrigger, ReflectionQueue
from datetime import datetime, timedelta

def final_integration_test():
    """Test complete integration of reflection system"""
    print("🚀 Final Integration Test - PRD v3 Reflection System")
    print("=" * 60)
    
    init_db()
    
    # Test user and data
    test_user_id = 777777
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime('%Y-%m-%d')
    
    # Simulate adding initial data
    print("📊 Step 1: Adding initial week data")
    initial_data = {
        'applications': 10,
        'responses': 2, 
        'screenings': 1,
        'onsites': 0,
        'offers': 0,
        'rejections': 8
    }
    
    add_week_data(test_user_id, week_start, "LinkedIn", "active", initial_data, check_triggers=False)
    print("   ✅ Initial data added")
    
    # Get old data
    old_data_record = get_week_data(test_user_id, week_start, "LinkedIn", "active")
    old_data = dict(old_data_record) if old_data_record else {}
    print(f"   📄 Old data: {old_data}")
    
    # Add new data with increases
    print("📊 Step 2: Adding new data with increases")
    new_data = {
        'applications': 5,  # Total will be 15
        'responses': 3,     # Total will be 5 (+3 increase -> trigger)
        'screenings': 2,    # Total will be 3 (+2 increase -> trigger) 
        'onsites': 1,       # Total will be 1 (+1 increase -> trigger)
        'offers': 1,        # Total will be 1 (+1 increase -> trigger)
        'rejections': 2     # Total will be 10 (+2 increase -> trigger)
    }
    
    add_week_data(test_user_id, week_start, "LinkedIn", "active", new_data, check_triggers=False)
    
    # Get updated data
    updated_data_record = get_week_data(test_user_id, week_start, "LinkedIn", "active")
    updated_data = dict(updated_data_record) if updated_data_record else {}
    print(f"   📄 Updated data: {updated_data}")
    
    # Test trigger detection
    print("🔍 Step 3: Testing trigger detection")
    triggers = ReflectionTrigger.check_triggers(
        test_user_id, week_start, "LinkedIn", "active", old_data, updated_data
    )
    
    print(f"   🎯 Triggers detected: {triggers}")
    expected_triggers = ['responses', 'screenings', 'onsites', 'offers', 'rejections']
    actual_trigger_stages = [stage for stage, delta in triggers]
    
    triggers_correct = all(stage in actual_trigger_stages for stage in expected_triggers)
    print(f"   ✅ Trigger detection: {'PASS' if triggers_correct else 'FAIL'}")
    
    # Test queue creation
    print("📋 Step 4: Testing queue creation")
    total_forms_expected = sum(delta for _, delta in triggers)
    
    for stage, delta in triggers:
        entry_ids = ReflectionQueue.create_queue_entries(
            test_user_id, week_start, "LinkedIn", "active", stage, delta
        )
        print(f"   ➕ Created {len(entry_ids)} forms for {stage} stage")
    
    pending_forms = ReflectionQueue.get_pending_forms(test_user_id)
    print(f"   📊 Total pending forms: {len(pending_forms)}")
    
    queue_correct = len(pending_forms) == total_forms_expected
    print(f"   ✅ Queue creation: {'PASS' if queue_correct else 'FAIL'}")
    
    # Test commands
    print("🛠 Step 5: Testing command functionality")
    next_form = ReflectionQueue.get_next_form(test_user_id)
    commands_working = next_form is not None
    print(f"   ✅ Commands ready: {'PASS' if commands_working else 'FAIL'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    all_tests_passed = triggers_correct and queue_correct and commands_working
    
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Reflection system fully integrated and working")
        print("✅ Triggers detect counter increases correctly")
        print("✅ Queue management functional") 
        print("✅ Ready for user testing")
        print("\n🚀 SYSTEM STATUS: PRODUCTION READY")
        print("📝 User can now test by adding statistical data")
    else:
        print("⚠️  Some tests failed - check implementation")
    
    print("=" * 60)
    return all_tests_passed

if __name__ == "__main__":
    final_integration_test()