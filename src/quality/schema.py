"""
Event schema definition and validation.

Defines the structure of events processed by the platform
and provides schema validation capabilities.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid
import json


class EventType(Enum):
    """Supported event types in the system."""
    PAGE_VIEW = "page_view"
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SEARCH = "search"
    VIDEO_PLAY = "video_play"
    VIDEO_COMPLETE = "video_complete"
    WISHLIST_ADD = "wishlist_add"
    REVIEW_SUBMIT = "review_submit"
    CHECKOUT_START = "checkout_start"
    CHECKOUT_COMPLETE = "checkout_complete"


class DeviceType(Enum):
    """Supported device types."""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"


@dataclass
class Event:
    """
    Core event data structure.
    
    Represents a user action captured from various sources
    (mobile app, web, IoT devices, etc.).
    
    Attributes:
        event_id: Unique event identifier (UUID)
        event_type: Type of event (enum)
        user_id: Unique user identifier
        timestamp: Event timestamp in ISO 8601 format
        session_id: Session identifier for grouping events
        properties: Event-specific properties (flexible dict)
        device: Device type (mobile, desktop, tablet)
        geo_location: Geographic location (country-region format)
        source: Event source (organic, paid, direct, referral)
        version: Event schema version
    """
    event_id: str
    event_type: str
    user_id: int
    timestamp: str
    session_id: str
    properties: Dict[str, Any]
    device: str
    geo_location: str
    source: str = "direct"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return Event(**data)
    
    @staticmethod
    def from_json(json_str: str) -> 'Event':
        """Create event from JSON string."""
        data = json.loads(json_str)
        return Event.from_dict(data)
    
    def __hash__(self):
        """Allow event to be used in sets/dicts."""
        return hash(self.event_id)


@dataclass
class EventSchema:
    """
    Schema definition for events.
    
    Defines required fields, types, and constraints for events.
    Used for validation before ingestion.
    """
    
    # Required fields with their types
    REQUIRED_FIELDS = {
        'event_id': str,
        'event_type': str,
        'user_id': int,
        'timestamp': str,
        'session_id': str,
        'properties': dict,
        'device': str,
        'geo_location': str,
    }
    
    # Field constraints
    FIELD_CONSTRAINTS = {
        'event_id': {
            'min_length': 1,
            'max_length': 255,
            'description': 'Unique event identifier'
        },
        'user_id': {
            'min_value': 1,
            'max_value': 9999999999,
            'description': 'User ID must be positive'
        },
        'timestamp': {
            'format': 'ISO8601',
            'description': 'Timestamp in ISO 8601 format'
        },
        'properties': {
            'max_size': 10000,  # bytes
            'description': 'Event properties JSON'
        }
    }
    
    # Valid values for enum fields
    VALID_EVENT_TYPES = [e.value for e in EventType]
    VALID_DEVICE_TYPES = [e.value for e in DeviceType]
    VALID_SOURCES = ['organic', 'paid', 'direct', 'referral']
    
    @classmethod
    def validate(cls, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate event against schema.
        
        Args:
            event: Event dictionary to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for required fields
        for field, field_type in cls.REQUIRED_FIELDS.items():
            if field not in event:
                return False, f"Missing required field: {field}"
            
            if not isinstance(event[field], field_type):
                return False, (
                    f"Invalid type for {field}: "
                    f"expected {field_type.__name__}, "
                    f"got {type(event[field]).__name__}"
                )
        
        # Validate event_type
        if event['event_type'] not in cls.VALID_EVENT_TYPES:
            return False, f"Invalid event_type: {event['event_type']}"
        
        # Validate device type
        if event['device'] not in cls.VALID_DEVICE_TYPES:
            return False, f"Invalid device: {event['device']}"
        
        # Validate geo_location format (should be like "US-CA")
        if not isinstance(event['geo_location'], str) or '-' not in event['geo_location']:
            return False, f"Invalid geo_location format: {event['geo_location']}"
        
        # Validate optional source field
        if 'source' in event and event['source'] not in cls.VALID_SOURCES:
            return False, f"Invalid source: {event['source']}"
        
        # Validate timestamp is in ISO 8601 format
        try:
            datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return False, f"Invalid timestamp format: {event['timestamp']}"
        
        # Validate user_id is positive
        if event['user_id'] <= 0:
            return False, "user_id must be positive"
        
        return True, None
    
    @classmethod
    def get_schema_dict(cls) -> Dict[str, Any]:
        """Get schema as dictionary (for documentation)."""
        return {
            'required_fields': cls.REQUIRED_FIELDS,
            'constraints': cls.FIELD_CONSTRAINTS,
            'valid_event_types': cls.VALID_EVENT_TYPES,
            'valid_device_types': cls.VALID_DEVICE_TYPES,
            'valid_sources': cls.VALID_SOURCES,
        }


# Sample event for testing
SAMPLE_EVENT = {
    'event_id': str(uuid.uuid4()),
    'event_type': 'purchase',
    'user_id': 12345,
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'session_id': 'sess_67890',
    'properties': {
        'order_id': 'ord_123456',
        'total_amount': 99.99,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'items_count': 3,
    },
    'device': 'mobile',
    'geo_location': 'US-CA',
    'source': 'organic',
    'version': '1.0'
}
