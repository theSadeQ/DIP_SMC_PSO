#==========================================================================================\\\
#============================== validator.py ========================================\\\
#==========================================================================================\\\
"""
Research plan validation module.

This module provides validation functionality for research plans used in
property-based testing. It includes schema validation and constraint checking.
"""

from typing import Dict, List, Any, Union, Optional
import json
from datetime import datetime


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_research_plan(plan: Dict[str, Any]) -> bool:
    """
    Validate a research plan against the expected schema.

    Args:
        plan: The research plan dictionary to validate

    Returns:
        bool: True if validation passes

    Raises:
        ValidationError: If validation fails
    """
    try:
        # Basic structure validation
        required_keys = ['metadata', 'executive_summary', 'phases', 'risks', 'acceptance', 'checklists', 'manifests']

        for key in required_keys:
            if key not in plan:
                raise ValidationError(f"Missing required key: {key}")

        # Validate metadata
        metadata = plan['metadata']
        metadata_required = ['title', 'version', 'created_at', 'schema_version']
        for key in metadata_required:
            if key not in metadata:
                raise ValidationError(f"Missing metadata key: {key}")

        # Validate executive summary
        exec_summary = plan['executive_summary']
        exec_required = ['context', 'intended_outcomes', 'phases_overview']
        for key in exec_required:
            if key not in exec_summary:
                raise ValidationError(f"Missing executive_summary key: {key}")

        # Validate phases
        phases = plan['phases']
        if not isinstance(phases, list) or len(phases) == 0:
            raise ValidationError("Phases must be a non-empty list")

        for phase in phases:
            phase_required = ['name', 'goals', 'success_criteria', 'tasks', 'artifacts', 'validation_steps', 'execution_prompt']
            for key in phase_required:
                if key not in phase:
                    raise ValidationError(f"Missing phase key: {key}")

        # Validate acceptance criteria
        acceptance = plan['acceptance']
        if not isinstance(acceptance, list):
            raise ValidationError("Acceptance must be a list")

        for item in acceptance:
            if not isinstance(item, dict) or 'statement' not in item:
                raise ValidationError("Each acceptance item must have a 'statement' key")

        return True

    except Exception as e:
        raise ValidationError(f"Validation failed: {str(e)}")


def validate_json_schema(data: Union[Dict, str], schema_path: Optional[str] = None) -> bool:
    """
    Validate JSON data against a schema.

    Args:
        data: The data to validate (dict or JSON string)
        schema_path: Optional path to schema file

    Returns:
        bool: True if validation passes
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")

    # Basic validation - extend as needed
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")

    return True


def validate_date_format(date_string: str) -> bool:
    """
    Validate ISO date format.

    Args:
        date_string: Date string to validate

    Returns:
        bool: True if valid ISO date format
    """
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        raise ValidationError(f"Invalid date format: {date_string}")


# Additional validation utilities
def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate that all required fields are present."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {missing_fields}")
    return True


def validate_list_structure(data: List[Any], min_length: int = 0, item_validator: Optional[callable] = None) -> bool:
    """Validate list structure and optionally validate items."""
    if not isinstance(data, list):
        raise ValidationError("Expected list")

    if len(data) < min_length:
        raise ValidationError(f"List must have at least {min_length} items")

    if item_validator:
        for i, item in enumerate(data):
            try:
                item_validator(item)
            except ValidationError as e:
                raise ValidationError(f"Item {i} validation failed: {str(e)}")

    return True