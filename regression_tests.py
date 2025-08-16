#!/usr/bin/env python3
"""
Complete regression testing for reflection system and state management
"""

import sys
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

def test_state_flow():
    """Test complete state flow for 5-step wizard"""
    print("🔍 DEBUGGING STATE FLOW")
    print("=" * 50)
    
    # Test scenario
    print("📝 Testing scenario:")
    print("   1. User enters Applications: 1")
    print("   2. User enters Responses: 1") 
    print("   3. User enters Screenings: 0")
    print("   4. User enters Onsites: 0")
    print("   5. User enters Offers: 0")
    print("   6. User enters Rejections: 1")
    print("   EXPECTED: Reflection prompt appears")
    print("   ACTUAL: '❌ Введите число' appears")
    print()
    
    # Check which handlers exist
    try:
        from main import dp
        print("📊 Registered handlers:")
        
        # Get handlers by state
        handlers = dp._get_effective_handlers()
        for i, handler in enumerate(handlers[:10]):  # Show first 10
            print(f"   {i+1}. {handler}")
            
    except Exception as e:
        print(f"   ❌ Could not analyze handlers: {e}")
    
    return False  # Always return False to indicate manual investigation needed

def check_state_conflicts():
    """Check for potential state conflicts"""
    print("\n🔍 CHECKING FOR STATE CONFLICTS")
    print("=" * 50)
    
    # Check if there are any handlers that catch all text messages
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Look for problematic handlers
    problematic_patterns = [
        '@dp.message(F.text)',  # Catches all text
        '@dp.message()',        # Catches all messages
        'StateFilter(None)',    # Catches messages with no state
    ]
    
    found_issues = []
    for pattern in problematic_patterns:
        if pattern in content:
            found_issues.append(pattern)
    
    if found_issues:
        print("⚠️  POTENTIAL ISSUES FOUND:")
        for issue in found_issues:
            print(f"   - {issue}")
    else:
        print("✅ No obvious handler conflicts found")
    
    # Check for handlers without proper state filters
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '@dp.message(' in line and 'FunnelStates.' not in line and 'ProfileStates.' not in line:
            if 'F.text' in line or line.strip() == '@dp.message()':
                print(f"🚨 Line {i+1}: {line.strip()}")
                print("   ^ This handler might catch messages after state.clear()")
    
    return len(found_issues) == 0

def suggest_fix():
    """Suggest fix for the issue"""
    print("\n🛠️  SUGGESTED FIX")
    print("=" * 50)
    
    print("PROBLEM: After state.clear(), any text message triggers a handler")
    print("         that responds with '❌ Введите число'")
    print()
    print("SOLUTION: Add proper state filtering to ALL message handlers")
    print("          Ensure no handler catches text messages without state")
    print()
    print("STEPS:")
    print("1. Find handler that responds '❌ Введите число' to text input")
    print("2. Add proper StateFilter to prevent it from triggering")
    print("3. Test complete flow: wizard → save → reflection prompt")
    
if __name__ == "__main__":
    print("🧪 COMPLETE REGRESSION TEST")
    print("=" * 60)
    
    test_passed = test_state_flow()
    conflicts_ok = check_state_conflicts()
    
    suggest_fix()
    
    if not test_passed or not conflicts_ok:
        print("\n❌ TESTS FAILED - Manual investigation required")
        print("📍 Focus on handlers that catch text messages after state.clear()")
    else:
        print("\n✅ ALL TESTS PASSED")