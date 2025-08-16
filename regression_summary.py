#!/usr/bin/env python3
"""
Regression Testing Summary Report
"""

import json
from db import init_db, save_profile, get_profile, delete_profile
from profile import format_profile_display

def run_core_tests():
    """Run essential regression tests"""
    print("🚀 Running Core Regression Tests")
    print("=" * 50)
    
    init_db()
    
    # Test 1: LinkedIn field functionality
    print("🧪 Test 1: LinkedIn field integration")
    test_user_id = 999991
    
    profile_data = {
        'role': 'Software Engineer',
        'current_location': 'Berlin',
        'target_location': 'Remote',
        'level': 'Senior',
        'deadline_weeks': 12,
        'target_end_date': '2025-11-16',
        'linkedin': 'https://linkedin.com/in/engineer'
    }
    
    save_profile(test_user_id, profile_data)
    retrieved = get_profile(test_user_id)
    
    linkedin_ok = retrieved.get('linkedin') == profile_data['linkedin']
    display = format_profile_display(retrieved)
    display_ok = 'LINKEDIN' in display and 'https://linkedin.com/in/engineer' in display
    
    print(f"   LinkedIn field saved: {'✅' if linkedin_ok else '❌'}")
    print(f"   LinkedIn in display: {'✅' if display_ok else '❌'}")
    
    delete_profile(test_user_id)
    
    # Test 2: Constraints field mapping
    print("🧪 Test 2: Constraints field mapping")
    test_user_id = 999992
    
    profile_with_constraints = {
        'role': 'Product Manager',
        'current_location': 'Moscow',
        'target_location': 'EU',
        'level': 'Senior',
        'deadline_weeks': 16,
        'target_end_date': '2025-12-01',
        'constraints': 'Remote only, Flexible hours'
    }
    
    save_profile(test_user_id, profile_with_constraints)
    retrieved = get_profile(test_user_id)
    
    constraints_saved = retrieved.get('constraints_text') == 'Remote only, Flexible hours'
    print(f"   Constraints saved correctly: {'✅' if constraints_saved else '❌'}")
    
    delete_profile(test_user_id)
    
    # Test 3: Date calculation accuracy
    print("🧪 Test 3: Date calculation accuracy")
    from validators import calculate_target_end_date
    from datetime import datetime, timedelta
    
    calculated = calculate_target_end_date(12)
    expected = datetime.now().date() + timedelta(weeks=12)
    calc_date = datetime.strptime(calculated, '%Y-%m-%d').date()
    
    diff_days = abs((calc_date - expected).days)
    date_ok = diff_days <= 1
    print(f"   Date calculation accurate: {'✅' if date_ok else '❌'} (diff: {diff_days} days)")
    
    # Test 4: Plain text profile display
    print("🧪 Test 4: Plain text profile display format")
    test_user_id = 999993
    
    display_test_profile = {
        'role': 'Designer',
        'current_location': 'Paris',
        'target_location': 'Remote',
        'level': 'Middle',
        'deadline_weeks': 8,
        'target_end_date': '2025-10-16',
        'salary_min': 50000,
        'salary_max': 50000,
        'salary_currency': 'EUR',
        'salary_period': 'год'
    }
    
    save_profile(test_user_id, display_test_profile)
    retrieved = get_profile(test_user_id)
    display = format_profile_display(retrieved)
    
    is_plain_text = '📋 ВАШ ПРОФИЛЬ' in display and '50000 EUR/год' in display
    print(f"   Plain text display format: {'✅' if is_plain_text else '❌'}")
    
    delete_profile(test_user_id)
    
    print("\n" + "=" * 50)
    print("REGRESSION TESTING COMPLETED")
    print("=" * 50)
    
    all_tests_passed = linkedin_ok and display_ok and constraints_saved and date_ok and is_plain_text
    
    if all_tests_passed:
        print("🎉 ALL CORE TESTS PASSED")
        print("✅ System stable and ready for use")
        print("✅ LinkedIn field working correctly")
        print("✅ Profile display in plain text format")
        print("✅ Constraints field mapping fixed")
        print("✅ Date calculations accurate")
    else:
        print("⚠️  Some tests failed - see details above")
    
    print("=" * 50)
    return all_tests_passed

if __name__ == "__main__":
    run_core_tests()