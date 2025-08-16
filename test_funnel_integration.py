#!/usr/bin/env python3
"""
Test script for funnel type integration in profile creation
"""

import sys
import os
sys.path.append('.')

from db import init_db, save_profile, get_profile, get_user_funnels
from profile import format_profile_display

def test_funnel_integration():
    """Test the complete funnel type integration"""
    print("🧪 Testing Funnel Type Integration...")
    
    # Initialize database
    init_db()
    
    # Test user ID
    test_user_id = 999999999
    
    # Test profile with funnel type
    test_profile = {
        'role': 'Product Manager',
        'current_location': 'Berlin, Germany',
        'target_location': 'Remote EU',
        'level': 'Senior',
        'deadline_weeks': 12,
        'target_end_date': '2025-11-16',
        'preferred_funnel_type': 'passive'
    }
    
    print("1. Testing profile save with funnel type...")
    try:
        result = save_profile(test_user_id, test_profile)
        if result:
            print("✅ Profile saved successfully")
        else:
            print("❌ Failed to save profile")
            return False
    except Exception as e:
        print(f"❌ Error saving profile: {e}")
        return False
    
    print("2. Testing profile retrieval...")
    retrieved_profile = get_profile(test_user_id)
    if retrieved_profile:
        print("✅ Profile retrieved successfully")
        print(f"   Funnel type: {retrieved_profile.get('preferred_funnel_type', 'not found')}")
    else:
        print("❌ Failed to retrieve profile")
        return False
    
    print("3. Testing user funnels with profile priority...")
    user_funnels = get_user_funnels(test_user_id)
    active_funnel = user_funnels.get('active_funnel', 'not found')
    print(f"   Active funnel from profile: {active_funnel}")
    
    if active_funnel == 'passive':
        print("✅ Profile funnel preference correctly applied")
    else:
        print("❌ Profile funnel preference not applied correctly")
        return False
    
    print("4. Testing profile display formatting...")
    display_text = format_profile_display(retrieved_profile)
    if "👀 Пассивный поиск" in display_text:
        print("✅ Funnel type correctly displayed in profile")
    else:
        print("❌ Funnel type not displayed correctly")
        print("Display text:", display_text[:200], "...")
        return False
    
    print("\n🎉 All integration tests passed!")
    return True

if __name__ == "__main__":
    success = test_funnel_integration()
    sys.exit(0 if success else 1)