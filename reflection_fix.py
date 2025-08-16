"""
Quick fix for reflection system integration
Run this to register reflection handlers and test the system
"""

from reflection_forms import ReflectionTrigger, ReflectionQueue
from db import init_db, get_db_connection
import sqlite3

def create_reflection_queue_table():
    """Create reflection_queue table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reflection_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            channel TEXT NOT NULL,
            funnel_type TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            form_data TEXT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Reflection queue table created")

def test_trigger_detection():
    """Test trigger detection logic"""
    old_data = {'responses': 5, 'screenings': 2, 'onsites': 1, 'offers': 0, 'rejections': 3}
    new_data = {'responses': 8, 'screenings': 4, 'onsites': 1, 'offers': 1, 'rejections': 3}
    
    triggers = ReflectionTrigger.check_triggers(
        user_id=123, 
        week_start='2025-01-13',
        channel='LinkedIn',
        funnel_type='active',
        old_data=old_data,
        new_data=new_data
    )
    
    print(f"✅ Triggers detected: {triggers}")
    return len(triggers) > 0

if __name__ == "__main__":
    init_db()
    create_reflection_queue_table()
    test_passed = test_trigger_detection()
    
    if test_passed:
        print("🎉 Reflection system ready!")
        print("📋 Next: Add data to trigger reflection forms")
    else:
        print("❌ Issue with trigger detection")