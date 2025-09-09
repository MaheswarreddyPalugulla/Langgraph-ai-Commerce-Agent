import unittest
from datetime import datetime, timedelta
from src.tools import CommerceTools

class TestOrderCancellationPolicy(unittest.TestCase):
    def setUp(self):
        self.tools = CommerceTools()
        self.order_id = "A1003"
        self.email = "mira@example.com"
        self.base_time = "2025-09-07T11:55:00Z"

    def test_edge_cases(self):
        """Test edge cases for the 60-minute cancellation policy"""
        print("\n🧪 Testing 60-minute policy edge cases...")
        
        # Test case 1: At 59 minutes (should allow)
        current_time = (datetime.fromisoformat(self.base_time.replace('Z', '+00:00')) + 
                       timedelta(minutes=59)).strftime('%Y-%m-%dT%H:%M:%SZ')
        result = self.tools.order_cancel(self.order_id, self.email, current_time)
        self.assertTrue(result['success'], "Should allow cancellation at 59 minutes")
        print("✅ 59 minutes: Allowed (correct)")

        # Test case 2: At exactly 60 minutes (should allow per requirements)
        current_time = (datetime.fromisoformat(self.base_time.replace('Z', '+00:00')) + 
                       timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        result = self.tools.order_cancel(self.order_id, self.email, current_time)
        self.assertTrue(result['success'], "Should allow cancellation at exactly 60 minutes")
        print("✅ 60 minutes: Allowed (correct)")

        # Test case 3: At 61 minutes (should block)
        current_time = (datetime.fromisoformat(self.base_time.replace('Z', '+00:00')) + 
                       timedelta(minutes=61)).strftime('%Y-%m-%dT%H:%M:%SZ')
        result = self.tools.order_cancel(self.order_id, self.email, current_time)
        self.assertFalse(result['success'], "Should block cancellation at 61 minutes")
        print("✅ 61 minutes: Blocked (correct)")

if __name__ == '__main__':
    unittest.main()
