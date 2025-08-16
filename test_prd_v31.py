#!/usr/bin/env python3
"""
Test suite for PRD v3.1 reflection forms implementation
Tests the simplified single-form reflection system
"""

import sqlite3
import asyncio
from unittest.mock import Mock, AsyncMock
from reflection_v31 import ReflectionV31System
from db import init_db, get_db_connection

def test_database_setup():
    """Test that the event_feedback table is created correctly"""
    print("Testing database setup...")
    
    # Initialize database
    init_db()
    
    # Check if event_feedback table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='event_feedback'
    """)
    result = cursor.fetchone()
    
    assert result is not None, "event_feedback table should exist"
    print("✅ Database setup test passed")
    
    # Check table structure
    cursor.execute("PRAGMA table_info(event_feedback)")
    columns = cursor.fetchall()
    
    expected_columns = [
        'id', 'user_id', 'funnel_type', 'channel', 'week_start',
        'section_stage', 'events_count', 'rating_overall', 'strengths',
        'weaknesses', 'rating_mood', 'reject_after_stage',
        'reject_reasons_json', 'reject_reason_other', 'created_at'
    ]
    
    column_names = [col['name'] for col in columns]
    for expected_col in expected_columns:
        assert expected_col in column_names, f"Column {expected_col} should exist"
    
    print("✅ Table structure test passed")
    conn.close()

def test_trigger_logic():
    """Test reflection trigger logic according to PRD v3.1"""
    print("Testing trigger logic...")
    
    # Test case 1: No changes should not trigger
    old_data = {'responses': 5, 'screenings': 3, 'onsites': 2, 'offers': 1, 'rejections': 4}
    new_data = {'responses': 5, 'screenings': 3, 'onsites': 2, 'offers': 1, 'rejections': 4}
    
    sections = ReflectionV31System.check_reflection_trigger(
        user_id=123, week_start='2025-01-20', channel='LinkedIn', 
        funnel_type='active', old_data=old_data, new_data=new_data
    )
    
    assert len(sections) == 0, "No changes should not trigger reflection"
    print("✅ No trigger test passed")
    
    # Test case 2: Increase in responses should trigger
    new_data_with_responses = old_data.copy()
    new_data_with_responses['responses'] = 7  # +2 increase
    
    sections = ReflectionV31System.check_reflection_trigger(
        user_id=123, week_start='2025-01-20', channel='LinkedIn',
        funnel_type='active', old_data=old_data, new_data=new_data_with_responses
    )
    
    assert len(sections) == 1, "Increase in responses should trigger reflection"
    assert sections[0]['stage'] == 'response', "Should trigger response stage"
    assert sections[0]['delta'] == 2, "Delta should be 2"
    print("✅ Response trigger test passed")
    
    # Test case 3: Multiple increases should create multiple sections
    new_data_multiple = old_data.copy()
    new_data_multiple['responses'] = 7  # +2
    new_data_multiple['offers'] = 3     # +2
    new_data_multiple['rejections'] = 6 # +2
    
    sections = ReflectionV31System.check_reflection_trigger(
        user_id=123, week_start='2025-01-20', channel='LinkedIn',
        funnel_type='active', old_data=old_data, new_data=new_data_multiple
    )
    
    assert len(sections) == 3, "Multiple increases should create multiple sections"
    stages = [s['stage'] for s in sections]
    assert 'response' in stages, "Should include response stage"
    assert 'offer' in stages, "Should include offer stage"
    assert 'reject_no_interview' in stages, "Should include rejection stage"
    print("✅ Multiple trigger test passed")
    
    # Test case 4: CVR fields (applications, views) should NOT trigger
    new_data_applications = old_data.copy()
    new_data_applications['applications'] = 10  # This should NOT trigger
    
    sections = ReflectionV31System.check_reflection_trigger(
        user_id=123, week_start='2025-01-20', channel='LinkedIn',
        funnel_type='active', old_data=old_data, new_data=new_data_applications
    )
    
    assert len(sections) == 0, "Applications increase should NOT trigger reflection"
    print("✅ CVR exclusion test passed")

def test_data_saving():
    """Test saving reflection data to database"""
    print("Testing data saving...")
    
    # Initialize database
    init_db()
    
    # Test data
    user_id = 123
    week_start = '2025-01-20'
    channel = 'LinkedIn'
    funnel_type = 'active'
    
    sections = [
        {
            'stage': 'response',
            'delta': 2,
            'stage_display': '✉️ Ответ'
        },
        {
            'stage': 'offer',
            'delta': 1,
            'stage_display': '🏁 Оффер'
        }
    ]
    
    form_data = {
        'section_response': {
            'rating_overall': 4,
            'strengths': 'Good communication',
            'weaknesses': 'Need more technical depth',
            'rating_mood': 3
        },
        'section_offer': {
            'rating_overall': 5,
            'strengths': 'Perfect fit',
            'weaknesses': None,
            'rating_mood': 5
        }
    }
    
    # Save data
    success = ReflectionV31System.save_reflection_data(
        user_id, week_start, channel, funnel_type, sections, form_data
    )
    
    assert success, "Data saving should succeed"
    print("✅ Data saving success test passed")
    
    # Verify data was saved correctly
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM event_feedback 
        WHERE user_id = ? AND week_start = ? AND channel = ?
    """, (user_id, week_start, channel))
    
    records = cursor.fetchall()
    assert len(records) == 2, "Should have 2 records (one per section)"
    
    # Check first record (response)
    response_record = next(r for r in records if r['section_stage'] == 'response')
    assert response_record['events_count'] == 2, "Events count should be 2"
    assert response_record['rating_overall'] == 4, "Rating should be 4"
    assert response_record['strengths'] == 'Good communication', "Strengths should match"
    
    # Check second record (offer)
    offer_record = next(r for r in records if r['section_stage'] == 'offer')
    assert offer_record['events_count'] == 1, "Events count should be 1"
    assert offer_record['rating_overall'] == 5, "Rating should be 5"
    assert offer_record['strengths'] == 'Perfect fit', "Strengths should match"
    
    print("✅ Data verification test passed")
    conn.close()

def test_display_functions():
    """Test stage display functions"""
    print("Testing display functions...")
    
    test_cases = [
        ('response', '✉️ Ответ'),
        ('screening', '📞 Скрининг'),
        ('onsite', '🧑‍💼 Онсайт'),
        ('offer', '🏁 Оффер'),
        ('reject_no_interview', '❌ Реджект без интервью'),
        ('reject_after_interview', '❌❌ Реджект после интервью')
    ]
    
    for stage, expected_display in test_cases:
        display = ReflectionV31System.get_stage_display(stage)
        assert display == expected_display, f"Stage {stage} should display as {expected_display}"
    
    print("✅ Display functions test passed")

async def test_keyboards():
    """Test keyboard generation functions"""
    print("Testing keyboard functions...")
    
    # Test rating keyboard
    rating_keyboard = ReflectionV31System.get_rating_keyboard()
    assert len(rating_keyboard.inline_keyboard) == 1, "Should have 1 row"
    assert len(rating_keyboard.inline_keyboard[0]) == 5, "Should have 5 buttons"
    
    button_texts = [btn.text for btn in rating_keyboard.inline_keyboard[0]]
    expected_texts = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    assert button_texts == expected_texts, "Rating buttons should be numbered 1-5"
    print("✅ Rating keyboard test passed")
    
    # Test rejection reasons keyboard
    rejection_keyboard = ReflectionV31System.get_rejection_reasons_keyboard()
    assert len(rejection_keyboard.inline_keyboard) == 9, "Should have 8 reason rows + 1 done button"
    
    # Check that last button is "Готово"
    done_button = rejection_keyboard.inline_keyboard[-1][0]
    assert done_button.text == "Готово", "Last button should be 'Готово'"
    assert done_button.callback_data == "reasons_v31_done", "Done button should have correct callback"
    print("✅ Rejection keyboard test passed")

def run_all_tests():
    """Run all tests"""
    print("🧪 Starting PRD v3.1 Tests\n")
    
    try:
        test_database_setup()
        test_trigger_logic()
        test_data_saving()
        test_display_functions()
        asyncio.run(test_keyboards())
        
        print("\n🎉 All PRD v3.1 tests passed successfully!")
        print("\n📋 PRD v3.1 Implementation Summary:")
        print("✅ Event feedback database table created")
        print("✅ Trigger logic: Only responses, screenings, onsites, offers, rejections")
        print("✅ CVR fields (applications, views) excluded from triggers")
        print("✅ Single combined form with multiple sections")
        print("✅ Data saving and retrieval working correctly")
        print("✅ All UI components (keyboards) functioning")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_all_tests()