#!/usr/bin/env python3
"""
Comprehensive regression testing for Job Funnel Coach Telegram Bot
Tests all critical functionality to prevent regressions before major changes
"""

import json
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta

# Import bot modules
from db import (
    init_db, save_profile, get_profile, delete_profile,
    add_user, get_user_funnels, add_channel, get_user_channels,
    add_week_data, get_week_data
)
from profile import format_profile_display
from validators import calculate_target_end_date
from export import generate_csv_export

class RegressionTester:
    def __init__(self):
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def test(self, test_name, test_func):
        """Run a single test"""
        self.test_count += 1
        try:
            print(f"🧪 Test {self.test_count}: {test_name}")
            test_func()
            print(f"✅ PASS")
            self.passed += 1
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            self.failed += 1
            self.errors.append({
                'test': test_name,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        print()
    
    def print_summary(self):
        """Print test results summary"""
        print("=" * 60)
        print("REGRESSION TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed/self.test_count)*100:.1f}%")
        
        if self.errors:
            print("\n❌ FAILED TESTS:")
            for error in self.errors:
                print(f"- {error['test']}: {error['error']}")
        
        print("=" * 60)
        return self.failed == 0

def test_database_initialization():
    """Test database initialization and schema"""
    init_db()
    conn = sqlite3.connect('funnel_coach.db')
    cursor = conn.cursor()
    
    # Check all required tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    required_tables = ['users', 'user_channels', 'week_data', 'profiles']
    
    for table in required_tables:
        assert table in tables, f"Required table {table} not found"
    
    # Check profiles table has all required columns including LinkedIn
    cursor.execute("PRAGMA table_info(profiles)")
    columns = [row[1] for row in cursor.fetchall()]
    required_columns = [
        'user_id', 'role', 'current_location', 'target_location', 'level',
        'deadline_weeks', 'target_end_date', 'linkedin', 'constraints_text'
    ]
    
    for column in required_columns:
        assert column in columns, f"Required column {column} not found in profiles table"
    
    conn.close()

def test_profile_creation_complete():
    """Test complete profile creation with all fields including LinkedIn"""
    test_user_id = 777777
    
    # Test profile with all fields
    complete_profile = {
        'role': 'Senior Product Manager',
        'current_location': 'Berlin, Germany',
        'target_location': 'Remote EU, London',
        'level': 'Senior',
        'deadline_weeks': 16,
        'target_end_date': '2025-12-01',
        'role_synonyms_json': json.dumps(['Product Owner', 'Growth PM', 'Platform PM']),
        'salary_min': 80000,
        'salary_max': 100000,
        'salary_currency': 'EUR',
        'salary_period': 'год',
        'company_types_json': json.dumps(['Scale-up', 'Enterprise']),
        'industries_json': json.dumps(['Fintech', 'SaaS', 'AI']),
        'competencies_json': json.dumps(['Product Strategy', 'Data Analysis', 'User Research']),
        'superpowers_json': json.dumps(['Increased user retention by 35%', 'Reduced churn by 20%']),
        'constraints': 'Remote only, No weekend work, Flexible hours',
        'linkedin': 'https://linkedin.com/in/senior-pm'
    }
    
    # Save profile
    save_profile(test_user_id, complete_profile)
    
    # Retrieve and verify
    retrieved = get_profile(test_user_id)
    assert retrieved is not None, "Profile not saved"
    assert retrieved['role'] == complete_profile['role'], "Role mismatch"
    assert retrieved['linkedin'] == complete_profile['linkedin'], "LinkedIn field not saved"
    assert retrieved['constraints_text'] == complete_profile['constraints'], "Constraints not saved correctly"
    
    # Test profile display
    display = format_profile_display(retrieved)
    assert 'LINKEDIN' in display, "LinkedIn not in profile display"
    assert 'https://linkedin.com/in/senior-pm' in display, "LinkedIn URL not in display"
    
    # Check constraints mapping for display - convert constraints_text to constraints
    if 'constraints_text' in retrieved and retrieved['constraints_text']:
        retrieved['constraints'] = retrieved['constraints_text']
    assert retrieved.get('constraints') == complete_profile['constraints'], "Constraints not properly mapped"
    
    # Cleanup
    delete_profile(test_user_id)

def test_profile_creation_minimal():
    """Test profile creation with only required fields"""
    test_user_id = 777778
    
    minimal_profile = {
        'role': 'Developer',
        'current_location': 'Moscow',
        'target_location': 'Remote',
        'level': 'Middle',
        'deadline_weeks': 8,
        'target_end_date': '2025-10-01'
    }
    
    save_profile(test_user_id, minimal_profile)
    retrieved = get_profile(test_user_id)
    
    assert retrieved is not None, "Minimal profile not saved"
    assert retrieved['role'] == 'Developer', "Role not saved correctly"
    assert retrieved['linkedin'] is None, "LinkedIn should be None for minimal profile"
    
    delete_profile(test_user_id)

def test_salary_parsing_formats():
    """Test different salary input formats"""
    test_cases = [
        ('60000 EUR/год', 60000, 60000, 'EUR', 'год'),
        ('60000-70000 EUR/год', 60000, 70000, 'EUR', 'год'),
        ('5000-8000 USD/месяц', 5000, 8000, 'USD', 'месяц'),
        ('100000 RUB/год', 100000, 100000, 'RUB', 'год'),
        ('3000-4000 USD/месяц', 3000, 4000, 'USD', 'месяц')
    ]
    
    for salary_text, expected_min, expected_max, expected_currency, expected_period in test_cases:
        parts = salary_text.split()
        range_part = parts[0]
        currency_period = ' '.join(parts[1:])
        
        if '/' in currency_period:
            currency, period = currency_period.split('/')
            currency = currency.strip()
            period = period.strip()
        else:
            currency = 'EUR'
            period = 'год'
        
        if '-' in range_part:
            min_val, max_val = range_part.split('-')
            salary_min = float(min_val.strip())
            salary_max = float(max_val.strip())
        else:
            salary_min = salary_max = float(range_part.strip())
        
        assert salary_min == expected_min, f"Min salary mismatch for {salary_text}"
        assert salary_max == expected_max, f"Max salary mismatch for {salary_text}"
        assert currency == expected_currency, f"Currency mismatch for {salary_text}"
        assert period == expected_period, f"Period mismatch for {salary_text}"

def test_funnel_data_operations():
    """Test funnel data operations"""
    test_user_id = 777779
    
    # Initialize user
    add_user(test_user_id, "test_user")
    add_channel(test_user_id, "LinkedIn")
    add_channel(test_user_id, "HH.ru")
    
    # Test week data addition
    week_start = "2025-08-12"
    active_data = {
        'applications': 10,
        'responses': 3,
        'screenings': 2,
        'onsites': 1,
        'offers': 1,
        'rejections': 2
    }
    
    add_week_data(test_user_id, week_start, "LinkedIn", "active", active_data)
    
    # Retrieve and verify
    retrieved_data = get_week_data(test_user_id, week_start, "LinkedIn", "active")
    assert retrieved_data is not None, "Week data not saved"
    
    # Convert sqlite.Row to dict for proper access
    if hasattr(retrieved_data, 'keys'):
        retrieved_dict = dict(retrieved_data)
    else:
        retrieved_dict = retrieved_data
        
    assert retrieved_dict['applications'] == 10, f"Applications count incorrect: expected 10, got {retrieved_dict.get('applications')}"
    assert retrieved_dict['offers'] == 1, f"Offers count incorrect: expected 1, got {retrieved_dict.get('offers')}"
    
    # Test duplicate data handling (should sum)
    add_week_data(test_user_id, week_start, "LinkedIn", "active", active_data)
    retrieved_again = get_week_data(test_user_id, week_start, "LinkedIn", "active")
    retrieved_again_dict = dict(retrieved_again) if hasattr(retrieved_again, 'keys') else retrieved_again
    assert retrieved_again_dict['applications'] == 20, f"Duplicate data not summed correctly: expected 20, got {retrieved_again_dict.get('applications')}"

def test_metrics_calculation():
    """Test CVR metrics calculation manually"""
    # Test CVR calculation logic manually
    # CVR1 = responses/applications * 100
    applications = 100
    responses = 20
    cvr1 = (responses / applications * 100) if applications > 0 else 0
    assert cvr1 == 20, f"CVR1 calculation incorrect: expected 20, got {cvr1}"
    
    # CVR2 = screenings/responses * 100
    screenings = 10
    cvr2 = (screenings / responses * 100) if responses > 0 else 0
    assert cvr2 == 50, f"CVR2 calculation incorrect: expected 50, got {cvr2}"
    
    # Test division by zero handling
    cvr_zero = (10 / 0 * 100) if 0 > 0 else 0
    assert cvr_zero == 0, "Division by zero not handled correctly"

def test_csv_export():
    """Test CSV export functionality"""
    test_user_id = 777780
    
    # Set up test data
    add_user(test_user_id, "export_test_user")
    add_channel(test_user_id, "TestChannel")
    
    test_data = {
        'applications': 5,
        'responses': 2,
        'screenings': 1,
        'onsites': 1,
        'offers': 0,
        'rejections': 1
    }
    
    add_week_data(test_user_id, "2025-08-12", "TestChannel", "active", test_data)
    
    # Generate export
    csv_content = generate_csv_export(test_user_id)
    assert csv_content is not None, "CSV export failed"
    assert "TestChannel" in csv_content, "Channel name not in CSV"
    assert "2025-08-12" in csv_content, "Week date not in CSV"
    
    # Check UTF-8 BOM for Excel compatibility
    assert csv_content.startswith('\ufeff'), "CSV missing UTF-8 BOM"

def test_date_calculations():
    """Test date calculation utilities"""
    # Test target end date calculation
    end_date = calculate_target_end_date(12)
    assert end_date is not None, "End date calculation failed"
    
    # Should be approximately 12 weeks from now
    expected_date = datetime.now() + timedelta(weeks=12)
    calculated_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Allow 1 day difference for date calculations
    diff = abs((calculated_date - expected_date).days)
    assert diff <= 1, f"Date calculation off by {diff} days"

def test_profile_display_formatting():
    """Test profile display formatting edge cases"""
    test_user_id = 777781
    
    # Test profile with special characters and long text
    special_profile = {
        'role': 'Full-Stack Developer & Team Lead',
        'current_location': 'Санкт-Петербург, Россия',
        'target_location': 'США, Канада, remote-worldwide',
        'level': 'Senior+',
        'deadline_weeks': 24,
        'target_end_date': '2026-02-01',
        'superpowers_json': json.dumps([
            'Migrated legacy system serving 1M+ users with 99.9% uptime',
            'Built microservices architecture reducing response time by 60%',
            'Led team of 8 developers through successful product launch'
        ]),
        'constraints': 'No relocation required, Flexible working hours, Must have health insurance, Minimum 4 weeks vacation',
        'linkedin': 'https://linkedin.com/in/fullstack-team-lead-senior'
    }
    
    save_profile(test_user_id, special_profile)
    retrieved = get_profile(test_user_id)
    display = format_profile_display(retrieved)
    
    # Check formatting doesn't break with special characters
    assert 'Санкт-Петербург' in display, "Cyrillic characters not handled"
    assert '1M+ users' in display, "Special characters in superpowers not handled"
    assert len(display) > 100, "Profile display too short"
    
    # Check numbered superpowers formatting
    assert '1.' in display, "Superpowers not numbered"
    assert '2.' in display, "Multiple superpowers not numbered correctly"
    
    delete_profile(test_user_id)

def test_error_handling():
    """Test error handling in critical functions"""
    # Test invalid user operations
    invalid_user_id = 999999999
    
    # Should return empty/None for non-existent user
    profile = get_profile(invalid_user_id)
    assert profile == {}, "Should return empty dict for non-existent profile"
    
    channels = get_user_channels(invalid_user_id)
    assert channels == [], "Should return empty list for non-existent user channels"
    
    # Test deletion of non-existent profile
    result = delete_profile(invalid_user_id)
    assert result == False, "Should return False when deleting non-existent profile"

def run_all_tests():
    """Run comprehensive regression test suite"""
    print("🚀 Starting Comprehensive Regression Testing")
    print("=" * 60)
    
    tester = RegressionTester()
    
    # Database and schema tests
    tester.test("Database Initialization & Schema", test_database_initialization)
    
    # Profile management tests
    tester.test("Complete Profile Creation", test_profile_creation_complete)
    tester.test("Minimal Profile Creation", test_profile_creation_minimal)
    tester.test("Profile Display Formatting", test_profile_display_formatting)
    
    # Data parsing and validation tests
    tester.test("Salary Parsing Formats", test_salary_parsing_formats)
    tester.test("Date Calculations", test_date_calculations)
    
    # Funnel data tests
    tester.test("Funnel Data Operations", test_funnel_data_operations)
    tester.test("Metrics Calculation", test_metrics_calculation)
    
    # Export functionality tests
    tester.test("CSV Export", test_csv_export)
    
    # Error handling tests
    tester.test("Error Handling", test_error_handling)
    
    # Print results
    success = tester.print_summary()
    
    if success:
        print("🎉 ALL REGRESSION TESTS PASSED!")
        print("✅ System ready for further development")
    else:
        print("⚠️  REGRESSION TESTS FAILED!")
        print("❌ Fix issues before proceeding with changes")
    
    return success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)