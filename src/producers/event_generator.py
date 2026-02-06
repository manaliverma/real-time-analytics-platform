"""
Realistic event generator for testing and data generation.

Generates realistic user behavior patterns including page views, clicks,
purchases, and other events with natural time distributions and properties.
"""

import random
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import uuid

from src.quality.schema import Event, EventType

logger = logging.getLogger(__name__)


class EventGenerator:
    """Base event generator."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed:
            random.seed(seed)
        
        self.user_ids = list(range(1, 10001))  # 10K users
        self.devices = ['mobile', 'desktop', 'tablet']
        self.geo_locations = [
            'US-CA', 'US-NY', 'US-TX', 'US-FL',
            'EU-UK', 'EU-DE', 'EU-FR', 'EU-IT',
            'ASIA-IN', 'ASIA-JP', 'ASIA-SG', 'ASIA-CN',
            'APAC-AU', 'APAC-NZ'
        ]
        self.sources = ['organic', 'paid', 'direct', 'referral']
        self.event_id_counter = 0
        self.session_map: Dict[int, str] = {}  # user_id -> session_id
        self.last_event_time = datetime.utcnow()
    
    def _get_or_create_session(self, user_id: int) -> str:
        """Get or create session ID for user."""
        if user_id not in self.session_map:
            self.session_map[user_id] = f"sess_{uuid.uuid4().hex[:8]}"
        return self.session_map[user_id]
    
    def _advance_time(self) -> None:
        """Advance event time by 1-100ms (realistic inter-event delay)."""
        self.last_event_time += timedelta(
            milliseconds=random.randint(1, 100)
        )
    
    def generate_page_view(self) -> Event:
        """Generate a page view event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.PAGE_VIEW.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'page_url': random.choice([
                    'https://example.com/home',
                    'https://example.com/products',
                    'https://example.com/category/electronics',
                    'https://example.com/product/laptop-123',
                    'https://example.com/checkout',
                    'https://example.com/account',
                ]),
                'referrer': random.choice([
                    'https://google.com',
                    'https://facebook.com',
                    None,
                    'https://twitter.com'
                ]),
                'time_on_page': random.randint(5, 600),  # seconds
                'scroll_depth': random.randint(0, 100),  # percentage
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_click(self) -> Event:
        """Generate a click event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.CLICK.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'element_id': f"btn_{random.randint(1, 1000)}",
                'element_class': random.choice(['cta', 'menu', 'social', 'nav', 'link']),
                'element_text': random.choice(['Buy Now', 'Add to Cart', 'Learn More', 'View Details']),
                'page_url': 'https://example.com/products',
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_add_to_cart(self) -> Event:
        """Generate an add to cart event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.ADD_TO_CART.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'product_id': f"prod_{random.randint(1, 10000):05d}",
                'product_name': random.choice([
                    'Laptop Pro', 'iPhone 15', 'iPad Air', 'AirPods Pro',
                    'Monitor 4K', 'Mechanical Keyboard', 'Gaming Mouse', 'Webcam'
                ]),
                'price': round(random.uniform(10, 2000), 2),
                'quantity': random.randint(1, 5),
                'category': random.choice(['Electronics', 'Accessories', 'Software']),
                'currency': 'USD',
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_purchase(self) -> Event:
        """Generate a purchase event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        # Purchases typically have multiple items
        items = [
            {
                'product_id': f"prod_{random.randint(1, 10000):05d}",
                'product_name': random.choice([
                    'Laptop Pro', 'iPhone 15', 'iPad Air', 'AirPods Pro',
                    'Monitor 4K', 'Mechanical Keyboard', 'Gaming Mouse'
                ]),
                'price': round(random.uniform(10, 2000), 2),
                'quantity': random.randint(1, 3),
            }
            for _ in range(random.randint(1, 3))
        ]
        
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.PURCHASE.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'order_id': f"ord_{random.randint(1000000, 9999999):07d}",
                'total_amount': round(total_amount, 2),
                'items': items,
                'items_count': len(items),
                'currency': 'USD',
                'payment_method': random.choice(['credit_card', 'paypal', 'apple_pay', 'google_pay']),
                'shipping_method': random.choice(['standard', 'express', 'overnight']),
                'coupon_applied': random.choice([True, False]),
                'discount_amount': round(random.uniform(0, total_amount * 0.2), 2),
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_search(self) -> Event:
        """Generate a search event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.SEARCH.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'query': random.choice([
                    'laptop', 'iphone', 'gaming monitor', 'keyboard',
                    'mechanical keyboard', 'wireless mouse', 'usb-c cable'
                ]),
                'results_count': random.randint(0, 500),
                'page_number': random.randint(1, 5),
                'filters_applied': random.choice([True, False]),
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_user_login(self) -> Event:
        """Generate a user login event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        self.session_map[user_id] = f"sess_{uuid.uuid4().hex[:8]}"  # New session
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.USER_LOGIN.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self.session_map[user_id],
            properties={
                'login_method': random.choice(['email', 'google', 'facebook', 'apple']),
                'device_new': random.choice([True, False]),
                'location_new': random.choice([True, False]),
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event
    
    def generate_video_play(self) -> Event:
        """Generate a video play event."""
        self._advance_time()
        user_id = random.choice(self.user_ids)
        
        event = Event(
            event_id=f"evt_{self.event_id_counter:010d}",
            event_type=EventType.VIDEO_PLAY.value,
            user_id=user_id,
            timestamp=self.last_event_time.isoformat() + 'Z',
            session_id=self._get_or_create_session(user_id),
            properties={
                'video_id': f"vid_{random.randint(1, 10000):05d}",
                'video_title': random.choice([
                    'Product Review', 'Tutorial', 'How-to Guide', 'Demo'
                ]),
                'video_duration': random.randint(30, 3600),  # seconds
                'autoplay': random.choice([True, False]),
            },
            device=random.choice(self.devices),
            geo_location=random.choice(self.geo_locations),
            source=random.choice(self.sources),
        )
        self.event_id_counter += 1
        return event


class RealisticEventGenerator(EventGenerator):
    """
    Generates realistic event distributions.
    
    Uses weighted event type distribution to simulate real user behavior:
    - 40% page views
    - 25% clicks
    - 15% add to cart
    - 10% purchases
    - 5% searches
    - 3% video plays
    - 2% logins
    """
    
    def generate_event(self) -> Event:
        """Generate a random event based on realistic distribution."""
        event_type = random.choices(
            [
                EventType.PAGE_VIEW,
                EventType.CLICK,
                EventType.ADD_TO_CART,
                EventType.PURCHASE,
                EventType.SEARCH,
                EventType.VIDEO_PLAY,
                EventType.USER_LOGIN,
            ],
            weights=[0.40, 0.25, 0.15, 0.10, 0.05, 0.03, 0.02],
        )[0]
        
        if event_type == EventType.PAGE_VIEW:
            return self.generate_page_view()
        elif event_type == EventType.CLICK:
            return self.generate_click()
        elif event_type == EventType.ADD_TO_CART:
            return self.generate_add_to_cart()
        elif event_type == EventType.PURCHASE:
            return self.generate_purchase()
        elif event_type == EventType.SEARCH:
            return self.generate_search()
        elif event_type == EventType.VIDEO_PLAY:
            return self.generate_video_play()
        elif event_type == EventType.USER_LOGIN:
            return self.generate_user_login()
        else:
            return self.generate_page_view()
