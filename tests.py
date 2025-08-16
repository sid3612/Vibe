"""
Regression tests for Job Funnel Coach Telegram Bot
"""
import unittest
from unittest.mock import Mock, patch
import asyncio
from datetime import datetime

# Import our modules
from db import init_db, add_user, add_channel, get_user_channels, add_week_data, get_user_history
from metrics import calculate_cvr_metrics, format_history_table
from export import generate_csv_export

class TestBotFunctionality(unittest.TestCase):
    """Test core bot functionality"""
    
    def setUp(self):
        """Set up test database"""
        init_db()
        # Test user
        self.test_user_id = 999999
        add_user(self.test_user_id, "test_user")
    
    def test_channel_management(self):
        """Test adding and retrieving channels"""
        # Test adding channel
        result = add_channel(self.test_user_id, "LinkedIn")
        self.assertTrue(result)
        
        # Test duplicate channel
        result = add_channel(self.test_user_id, "LinkedIn")
        self.assertFalse(result)
        
        # Test retrieving channels
        channels = get_user_channels(self.test_user_id)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0], "LinkedIn")
    
    def test_week_data_input(self):
        """Test adding and retrieving week data"""
        add_channel(self.test_user_id, "LinkedIn")
        
        # Test active funnel data
        week_data = {
            'applications': 10,
            'responses': 3,
            'screenings': 2,
            'onsites': 1,
            'offers': 1,
            'rejections': 0
        }
        
        week_start = "2025-08-11"
        add_week_data(self.test_user_id, week_start, "LinkedIn", "active", week_data)
        
        # Verify data was added
        history = get_user_history(self.test_user_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['applications'], 10)
        self.assertEqual(history[0]['responses'], 3)
    
    def test_cvr_calculations(self):
        """Test CVR metrics calculations"""
        # Test active funnel CVR
        active_data = {
            'applications': 10,
            'responses': 3,
            'screenings': 2,
            'onsites': 1,
            'offers': 1
        }
        
        metrics = calculate_cvr_metrics(active_data, 'active')
        self.assertEqual(metrics['cvr1'], '30%')  # 3/10
        self.assertEqual(metrics['cvr2'], '67%')  # 2/3
        self.assertEqual(metrics['cvr3'], '50%')  # 1/2
        self.assertEqual(metrics['cvr4'], '100%') # 1/1
        
        # Test division by zero
        zero_data = {'applications': 0, 'responses': 0, 'screenings': 0, 'onsites': 0, 'offers': 0}
        metrics = calculate_cvr_metrics(zero_data, 'active')
        self.assertEqual(metrics['cvr1'], '—')
    
    def test_csv_export(self):
        """Test CSV export functionality"""
        add_channel(self.test_user_id, "LinkedIn")
        
        week_data = {
            'applications': 10,
            'responses': 3,
            'screenings': 2,
            'onsites': 1,
            'offers': 1,
            'rejections': 0
        }
        
        add_week_data(self.test_user_id, "2025-08-11", "LinkedIn", "active", week_data)
        
        csv_content = generate_csv_export(self.test_user_id)
        self.assertIsNotNone(csv_content)
        self.assertTrue(csv_content.startswith('\ufeff'))  # UTF-8 BOM check
        self.assertIn('LinkedIn', csv_content)
        self.assertIn('2025-08-11', csv_content)
    
    def test_history_table_formatting(self):
        """Test history table formatting doesn't break"""
        add_channel(self.test_user_id, "LinkedIn")
        
        week_data = {
            'applications': 10,
            'responses': 3,
            'screenings': 2,
            'onsites': 1,
            'offers': 1,
            'rejections': 0
        }
        
        add_week_data(self.test_user_id, "2025-08-11", "LinkedIn", "active", week_data)
        history = get_user_history(self.test_user_id)
        
        table = format_history_table(history, 'active')
        self.assertIsNotNone(table)
        self.assertIn('LinkedIn', table)
        # Check that CVR4 column doesn't overflow (expanded to 80 chars)
        lines = table.split('\n')
        for line in lines:
            if 'LinkedIn' in line:
                self.assertLessEqual(len(line), 80)  # Reasonable line length
                
    def test_passive_funnel_functionality(self):
        """Test passive funnel data handling"""
        add_channel(self.test_user_id, "HH.ru")
        
        # Test passive funnel data
        week_data = {
            'views': 50,
            'incoming': 5,
            'screenings': 3,
            'onsites': 2,
            'offers': 1,
            'rejections': 1
        }
        
        add_week_data(self.test_user_id, "2025-08-11", "HH.ru", "passive", week_data)
        
        # Verify data was added
        history = get_user_history(self.test_user_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['views'], 50)
        self.assertEqual(history[0]['incoming'], 5)
        
        # Test passive CVR calculations
        metrics = calculate_cvr_metrics(week_data, 'passive')
        self.assertEqual(metrics['cvr1'], '10%')  # 5/50
        self.assertEqual(metrics['cvr2'], '60%')  # 3/5
    
    def test_improved_prompts_integration(self):
        """Test that improved prompts don't break functionality"""
        # This test ensures the new clearer field names don't affect data storage
        add_channel(self.test_user_id, "TestChannel")
        
        # Simulate step-by-step input with new prompts
        week_data = {
            'applications': 15,  # количество подач резюме (Applications)
            'responses': 8,      # количество ответов от компаний (Responses)
            'screenings': 5,     # количество первичных звонков/скринингов (Screenings)
            'onsites': 3,        # количество основных интервью (Onsites)
            'offers': 2,         # количество полученных офферов (Offers)
            'rejections': 1      # количество отказов (Rejections)
        }
        
        add_week_data(self.test_user_id, "2025-08-16", "TestChannel", "active", week_data)
        
        # Verify data is stored correctly despite prompt changes
        history = get_user_history(self.test_user_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['applications'], 15)
        self.assertEqual(history[0]['responses'], 8)
        self.assertEqual(history[0]['screenings'], 5)
        self.assertEqual(history[0]['onsites'], 3)
        self.assertEqual(history[0]['offers'], 2)
        self.assertEqual(history[0]['rejections'], 1)

if __name__ == '__main__':
    unittest.main()