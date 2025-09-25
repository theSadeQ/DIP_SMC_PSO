#==========================================================================================\\\
#====================== src/interfaces/data_exchange/schemas.py ========================\\\
#==========================================================================================\\\
"""
Schema validation framework for data exchange.
This module provides comprehensive schema validation capabilities
including JSON Schema, custom data schemas, field validation,
and type checking for ensuring data integrity and consistency.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Type, Callable, Set
from enum import Enum
import logging
import time

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class FieldType(Enum):
    """Field type enumeration for schema validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    BINARY = "binary"
    ENUM = "enum"


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationError:
    """Validation error information."""
    field_path: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    error_code: str = "VALIDATION_ERROR"
    expected_type: Optional[FieldType] = None
    actual_value: Optional[Any] = None
    constraint_name: Optional[str] = None


@dataclass
class FieldConstraint:
    """Field validation constraint."""
    name: str
    validator: Callable[[Any], bool]
    error_message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class FieldSchema:
    """Schema definition for a data field."""
    name: str
    field_type: FieldType
    required: bool = True
    nullable: bool = False
    default_value: Optional[Any] = None

    # Type-specific constraints
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None

    # Array constraints
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False
    item_schema: Optional['FieldSchema'] = None

    # Object constraints
    properties: Dict[str, 'FieldSchema'] = field(default_factory=dict)
    additional_properties: bool = True

    # Custom constraints
    custom_constraints: List[FieldConstraint] = field(default_factory=list)

    # Documentation
    description: str = ""
    examples: List[Any] = field(default_factory=list)

    def add_constraint(self, name: str, validator: Callable[[Any], bool],
                      error_message: str, severity: ValidationSeverity = ValidationSeverity.ERROR) -> None:
        """Add custom validation constraint."""
        constraint = FieldConstraint(name, validator, error_message, severity)
        self.custom_constraints.append(constraint)

    def validate_value(self, value: Any, field_path: str = "") -> List[ValidationError]:
        """Validate a value against this field schema."""
        errors = []

        # Check if null and nullable
        if value is None:
            if not self.nullable:
                if self.required:
                    errors.append(ValidationError(
                        field_path=field_path or self.name,
                        message="Field is required but value is null",
                        error_code="NULL_VALUE"
                    ))
                return errors
            else:
                return errors  # Null is allowed

        # Type validation
        type_errors = self._validate_type(value, field_path)
        errors.extend(type_errors)

        if not type_errors:  # Only continue if type is correct
            # Value constraints
            errors.extend(self._validate_constraints(value, field_path))

            # Custom constraints
            errors.extend(self._validate_custom_constraints(value, field_path))

        return errors

    def _validate_type(self, value: Any, field_path: str) -> List[ValidationError]:
        """Validate the type of a value."""
        errors = []

        expected_types = {
            FieldType.STRING: str,
            FieldType.INTEGER: int,
            FieldType.FLOAT: (int, float),
            FieldType.BOOLEAN: bool,
            FieldType.ARRAY: (list, tuple),
            FieldType.OBJECT: dict,
        }

        if self.field_type in expected_types:
            expected_type = expected_types[self.field_type]
            if not isinstance(value, expected_type):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Expected {self.field_type.value}, got {type(value).__name__}",
                    error_code="TYPE_MISMATCH",
                    expected_type=self.field_type,
                    actual_value=value
                ))

        elif self.field_type == FieldType.DATETIME:
            # Check for datetime string or datetime object
            if not isinstance(value, str):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message="DateTime field must be a string",
                    error_code="TYPE_MISMATCH",
                    expected_type=self.field_type,
                    actual_value=value
                ))

        elif self.field_type == FieldType.UUID:
            if not isinstance(value, str) or not self._is_valid_uuid(value):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message="Invalid UUID format",
                    error_code="INVALID_UUID",
                    expected_type=self.field_type,
                    actual_value=value
                ))

        elif self.field_type == FieldType.EMAIL:
            if not isinstance(value, str) or not self._is_valid_email(value):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message="Invalid email format",
                    error_code="INVALID_EMAIL",
                    expected_type=self.field_type,
                    actual_value=value
                ))

        elif self.field_type == FieldType.URL:
            if not isinstance(value, str) or not self._is_valid_url(value):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message="Invalid URL format",
                    error_code="INVALID_URL",
                    expected_type=self.field_type,
                    actual_value=value
                ))

        return errors

    def _validate_constraints(self, value: Any, field_path: str) -> List[ValidationError]:
        """Validate value constraints."""
        errors = []

        # Numeric constraints
        if self.field_type in [FieldType.INTEGER, FieldType.FLOAT]:
            if self.min_value is not None and value < self.min_value:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Value {value} is less than minimum {self.min_value}",
                    error_code="MIN_VALUE_VIOLATION",
                    constraint_name="min_value"
                ))

            if self.max_value is not None and value > self.max_value:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Value {value} is greater than maximum {self.max_value}",
                    error_code="MAX_VALUE_VIOLATION",
                    constraint_name="max_value"
                ))

        # String constraints
        if self.field_type == FieldType.STRING:
            if self.min_length is not None and len(value) < self.min_length:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"String length {len(value)} is less than minimum {self.min_length}",
                    error_code="MIN_LENGTH_VIOLATION",
                    constraint_name="min_length"
                ))

            if self.max_length is not None and len(value) > self.max_length:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"String length {len(value)} is greater than maximum {self.max_length}",
                    error_code="MAX_LENGTH_VIOLATION",
                    constraint_name="max_length"
                ))

            if self.pattern is not None and not re.match(self.pattern, value):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"String does not match pattern: {self.pattern}",
                    error_code="PATTERN_MISMATCH",
                    constraint_name="pattern"
                ))

        # Enum constraints
        if self.enum_values is not None and value not in self.enum_values:
            errors.append(ValidationError(
                field_path=field_path or self.name,
                message=f"Value {value} is not in allowed values: {self.enum_values}",
                error_code="ENUM_VIOLATION",
                constraint_name="enum_values"
            ))

        # Array constraints
        if self.field_type == FieldType.ARRAY:
            if self.min_items is not None and len(value) < self.min_items:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Array has {len(value)} items, minimum is {self.min_items}",
                    error_code="MIN_ITEMS_VIOLATION",
                    constraint_name="min_items"
                ))

            if self.max_items is not None and len(value) > self.max_items:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Array has {len(value)} items, maximum is {self.max_items}",
                    error_code="MAX_ITEMS_VIOLATION",
                    constraint_name="max_items"
                ))

            if self.unique_items and len(value) != len(set(str(item) for item in value)):
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message="Array items must be unique",
                    error_code="UNIQUE_ITEMS_VIOLATION",
                    constraint_name="unique_items"
                ))

            # Validate array items
            if self.item_schema:
                for i, item in enumerate(value):
                    item_path = f"{field_path or self.name}[{i}]"
                    item_errors = self.item_schema.validate_value(item, item_path)
                    errors.extend(item_errors)

        # Object constraints
        if self.field_type == FieldType.OBJECT:
            # Validate required properties
            for prop_name, prop_schema in self.properties.items():
                if prop_schema.required and prop_name not in value:
                    errors.append(ValidationError(
                        field_path=f"{field_path or self.name}.{prop_name}",
                        message=f"Required property '{prop_name}' is missing",
                        error_code="MISSING_PROPERTY"
                    ))

            # Validate existing properties
            for prop_name, prop_value in value.items():
                prop_path = f"{field_path or self.name}.{prop_name}"
                if prop_name in self.properties:
                    prop_errors = self.properties[prop_name].validate_value(prop_value, prop_path)
                    errors.extend(prop_errors)
                elif not self.additional_properties:
                    errors.append(ValidationError(
                        field_path=prop_path,
                        message=f"Additional property '{prop_name}' is not allowed",
                        error_code="ADDITIONAL_PROPERTY"
                    ))

        return errors

    def _validate_custom_constraints(self, value: Any, field_path: str) -> List[ValidationError]:
        """Validate custom constraints."""
        errors = []

        for constraint in self.custom_constraints:
            try:
                if not constraint.validator(value):
                    errors.append(ValidationError(
                        field_path=field_path or self.name,
                        message=constraint.error_message,
                        severity=constraint.severity,
                        error_code="CUSTOM_CONSTRAINT_VIOLATION",
                        constraint_name=constraint.name,
                        actual_value=value
                    ))
            except Exception as e:
                errors.append(ValidationError(
                    field_path=field_path or self.name,
                    message=f"Error in custom constraint '{constraint.name}': {e}",
                    severity=ValidationSeverity.ERROR,
                    error_code="CONSTRAINT_ERROR",
                    constraint_name=constraint.name
                ))

        return errors

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if string is a valid UUID."""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    @staticmethod
    def _is_valid_email(value: str) -> bool:
        """Check if string is a valid email."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))

    @staticmethod
    def _is_valid_url(value: str) -> bool:
        """Check if string is a valid URL."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, value, re.IGNORECASE))


@dataclass
class DataSchema:
    """Complete schema definition for data validation."""
    name: str
    version: str = "1.0"
    description: str = ""
    fields: Dict[str, FieldSchema] = field(default_factory=dict)
    required_fields: Set[str] = field(default_factory=set)
    allow_additional_fields: bool = True
    strict_mode: bool = False

    def add_field(self, field_schema: FieldSchema) -> None:
        """Add field schema to the data schema."""
        self.fields[field_schema.name] = field_schema
        if field_schema.required:
            self.required_fields.add(field_schema.name)

    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate data against this schema."""
        errors = []

        # Check required fields
        for required_field in self.required_fields:
            if required_field not in data:
                errors.append(ValidationError(
                    field_path=required_field,
                    message=f"Required field '{required_field}' is missing",
                    error_code="MISSING_REQUIRED_FIELD"
                ))

        # Validate existing fields
        for field_name, field_value in data.items():
            if field_name in self.fields:
                field_errors = self.fields[field_name].validate_value(field_value, field_name)
                errors.extend(field_errors)
            elif not self.allow_additional_fields:
                errors.append(ValidationError(
                    field_path=field_name,
                    message=f"Additional field '{field_name}' is not allowed",
                    error_code="ADDITIONAL_FIELD",
                    severity=ValidationSeverity.WARNING if not self.strict_mode else ValidationSeverity.ERROR
                ))

        return errors

    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid according to this schema."""
        errors = self.validate(data)
        # Only consider errors and critical issues
        critical_errors = [e for e in errors if e.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        return len(critical_errors) == 0

    def get_field_names(self) -> List[str]:
        """Get list of all field names."""
        return list(self.fields.keys())

    def get_required_field_names(self) -> List[str]:
        """Get list of required field names."""
        return list(self.required_fields)


class SchemaValidator:
    """Main schema validator with caching and performance optimization."""

    def __init__(self):
        self._schemas: Dict[str, DataSchema] = {}
        self._validation_cache: Dict[str, List[ValidationError]] = {}
        self._cache_max_size = 1000
        self._logger = logging.getLogger("schema_validator")

    def register_schema(self, schema: DataSchema) -> None:
        """Register a schema for validation."""
        schema_key = f"{schema.name}:{schema.version}"
        self._schemas[schema_key] = schema
        self._logger.info(f"Registered schema: {schema_key}")

    def validate_data(self, data: Dict[str, Any], schema_name: str,
                     schema_version: str = "1.0", use_cache: bool = True) -> List[ValidationError]:
        """Validate data against a registered schema."""
        schema_key = f"{schema_name}:{schema_version}"

        if schema_key not in self._schemas:
            return [ValidationError(
                field_path="",
                message=f"Schema '{schema_key}' not found",
                error_code="SCHEMA_NOT_FOUND",
                severity=ValidationSeverity.CRITICAL
            )]

        # Check cache if enabled
        if use_cache:
            data_hash = self._hash_data(data)
            cache_key = f"{schema_key}:{data_hash}"
            if cache_key in self._validation_cache:
                return self._validation_cache[cache_key]

        # Validate data
        schema = self._schemas[schema_key]
        errors = schema.validate(data)

        # Cache results
        if use_cache:
            self._cache_validation_result(cache_key, errors)

        return errors

    def is_data_valid(self, data: Dict[str, Any], schema_name: str,
                     schema_version: str = "1.0") -> bool:
        """Check if data is valid against a schema."""
        errors = self.validate_data(data, schema_name, schema_version)
        critical_errors = [e for e in errors if e.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        return len(critical_errors) == 0

    def get_schema(self, schema_name: str, schema_version: str = "1.0") -> Optional[DataSchema]:
        """Get a registered schema."""
        schema_key = f"{schema_name}:{schema_version}"
        return self._schemas.get(schema_key)

    def list_schemas(self) -> List[str]:
        """List all registered schemas."""
        return list(self._schemas.keys())

    def clear_cache(self) -> None:
        """Clear validation cache."""
        self._validation_cache.clear()

    def _hash_data(self, data: Dict[str, Any]) -> str:
        """Generate hash for data caching."""
        import hashlib
        import json

        try:
            # Convert to deterministic JSON string
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(json_str.encode()).hexdigest()
        except Exception:
            # Fallback to timestamp for non-serializable data
            return str(time.time())

    def _cache_validation_result(self, cache_key: str, errors: List[ValidationError]) -> None:
        """Cache validation result."""
        # Implement LRU-style cache management
        if len(self._validation_cache) >= self._cache_max_size:
            # Remove oldest entry (simplified implementation)
            oldest_key = next(iter(self._validation_cache))
            del self._validation_cache[oldest_key]

        self._validation_cache[cache_key] = errors


class JSONSchema:
    """JSON Schema integration for standards-compliant validation."""

    def __init__(self):
        if not JSONSCHEMA_AVAILABLE:
            raise ImportError("jsonschema library not available")
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def add_schema(self, schema_id: str, schema_definition: Dict[str, Any]) -> None:
        """Add JSON Schema definition."""
        self._schemas[schema_id] = schema_definition

    def validate(self, data: Any, schema_id: str) -> List[ValidationError]:
        """Validate data against JSON Schema."""
        if schema_id not in self._schemas:
            return [ValidationError(
                field_path="",
                message=f"JSON Schema '{schema_id}' not found",
                error_code="SCHEMA_NOT_FOUND",
                severity=ValidationSeverity.CRITICAL
            )]

        errors = []
        schema = self._schemas[schema_id]

        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errors.append(ValidationError(
                field_path=".".join(str(p) for p in e.absolute_path),
                message=e.message,
                error_code="JSON_SCHEMA_VIOLATION"
            ))
        except jsonschema.SchemaError as e:
            errors.append(ValidationError(
                field_path="",
                message=f"Invalid schema: {e.message}",
                error_code="INVALID_SCHEMA",
                severity=ValidationSeverity.CRITICAL
            ))

        return errors


@dataclass
class MessageSchema:
    """Schema specifically for message validation."""
    message_type: str
    version: str
    header_schema: DataSchema
    payload_schema: DataSchema
    metadata_schema: Optional[DataSchema] = None

    def validate_message(self, message_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate complete message structure."""
        errors = []

        # Validate header
        if 'header' in message_data:
            header_errors = self.header_schema.validate(message_data['header'])
            for error in header_errors:
                error.field_path = f"header.{error.field_path}"
            errors.extend(header_errors)
        else:
            errors.append(ValidationError(
                field_path="header",
                message="Message header is missing",
                error_code="MISSING_HEADER",
                severity=ValidationSeverity.CRITICAL
            ))

        # Validate payload
        if 'payload' in message_data:
            payload_errors = self.payload_schema.validate(message_data['payload'])
            for error in payload_errors:
                error.field_path = f"payload.{error.field_path}"
            errors.extend(payload_errors)
        else:
            errors.append(ValidationError(
                field_path="payload",
                message="Message payload is missing",
                error_code="MISSING_PAYLOAD",
                severity=ValidationSeverity.CRITICAL
            ))

        # Validate metadata if schema is provided
        if self.metadata_schema and 'metadata' in message_data:
            metadata_errors = self.metadata_schema.validate(message_data['metadata'])
            for error in metadata_errors:
                error.field_path = f"metadata.{error.field_path}"
            errors.extend(metadata_errors)

        return errors


# Factory functions for common schemas
def create_control_message_schema() -> MessageSchema:
    """Create schema for control messages."""
    header_schema = DataSchema("control_header")
    header_schema.add_field(FieldSchema("message_type", FieldType.STRING, enum_values=["command"]))
    header_schema.add_field(FieldSchema("timestamp", FieldType.FLOAT))
    header_schema.add_field(FieldSchema("source", FieldType.STRING))

    payload_schema = DataSchema("control_payload")
    payload_schema.add_field(FieldSchema("command", FieldType.STRING, min_length=1))
    payload_schema.add_field(FieldSchema("parameters", FieldType.OBJECT, required=False))
    payload_schema.add_field(FieldSchema("target", FieldType.STRING, default_value="system"))

    return MessageSchema("control", "1.0", header_schema, payload_schema)


def create_telemetry_message_schema() -> MessageSchema:
    """Create schema for telemetry messages."""
    header_schema = DataSchema("telemetry_header")
    header_schema.add_field(FieldSchema("message_type", FieldType.STRING, enum_values=["telemetry"]))
    header_schema.add_field(FieldSchema("timestamp", FieldType.FLOAT))
    header_schema.add_field(FieldSchema("source", FieldType.STRING))

    payload_schema = DataSchema("telemetry_payload")
    payload_schema.add_field(FieldSchema("sensor_id", FieldType.STRING, min_length=1))
    payload_schema.add_field(FieldSchema("measurements", FieldType.OBJECT))
    payload_schema.add_field(FieldSchema("units", FieldType.OBJECT, required=False))
    payload_schema.add_field(FieldSchema("quality", FieldType.OBJECT, required=False))

    return MessageSchema("telemetry", "1.0", header_schema, payload_schema)