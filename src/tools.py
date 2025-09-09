import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any


class CommerceTools:
    def __init__(self):
        self.products = self._load_products()
        self.orders = self._load_orders()
    
    def _load_products(self) -> List[Dict]:
        """Load products from JSON file"""
        try:
            with open('data/products.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback for testing
            return [
                {"id":"P1","title":"Midi Wrap Dress","price":119,"tags":["wedding","midi"],"sizes":["S","M","L"],"color":"Charcoal"},
                {"id":"P2","title":"Satin Slip Dress","price":99,"tags":["wedding","midi"],"sizes":["XS","S","M"],"color":"Blush"},
                {"id":"P3","title":"Knit Bodycon","price":89,"tags":["midi"],"sizes":["M","L"],"color":"Navy"},
                {"id":"P4","title":"A-Line Day Dress","price":75,"tags":["daywear","midi"],"sizes":["S","M","L"],"color":"Olive"},
                {"id":"P5","title":"Sequin Party Dress","price":149,"tags":["party"],"sizes":["S","M"],"color":"Black"}
            ]
    
    def _load_orders(self) -> List[Dict]:
        """Load orders from JSON file"""
        try:
            with open('data/orders.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback for testing
            return [
                {"order_id":"A1001","email":"rehan@example.com","created_at":"2025-09-07T09:30:00Z","items":[{"id":"P1","size":"M"}]},
                {"order_id":"A1002","email":"alex@example.com","created_at":"2025-09-06T13:05:00Z","items":[{"id":"P2","size":"S"}]},
                {"order_id":"A1003","email":"mira@example.com","created_at":"2025-09-07T11:55:00Z","items":[{"id":"P3","size":"L"}]}
            ]


    def product_search(self, query: str = "", price_max: int = 1000, tags: List[str] = None) -> List[Dict]:
        """Search products by query, price, and tags - return max 2 results"""
        if tags is None:
            tags = []
        
        results = []
        query_lower = query.lower()
        
        for product in self.products:
            # Price filter - strict requirement
            if product['price'] > price_max:
                continue
            
            # Tag filter (if any tags specified, at least one must match)
            if tags and not any(tag in product['tags'] for tag in tags):
                continue
            
            # Query filter (search in title and tags)
            if query and not (
                query_lower in product['title'].lower() or 
                any(query_lower in tag.lower() for tag in product['tags'])
            ):
                continue
            
            results.append(product)
        
        # Return max 2 results, sorted by price (requirement)
        return sorted(results, key=lambda x: x['price'])[:2]
    
    def size_recommender(self, user_inputs: str) -> str:
        """Provide size recommendation based on user preferences"""
        user_lower = user_inputs.lower()
        
        if any(word in user_lower for word in ['fitted', 'tight', 'small', 'petite']):
            return "I'd recommend size M for a more fitted look"
        elif any(word in user_lower for word in ['loose', 'comfortable', 'roomy', 'large']):
            return "I'd recommend size L for a more comfortable fit"
        elif 'between m/l' in user_lower or 'between m and l' in user_lower:
            return "For M vs L: choose M if you prefer fitted style, L if you want more room and comfort"
        else:
            return "I'd recommend size M as a good middle ground, but L if you prefer looser fits"
    
    def eta(self, zip_code: str) -> str:
        """Calculate ETA based on zip code - rule-based"""
        # Extract numbers from zip code
        zip_digits = ''.join(filter(str.isdigit, str(zip_code)))
        
        if not zip_digits:
            return "3-4 business days"  # Default
        
        zip_int = int(zip_digits[:6].ljust(6, '0'))  # Pad with zeros if needed
        
        # Simple rule-based ETA
        if zip_int < 400000:  # Northern regions
            return "3-4 business days"
        elif zip_int < 600000:  # Central regions  
            return "2-3 business days"
        else:  # Southern regions
            return "4-5 business days"
    
    def order_lookup(self, order_id: str, email: str) -> Optional[Dict]:
        """Look up order by ID and email - secure lookup"""
        for order in self.orders:
            if order['order_id'] == order_id and order['email'] == email:
                return order
        return None
    
    def order_cancel(self, order_id: str, email: str, current_time: str = None) -> Dict:
        """Cancel order with 60-minute policy enforcement"""
        if current_time is None:
            current_time = os.getenv("CURRENT_TIME", "2025-09-08T11:05:00Z")
        
        # Look up order first
        order = self.order_lookup(order_id, email)
        if not order:
            return {
                "success": False,
                "reason": "order_not_found",
                "message": "Order not found with provided ID and email"
            }
        
        # Check 60-minute policy with timezone awareness
        created_at = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        time_diff_minutes = (current_dt - created_at).total_seconds() / 60
        
        if time_diff_minutes <= 60:  # Allow cancellation at exactly 60 minutes per requirements
            return {
                "success": True,
                "reason": "within_policy",
                "message": f"Order {order_id} cancelled successfully. Refund will process in 3-5 business days.",
                "time_diff_minutes": round(time_diff_minutes, 1)
            }
        else:
            return {
                "success": False,
                "reason": "policy_violation", 
                "message": f"Order was placed {round(time_diff_minutes/60, 1)} hours ago, beyond our 60-minute cancellation window.",
                "time_diff_minutes": round(time_diff_minutes, 1),
                "alternatives": [
                    "Update shipping address",
                    "Convert to store credit", 
                    "Connect with customer support"
                ]
            }


# Global instance
commerce_tools = CommerceTools()
