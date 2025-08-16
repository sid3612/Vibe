#!/usr/bin/env python3
"""
Fix regression issues found in testing
"""

import json
from db import save_profile, get_profile, delete_profile

def fix_constraints_field_issue():
    """Fix the constraints field mapping issue"""
    print("🔧 Investigating constraints field issue...")
    
    test_user_id = 888888
    
    # Test profile with constraints
    test_profile = {
        'role': 'Test Role',
        'current_location': 'Test Location',
        'target_location': 'Test Target',
        'level': 'Senior',
        'deadline_weeks': 16,
        'target_end_date': '2025-12-01',
        'constraints': 'Test constraints text'
    }
    
    print(f"Original constraints: {test_profile.get('constraints')}")
    
    # Save profile
    save_profile(test_user_id, test_profile)
    
    # Retrieve and check
    retrieved = get_profile(test_user_id)
    print(f"Retrieved constraints_text: {retrieved.get('constraints_text')}")
    print(f"Retrieved constraints: {retrieved.get('constraints')}")
    
    # Check what's actually in the database
    import sqlite3
    conn = sqlite3.connect('funnel_coach.db')
    cursor = conn.cursor()
    cursor.execute("SELECT constraints_text FROM profiles WHERE user_id = ?", (test_user_id,))
    db_result = cursor.fetchone()
    print(f"Database constraints_text: {db_result[0] if db_result else 'None'}")
    conn.close()
    
    # The issue is that we need to ensure proper mapping
    # The save_profile function should convert 'constraints' to 'constraints_text'
    # And get_profile should convert 'constraints_text' back to 'constraints' for display
    
    delete_profile(test_user_id)

def check_date_calculation():
    """Check date calculation accuracy"""
    from validators import calculate_target_end_date
    from datetime import datetime, timedelta
    
    print("🔧 Investigating date calculation issue...")
    
    weeks = 12
    calculated = calculate_target_end_date(weeks)
    print(f"Calculated end date for {weeks} weeks: {calculated}")
    
    # Expected date
    expected = datetime.now() + timedelta(weeks=weeks)
    print(f"Expected date: {expected.strftime('%Y-%m-%d')}")
    
    # Check difference
    calc_date = datetime.strptime(calculated, '%Y-%m-%d')
    diff_days = abs((calc_date - expected).days)
    print(f"Difference: {diff_days} days")
    
    if diff_days > 1:
        print("❌ Date calculation is off by more than 1 day")
        print("This could be due to timezone or calculation method")
    else:
        print("✅ Date calculation is within acceptable range")

if __name__ == "__main__":
    print("🧪 Investigating Regression Issues")
    print("=" * 50)
    
    fix_constraints_field_issue()
    print()
    check_date_calculation()