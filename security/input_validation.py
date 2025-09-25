#==========================================================================================\\\
#============================== security/input_validation.py ==============================\\\
#==========================================================================================\\\
"""
Production-Grade Input Validation and Sanitization
Prevents injection attacks and ensures safe operation of the DIP control system.

SECURITY FEATURES:
- Strict numeric bounds checking
- Buffer overflow prevention
- Rate limiting
- Input sanitization
- Command validation
- Safe parsing with error handling
"""

import re
import math
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputType(Enum):
    """Types of inputs that need validation"""
    CONTROL_FORCE = "control_force"
    PENDULUM_ANGLE = "pendulum_angle"
    CART_POSITION = "cart_position"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"
    CONFIGURATION_VALUE = "configuration_value"
    NETWORK_COMMAND = "network_command"
    TIME_VALUE = "time_value"

@dataclass
class SecurityContext:
    """Security context for validation requests"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    request_id: str
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class ValidationRule:
    """Validation rule definition"""
    input_type: InputType
    min_value: float
    max_value: float
    max_precision: int = 6
    required: bool = True
    description: str = ""

@dataclass
class RateLimitRule:
    """Rate limiting rule"""
    max_requests: int
    time_window: int  # seconds
    block_duration: int = 60  # seconds to block after limit exceeded

class InputValidator:
    """Comprehensive input validation and sanitization"""

    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        self.rate_limits = self._initialize_rate_limits()
        self.request_history: Dict[str, List[datetime]] = {}
        self.blocked_clients: Dict[str, datetime] = {}

    def _initialize_validation_rules(self) -> Dict[InputType, ValidationRule]:
        """Initialize validation rules for different input types"""
        return {
            InputType.CONTROL_FORCE: ValidationRule(
                input_type=InputType.CONTROL_FORCE,
                min_value=-150.0,  # Newton - maximum safe force
                max_value=150.0,
                max_precision=3,
                description="Control force applied to cart (Newton)"
            ),
            InputType.PENDULUM_ANGLE: ValidationRule(
                input_type=InputType.PENDULUM_ANGLE,
                min_value=-math.pi,  # Radians
                max_value=math.pi,
                max_precision=6,
                description="Pendulum angle (radians)"
            ),
            InputType.CART_POSITION: ValidationRule(
                input_type=InputType.CART_POSITION,
                min_value=-2.0,  # Meters - track length limits
                max_value=2.0,
                max_precision=4,
                description="Cart position on track (meters)"
            ),
            InputType.VELOCITY: ValidationRule(
                input_type=InputType.VELOCITY,
                min_value=-10.0,  # m/s - safety limits
                max_value=10.0,
                max_precision=4,
                description="Velocity (m/s)"
            ),
            InputType.ACCELERATION: ValidationRule(
                input_type=InputType.ACCELERATION,
                min_value=-100.0,  # m/s^2 - physical limits
                max_value=100.0,
                max_precision=3,
                description="Acceleration (m/s^2)"
            ),
            InputType.CONFIGURATION_VALUE: ValidationRule(
                input_type=InputType.CONFIGURATION_VALUE,
                min_value=0.001,  # Positive configuration values
                max_value=1000.0,
                max_precision=6,
                description="Configuration parameter value"
            ),
            InputType.TIME_VALUE: ValidationRule(
                input_type=InputType.TIME_VALUE,
                min_value=0.0,
                max_value=86400.0,  # 24 hours maximum
                max_precision=6,
                description="Time value (seconds)"
            )
        }

    def _initialize_rate_limits(self) -> Dict[str, RateLimitRule]:
        """Initialize rate limiting rules"""
        return {
            'control_commands': RateLimitRule(
                max_requests=1000,  # Max control commands per minute
                time_window=60,
                block_duration=300  # 5 minute block
            ),
            'configuration_changes': RateLimitRule(
                max_requests=10,  # Max config changes per minute
                time_window=60,
                block_duration=600  # 10 minute block
            ),
            'authentication_attempts': RateLimitRule(
                max_requests=5,  # Max login attempts per minute
                time_window=60,
                block_duration=900  # 15 minute block
            )
        }

    def sanitize_string(self, value: str, max_length: int = 256) -> str:
        """Sanitize string input to prevent injection attacks"""
        if not isinstance(value, str):
            raise ValidationError("Input must be a string")

        # Limit length to prevent buffer overflow
        if len(value) > max_length:
            raise ValidationError(f"String too long (max {max_length} characters)")

        # Remove potentially dangerous characters
        # Allow only alphanumeric, spaces, hyphens, underscores, and dots
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-_\.]', '', value)

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized

    def validate_numeric_input(self, value: Any, input_type: InputType,
                             client_id: Optional[str] = None) -> float:
        """Validate and sanitize numeric input"""
        try:
            # Get validation rule
            rule = self.validation_rules.get(input_type)
            if not rule:
                raise ValidationError(f"No validation rule for {input_type}")

            # Check rate limiting if client_id provided
            if client_id:
                self._check_rate_limit(client_id, 'control_commands')

            # Convert to float
            if isinstance(value, str):
                # Remove any non-numeric characters except decimal point and minus
                cleaned = re.sub(r'[^0-9.\-]', '', value)
                if not cleaned or cleaned in ['.', '-', '-.']:
                    raise ValidationError("Invalid numeric format")
                numeric_value = float(cleaned)
            elif isinstance(value, (int, float)):
                numeric_value = float(value)
            else:
                raise ValidationError("Value must be numeric")

            # Check for NaN or infinity
            if math.isnan(numeric_value) or math.isinf(numeric_value):
                raise ValidationError("Invalid numeric value (NaN or infinity)")

            # Check bounds
            if numeric_value < rule.min_value or numeric_value > rule.max_value:
                raise ValidationError(
                    f"{rule.description}: value {numeric_value} outside safe range "
                    f"[{rule.min_value}, {rule.max_value}]"
                )

            # Limit precision to prevent precision attacks
            precision_factor = 10 ** rule.max_precision
            numeric_value = round(numeric_value * precision_factor) / precision_factor

            logger.debug(f"Validated {input_type.value}: {numeric_value}")
            return numeric_value

        except ValueError as e:
            raise ValidationError(f"Invalid numeric value: {e}")
        except Exception as e:
            logger.error(f"Validation error for {input_type}: {e}")
            raise ValidationError(f"Validation failed: {e}")

    def validate_control_state(self, state_vector: List[float],
                             client_id: Optional[str] = None) -> List[float]:
        """Validate complete control state vector"""
        if not isinstance(state_vector, list):
            raise ValidationError("State vector must be a list")

        if len(state_vector) != 6:
            raise ValidationError("State vector must have exactly 6 elements")

        validated_state = []

        try:
            # Validate each state component
            validated_state.append(
                self.validate_numeric_input(state_vector[0], InputType.CART_POSITION, client_id)
            )
            validated_state.append(
                self.validate_numeric_input(state_vector[1], InputType.PENDULUM_ANGLE, client_id)
            )
            validated_state.append(
                self.validate_numeric_input(state_vector[2], InputType.PENDULUM_ANGLE, client_id)
            )
            validated_state.append(
                self.validate_numeric_input(state_vector[3], InputType.VELOCITY, client_id)
            )
            validated_state.append(
                self.validate_numeric_input(state_vector[4], InputType.VELOCITY, client_id)
            )
            validated_state.append(
                self.validate_numeric_input(state_vector[5], InputType.VELOCITY, client_id)
            )

            return validated_state

        except Exception as e:
            logger.warning(f"State vector validation failed: {e}")
            raise ValidationError(f"Invalid state vector: {e}")

    def validate_control_command(self, control_force: Any,
                                client_id: Optional[str] = None) -> float:
        """Validate control command with safety checks"""
        validated_force = self.validate_numeric_input(
            control_force, InputType.CONTROL_FORCE, client_id
        )

        # Additional safety checks for control commands
        if abs(validated_force) > 100.0:  # Extra safety limit
            logger.warning(f"High control force requested: {validated_force}N")

        return validated_force

    def _check_rate_limit(self, client_id: str, operation_type: str):
        """Check and enforce rate limiting"""
        now = datetime.now()

        # Check if client is currently blocked
        if client_id in self.blocked_clients:
            if now < self.blocked_clients[client_id]:
                remaining = (self.blocked_clients[client_id] - now).total_seconds()
                raise ValidationError(f"Client blocked for {remaining:.0f} more seconds")
            else:
                # Remove expired block
                del self.blocked_clients[client_id]

        # Get rate limit rule
        rule = self.rate_limits.get(operation_type)
        if not rule:
            return  # No rate limiting for this operation

        # Initialize request history for client
        if client_id not in self.request_history:
            self.request_history[client_id] = []

        # Clean old requests outside time window
        cutoff_time = now - timedelta(seconds=rule.time_window)
        self.request_history[client_id] = [
            req_time for req_time in self.request_history[client_id]
            if req_time > cutoff_time
        ]

        # Check if limit exceeded
        if len(self.request_history[client_id]) >= rule.max_requests:
            # Block client
            self.blocked_clients[client_id] = now + timedelta(seconds=rule.block_duration)
            logger.warning(f"Client {client_id} exceeded rate limit for {operation_type}")
            raise ValidationError(
                f"Rate limit exceeded for {operation_type}. "
                f"Blocked for {rule.block_duration} seconds."
            )

        # Record this request
        self.request_history[client_id].append(now)

    def validate_control_input(self, control_data: Dict[str, Any], context: SecurityContext) -> bool:
        """Validate control input with security context."""
        try:
            # Rate limiting check
            self._check_rate_limit(context.user_id, 'control_commands')

            # Validate each control parameter
            if 'force' in control_data:
                self.validate_numeric_input(control_data['force'], InputType.CONTROL_FORCE, context.user_id)

            if 'position' in control_data:
                self.validate_numeric_input(control_data['position'], InputType.CART_POSITION, context.user_id)

            if 'angle1' in control_data:
                self.validate_numeric_input(control_data['angle1'], InputType.PENDULUM_ANGLE, context.user_id)

            if 'angle2' in control_data:
                self.validate_numeric_input(control_data['angle2'], InputType.PENDULUM_ANGLE, context.user_id)

            # Check for malicious patterns
            for key, value in control_data.items():
                if isinstance(value, str):
                    sanitized = self.sanitize_string_input(value)
                    if sanitized != value:
                        logger.warning(f"Suspicious input detected from {context.user_id}: {key}={value}")
                        return False

            return True

        except ValidationError as e:
            logger.warning(f"Control input validation failed for {context.user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Control input validation error for {context.user_id}: {e}")
            return False

    def validate_network_packet(self, packet_data: bytes, max_size: int = 1024) -> bytes:
        """Validate network packet to prevent buffer overflow"""
        if not isinstance(packet_data, bytes):
            raise ValidationError("Packet data must be bytes")

        if len(packet_data) > max_size:
            raise ValidationError(f"Packet too large (max {max_size} bytes)")

        if len(packet_data) == 0:
            raise ValidationError("Empty packet")

        return packet_data

    def validate_configuration_update(self, config_dict: Dict[str, Any],
                                    client_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate configuration updates"""
        if client_id:
            self._check_rate_limit(client_id, 'configuration_changes')

        if not isinstance(config_dict, dict):
            raise ValidationError("Configuration must be a dictionary")

        validated_config = {}

        for key, value in config_dict.items():
            # Sanitize key
            safe_key = self.sanitize_string(key, max_length=64)
            if not safe_key:
                raise ValidationError(f"Invalid configuration key: {key}")

            # Validate value based on type
            if isinstance(value, (int, float)):
                validated_value = self.validate_numeric_input(
                    value, InputType.CONFIGURATION_VALUE, client_id
                )
            elif isinstance(value, str):
                validated_value = self.sanitize_string(value, max_length=256)
            elif isinstance(value, bool):
                validated_value = bool(value)
            else:
                raise ValidationError(f"Unsupported configuration value type: {type(value)}")

            validated_config[safe_key] = validated_value

        return validated_config

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation statistics and current status"""
        now = datetime.now()

        active_blocks = {
            client_id: (block_time - now).total_seconds()
            for client_id, block_time in self.blocked_clients.items()
            if block_time > now
        }

        return {
            'validation_rules_count': len(self.validation_rules),
            'rate_limit_rules_count': len(self.rate_limits),
            'active_clients': len(self.request_history),
            'blocked_clients': len(active_blocks),
            'blocked_client_details': active_blocks
        }

# Global input validator instance
input_validator = InputValidator()

def validate_input(input_type: InputType, client_id: Optional[str] = None):
    """Decorator for input validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate inputs based on function parameters
            # This would need to be customized based on specific function signatures
            return func(*args, **kwargs)
        return wrapper
    return decorator