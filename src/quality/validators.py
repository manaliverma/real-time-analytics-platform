"""
Data validation framework for real-time data quality checks.

Provides validators for schema, range, nullability, and anomaly detection.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import statistics
from collections import deque

from src.quality.schema import EventSchema
from src.utils.metrics import record_validation_failure


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    validator_name: str
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SchemaValidator:
    """Validates events against schema definition."""
    
    def __init__(self):
        self.name = "schema_validator"
        self.failure_count = 0
    
    def validate(self, event: Dict[str, Any]) -> ValidationResult:
        """Validate event schema."""
        is_valid, error_msg = EventSchema.validate(event)
        
        if not is_valid:
            self.failure_count += 1
            record_validation_failure(self.name, "schema_violation")
            logger.warning(f"Schema validation failed: {error_msg}")
        
        return ValidationResult(
            is_valid=is_valid,
            validator_name=self.name,
            error_message=error_msg
        )


class RangeValidator:
    """Validates that numeric fields are within expected ranges."""
    
    RANGE_CONSTRAINTS = {
        'user_id': {'min': 1, 'max': 9999999999},
        'price': {'min': 0.01, 'max': 999999.99},
        'quantity': {'min': 1, 'max': 1000},
        'discount': {'min': 0, 'max': 100},
    }
    
    def __init__(self):
        self.name = "range_validator"
        self.failure_count = 0
    
    def validate(self, event: Dict[str, Any]) -> ValidationResult:
        """Validate numeric fields are in expected ranges."""
        warnings = []
        
        # Check top-level fields
        for field, value in event.items():
            if field in self.RANGE_CONSTRAINTS and isinstance(value, (int, float)):
                constraints = self.RANGE_CONSTRAINTS[field]
                if not (constraints['min'] <= value <= constraints['max']):
                    msg = (
                        f"Field {field}={value} out of range "
                        f"[{constraints['min']}, {constraints['max']}]"
                    )
                    warnings.append(msg)
                    record_validation_failure(self.name, "out_of_range")
        
        # Check properties sub-fields
        if 'properties' in event and isinstance(event['properties'], dict):
            for field, value in event['properties'].items():
                if field in self.RANGE_CONSTRAINTS and isinstance(value, (int, float)):
                    constraints = self.RANGE_CONSTRAINTS[field]
                    if not (constraints['min'] <= value <= constraints['max']):
                        msg = (
                            f"Property {field}={value} out of range "
                            f"[{constraints['min']}, {constraints['max']}]"
                        )
                        warnings.append(msg)
        
        is_valid = len(warnings) == 0
        self.failure_count += 0 if is_valid else 1
        
        return ValidationResult(
            is_valid=is_valid,
            validator_name=self.name,
            warnings=warnings
        )


class NullabilityValidator:
    """Validates that required fields are not null/empty."""
    
    REQUIRED_NON_NULL = [
        'event_id',
        'event_type',
        'user_id',
        'timestamp',
        'device',
        'geo_location'
    ]
    
    def __init__(self):
        self.name = "nullability_validator"
        self.failure_count = 0
    
    def validate(self, event: Dict[str, Any]) -> ValidationResult:
        """Validate required fields are not null."""
        errors = []
        
        for field in self.REQUIRED_NON_NULL:
            if field not in event:
                errors.append(f"Missing required field: {field}")
                continue
            
            value = event[field]
            if value is None or (isinstance(value, str) and value.strip() == ''):
                errors.append(f"Required field is null/empty: {field}")
                record_validation_failure(self.name, "null_value")
        
        is_valid = len(errors) == 0
        self.failure_count += 0 if is_valid else 1
        
        return ValidationResult(
            is_valid=is_valid,
            validator_name=self.name,
            error_message="; ".join(errors) if errors else None
        )


class AnomalyDetector:
    """
    Detects anomalies in event streams using statistical methods.
    
    Maintains sliding window of recent values to detect:
    - Sudden spikes
    - Sudden drops
    - Unusual patterns
    """
    
    def __init__(self, window_size: int = 100, std_threshold: float = 3.0):
        self.name = "anomaly_detector"
        self.window_size = window_size
        self.std_threshold = std_threshold
        self.value_history = deque(maxlen=window_size)
        self.failure_count = 0
    
    def detect(self, field: str, value: float) -> ValidationResult:
        """
        Detect anomalies in numeric field.
        
        Returns anomaly if value deviates >3 standard deviations
        from mean of recent values.
        """
        warnings = []
        
        self.value_history.append(value)
        
        # Need at least min_samples to detect anomalies
        if len(self.value_history) < 10:
            return ValidationResult(
                is_valid=True,
                validator_name=self.name,
                warnings=["Insufficient samples for anomaly detection"]
            )
        
        values = list(self.value_history)
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        
        if stdev == 0:
            return ValidationResult(is_valid=True, validator_name=self.name)
        
        # Calculate z-score
        z_score = abs((value - mean) / stdev)
        
        if z_score > self.std_threshold:
            msg = (
                f"Anomaly detected in {field}: value={value:.2f}, "
                f"mean={mean:.2f}, stdev={stdev:.2f}, z-score={z_score:.2f}"
            )
            warnings.append(msg)
            record_validation_failure(self.name, "anomaly_detected")
            self.failure_count += 1
        
        return ValidationResult(
            is_valid=len(warnings) == 0,
            validator_name=self.name,
            warnings=warnings
        )


class DataValidator:
    """
    Orchestrates all data validation checks.
    
    Runs multiple validators and aggregates results.
    """
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.range_validator = RangeValidator()
        self.nullability_validator = NullabilityValidator()
        self.anomaly_detector = AnomalyDetector()
        self.validation_results = []
    
    def validate(self, event: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validators on event.
        
        Args:
            event: Event to validate
        
        Returns:
            Tuple of (overall_valid, list_of_results)
        """
        results = []
        
        # Run schema validation (hard requirement)
        schema_result = self.schema_validator.validate(event)
        results.append(schema_result)
        
        if not schema_result.is_valid:
            return False, results
        
        # Run other validators (warnings)
        range_result = self.range_validator.validate(event)
        results.append(range_result)
        
        nullability_result = self.nullability_validator.validate(event)
        results.append(nullability_result)
        
        # Check for anomalies in price field if present
        if 'properties' in event and 'price' in event['properties']:
            price = event['properties']['price']
            if isinstance(price, (int, float)):
                anomaly_result = self.anomaly_detector.detect('price', price)
                results.append(anomaly_result)
        
        # Overall valid if schema passes (range/nullability are warnings)
        overall_valid = schema_result.is_valid and nullability_result.is_valid
        
        self.validation_results = results
        return overall_valid, results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            'total_validations': len(self.validation_results),
            'passed': sum(1 for r in self.validation_results if r.is_valid),
            'warnings': sum(len(r.warnings) for r in self.validation_results),
            'validators': [r.validator_name for r in self.validation_results],
        }
