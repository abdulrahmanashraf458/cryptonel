"""
Validation Utilities - Input validation, schema validation, and data normalization

This module provides utilities for validating and normalizing data:
- Schema-based validation (JSON Schema, Pydantic, etc.)
- Type validation and conversion
- Data normalization
- Custom validation rules
"""

import re
import json
import datetime
import decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Type, Callable

# Try to import validation libraries with fallbacks
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from pydantic import BaseModel, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

# Type variable for generic functions
T = TypeVar('T')

# Common error messages
ERROR_MESSAGES = {
    "required": "This field is required",
    "min_length": "Value is too short (minimum length: {min_length})",
    "max_length": "Value is too long (maximum length: {max_length})",
    "pattern": "Value does not match the required pattern",
    "min_value": "Value is too small (minimum value: {min_value})",
    "max_value": "Value is too large (maximum value: {max_value})",
    "invalid_type": "Invalid type, expected {expected_type}",
    "invalid_format": "Invalid format, expected {expected_format}",
    "invalid_choice": "Invalid choice, must be one of: {choices}",
}


class ValidationError(Exception):
    """Custom validation error with detailed error information"""
    
    def __init__(self, field: str = "", message: str = "", code: str = "",
                errors: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize a validation error
        
        Args:
            field: Name of the field with the error
            message: Error message
            code: Error code for programmatic handling
            errors: List of nested validation errors
        """
        self.field = field
        self.message = message
        self.code = code
        self.errors = errors or []
        
        # Build error message
        error_msg = message or "Validation error"
        if field:
            error_msg = f"{field}: {error_msg}"
            
        # Initialize the base exception
        super().__init__(error_msg)
        
    def add_error(self, field: str, message: str, code: str = "") -> None:
        """
        Add a nested validation error
        
        Args:
            field: Name of the field with the error
            message: Error message
            code: Error code for programmatic handling
        """
        self.errors.append({
            "field": field,
            "message": message,
            "code": code
        })
        
    def as_dict(self) -> Dict[str, Any]:
        """
        Convert the validation error to a dictionary
        
        Returns:
            Dictionary representation of the error
        """
        result = {
            "message": self.message,
        }
        
        if self.field:
            result["field"] = self.field
            
        if self.code:
            result["code"] = self.code
            
        if self.errors:
            result["errors"] = self.errors
            
        return result


def validate_type(value: Any, expected_type: Union[Type, Tuple[Type, ...]],
                field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is of the expected type
    
    Args:
        value: Value to validate
        expected_type: Expected type or tuple of types
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle None values
    if value is None:
        return True, None
        
    if not isinstance(value, expected_type):
        type_names = []
        if isinstance(expected_type, tuple):
            type_names = [t.__name__ for t in expected_type]
        else:
            type_names = [expected_type.__name__]
            
        expected_type_str = " or ".join(type_names)
        field_prefix = f"{field_name}: " if field_name else ""
        
        return False, f"{field_prefix}Expected {expected_type_str}, got {type(value).__name__}"
        
    return True, None


def validate_string(value: str, min_length: Optional[int] = None,
                   max_length: Optional[int] = None, 
                   pattern: Optional[str] = None,
                   field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a string value
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        pattern: Regular expression pattern
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, str, field_name)
    if not is_valid:
        return False, error
        
    # Check minimum length
    if min_length is not None and len(value) < min_length:
        return False, f"{field_prefix}String too short (minimum length: {min_length})"
        
    # Check maximum length
    if max_length is not None and len(value) > max_length:
        return False, f"{field_prefix}String too long (maximum length: {max_length})"
        
    # Check pattern
    if pattern is not None and not re.match(pattern, value):
        return False, f"{field_prefix}String does not match the required pattern"
        
    return True, None


def validate_number(value: Union[int, float, decimal.Decimal],
                   min_value: Optional[Union[int, float, decimal.Decimal]] = None,
                   max_value: Optional[Union[int, float, decimal.Decimal]] = None,
                   field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a numeric value
    
    Args:
        value: Number to validate
        min_value: Minimum value
        max_value: Maximum value
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, (int, float, decimal.Decimal), field_name)
    if not is_valid:
        return False, error
        
    # Check minimum value
    if min_value is not None and value < min_value:
        return False, f"{field_prefix}Value too small (minimum: {min_value})"
        
    # Check maximum value
    if max_value is not None and value > max_value:
        return False, f"{field_prefix}Value too large (maximum: {max_value})"
        
    return True, None


def validate_boolean(value: Any, field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a boolean value
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # First check if it's already a boolean
    if isinstance(value, bool):
        return True, None
        
    # Try to convert common string representations
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ('true', 'yes', '1', 'y', 't'):
            return True, None
        if lower_value in ('false', 'no', '0', 'n', 'f'):
            return True, None
            
    # Try to convert numeric representations
    if isinstance(value, (int, float)) and value in (0, 1):
        return True, None
        
    field_prefix = f"{field_name}: " if field_name else ""
    return False, f"{field_prefix}Expected a boolean value"


def validate_list(value: List[Any], item_validator: Optional[Callable[[Any], Tuple[bool, Optional[str]]]] = None,
                 min_length: Optional[int] = None, max_length: Optional[int] = None,
                 field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a list and optionally its items
    
    Args:
        value: List to validate
        item_validator: Function to validate each item
        min_length: Minimum list length
        max_length: Maximum list length
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, list, field_name)
    if not is_valid:
        return False, error
        
    # Check minimum length
    if min_length is not None and len(value) < min_length:
        return False, f"{field_prefix}List too short (minimum length: {min_length})"
        
    # Check maximum length
    if max_length is not None and len(value) > max_length:
        return False, f"{field_prefix}List too long (maximum length: {max_length})"
        
    # Validate each item if an item validator is provided
    if item_validator:
        for i, item in enumerate(value):
            item_field = f"{field_name}[{i}]" if field_name else f"item[{i}]"
            is_valid, error = item_validator(item)
            if not is_valid:
                return False, error
                
    return True, None


def validate_dict(value: Dict[str, Any], 
                 schema: Optional[Dict[str, Any]] = None,
                 field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a dictionary against a schema
    
    Args:
        value: Dictionary to validate
        schema: Dictionary schema with field validators
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, dict, field_name)
    if not is_valid:
        return False, error
        
    # If no schema is provided, just validate the type
    if schema is None:
        return True, None
        
    # Validate against schema
    for key, validator in schema.items():
        # Check required fields
        if key not in value and validator.get('required', False):
            return False, f"{field_prefix}Missing required field: {key}"
            
        # Skip validation for missing optional fields
        if key not in value:
            continue
            
        # Get the field value
        field_value = value[key]
        
        # Get the field validator
        field_validator = validator.get('validator')
        if field_validator:
            nested_field_name = f"{field_name}.{key}" if field_name else key
            is_valid, error = field_validator(field_value, field_name=nested_field_name)
            if not is_valid:
                return False, error
                
    return True, None


def validate_enum(value: Any, enum_class: Type[Enum], 
                 field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a value against an Enum
    
    Args:
        value: Value to validate
        enum_class: Enum class to validate against
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check if the value is already an instance of the enum
    if isinstance(value, enum_class):
        return True, None
        
    # Check if the value matches any enum values
    try:
        # Try to get enum by value
        enum_class(value)
        return True, None
    except ValueError:
        try:
            # Try to get enum by name
            if isinstance(value, str):
                enum_class[value]
                return True, None
        except KeyError:
            pass
            
    # Build error message with valid choices
    choices = [str(item.value) for item in enum_class]
    choices_str = ", ".join(choices)
    return False, f"{field_prefix}Invalid value. Must be one of: {choices_str}"


def validate_email(value: str, field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate an email address
    
    Args:
        value: Email address to validate
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, str, field_name)
    if not is_valid:
        return False, error
        
    # Use a regex pattern for basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        return False, f"{field_prefix}Invalid email address format"
        
    return True, None


def validate_url(value: str, require_https: bool = False,
               field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a URL
    
    Args:
        value: URL to validate
        require_https: Whether to require HTTPS
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Check type
    is_valid, error = validate_type(value, str, field_name)
    if not is_valid:
        return False, error
        
    # Use a regex pattern for basic URL validation
    url_pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(/[-\w%!$&\'()*+,;=:]+)*(?:\?[-\w%!$&\'()*+,;=:/?]+)?$'
    if not re.match(url_pattern, value):
        return False, f"{field_prefix}Invalid URL format"
        
    # Check for HTTPS if required
    if require_https and not value.startswith('https://'):
        return False, f"{field_prefix}URL must use HTTPS"
        
    return True, None


def validate_date(value: Union[str, datetime.date, datetime.datetime],
                 min_date: Optional[Union[str, datetime.date, datetime.datetime]] = None,
                 max_date: Optional[Union[str, datetime.date, datetime.datetime]] = None,
                 format_str: str = "%Y-%m-%d",
                 field_name: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate a date
    
    Args:
        value: Date to validate
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        format_str: Format string for parsing string dates
        field_name: Name of the field (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    field_prefix = f"{field_name}: " if field_name else ""
    
    # Convert string dates to datetime objects
    date_value = value
    if isinstance(value, str):
        try:
            date_value = datetime.datetime.strptime(value, format_str).date()
        except ValueError:
            return False, f"{field_prefix}Invalid date format, expected {format_str}"
    elif isinstance(value, datetime.datetime):
        date_value = value.date()
    elif not isinstance(value, datetime.date):
        return False, f"{field_prefix}Expected date, got {type(value).__name__}"
        
    # Convert min and max dates if they are strings
    if isinstance(min_date, str):
        try:
            min_date = datetime.datetime.strptime(min_date, format_str).date()
        except ValueError:
            raise ValueError(f"Invalid min_date format, expected {format_str}")
            
    if isinstance(max_date, str):
        try:
            max_date = datetime.datetime.strptime(max_date, format_str).date()
        except ValueError:
            raise ValueError(f"Invalid max_date format, expected {format_str}")
            
    # Convert datetime objects to date
    if isinstance(min_date, datetime.datetime):
        min_date = min_date.date()
        
    if isinstance(max_date, datetime.datetime):
        max_date = max_date.date()
        
    # Check minimum date
    if min_date is not None and date_value < min_date:
        return False, f"{field_prefix}Date cannot be earlier than {min_date}"
        
    # Check maximum date
    if max_date is not None and date_value > max_date:
        return False, f"{field_prefix}Date cannot be later than {max_date}"
        
    return True, None


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any],
                   raise_exception: bool = True) -> Union[bool, Dict[str, Any]]:
    """
    Validate data against a JSON Schema
    
    Args:
        data: Data to validate
        schema: JSON Schema
        raise_exception: Whether to raise an exception for validation errors
        
    Returns:
        True if valid, errors dictionary if invalid and raise_exception is False
        
    Raises:
        ValidationError: If validation fails and raise_exception is True
    """
    if HAS_JSONSCHEMA:
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            if raise_exception:
                # Convert jsonschema error to our custom ValidationError
                raise ValidationError(
                    field=e.path[-1] if e.path else "",
                    message=e.message,
                    code="schema_error"
                )
            return {"errors": str(e)}
    else:
        # Basic validation without jsonschema
        errors = {}
        
        # Check required properties
        required = schema.get('required', [])
        for prop in required:
            if prop not in data:
                errors[prop] = ERROR_MESSAGES["required"]
                
        # Check property types and formats
        properties = schema.get('properties', {})
        for prop, prop_schema in properties.items():
            if prop not in data:
                continue
                
            # Check type
            if 'type' in prop_schema:
                expected_type = prop_schema['type']
                value = data[prop]
                
                if expected_type == 'string' and not isinstance(value, str):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='string')
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='number')
                elif expected_type == 'integer' and not isinstance(value, int):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='integer')
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='boolean')
                elif expected_type == 'array' and not isinstance(value, list):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='array')
                elif expected_type == 'object' and not isinstance(value, dict):
                    errors[prop] = ERROR_MESSAGES["invalid_type"].format(expected_type='object')
                    
            # Check string constraints
            if prop_schema.get('type') == 'string' and prop in data:
                value = data[prop]
                if not isinstance(value, str):
                    continue
                    
                if 'minLength' in prop_schema and len(value) < prop_schema['minLength']:
                    errors[prop] = ERROR_MESSAGES["min_length"].format(min_length=prop_schema['minLength'])
                    
                if 'maxLength' in prop_schema and len(value) > prop_schema['maxLength']:
                    errors[prop] = ERROR_MESSAGES["max_length"].format(max_length=prop_schema['maxLength'])
                    
                if 'pattern' in prop_schema and not re.match(prop_schema['pattern'], value):
                    errors[prop] = ERROR_MESSAGES["pattern"]
                    
            # Check numeric constraints
            if prop_schema.get('type') in ('number', 'integer') and prop in data:
                value = data[prop]
                if not isinstance(value, (int, float)):
                    continue
                    
                if 'minimum' in prop_schema and value < prop_schema['minimum']:
                    errors[prop] = ERROR_MESSAGES["min_value"].format(min_value=prop_schema['minimum'])
                    
                if 'maximum' in prop_schema and value > prop_schema['maximum']:
                    errors[prop] = ERROR_MESSAGES["max_value"].format(max_value=prop_schema['maximum'])
                    
            # Check array constraints
            if prop_schema.get('type') == 'array' and prop in data:
                value = data[prop]
                if not isinstance(value, list):
                    continue
                    
                if 'minItems' in prop_schema and len(value) < prop_schema['minItems']:
                    errors[prop] = ERROR_MESSAGES["min_length"].format(min_length=prop_schema['minItems'])
                    
                if 'maxItems' in prop_schema and len(value) > prop_schema['maxItems']:
                    errors[prop] = ERROR_MESSAGES["max_length"].format(max_length=prop_schema['maxItems'])
                    
            # Check enum constraints
            if 'enum' in prop_schema and prop in data:
                value = data[prop]
                if value not in prop_schema['enum']:
                    choices_str = ", ".join([str(c) for c in prop_schema['enum']])
                    errors[prop] = ERROR_MESSAGES["invalid_choice"].format(choices=choices_str)
                    
        if errors and raise_exception:
            # Create a ValidationError with all field errors
            error = ValidationError(message="Schema validation failed")
            for field, message in errors.items():
                error.add_error(field=field, message=message, code="schema_error")
            raise error
            
        return True if not errors else {"errors": errors}


def validate_with_model(data: Dict[str, Any], model_class: Type[Any]) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Validate data using a Pydantic model or similar
    
    Args:
        data: Data to validate
        model_class: Model class to validate against (Pydantic BaseModel or similar)
        
    Returns:
        Tuple of (validated_model, errors)
    """
    if HAS_PYDANTIC and issubclass(model_class, BaseModel):
        try:
            model_instance = model_class(**data)
            return model_instance, None
        except ValidationError as e:
            # Convert Pydantic validation errors to a dictionary
            return None, {"errors": e.errors()}
    else:
        # Fallback to basic validation using model's __init__ parameters
        try:
            model_instance = model_class(**data)
            return model_instance, None
        except Exception as e:
            return None, {"errors": str(e)}


def normalize_string(value: str) -> str:
    """
    Normalize a string by trimming whitespace and handling None
    
    Args:
        value: String to normalize
        
    Returns:
        Normalized string
    """
    if value is None:
        return ""
    return str(value).strip()


def normalize_int(value: Any, default: int = 0) -> int:
    """
    Normalize a value to an integer
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        
    Returns:
        Integer value
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, str):
            # Remove commas and other formatting characters
            clean_value = value.replace(',', '').strip()
            return int(float(clean_value))
        return int(value)
    except (ValueError, TypeError):
        return default


def normalize_float(value: Any, default: float = 0.0, precision: int = None) -> float:
    """
    Normalize a value to a float
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        precision: Number of decimal places (if not None)
        
    Returns:
        Float value
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, str):
            # Remove commas and other formatting characters
            clean_value = value.replace(',', '').strip()
            result = float(clean_value)
        else:
            result = float(value)
            
        if precision is not None:
            result = round(result, precision)
            
        return result
    except (ValueError, TypeError):
        return default


def normalize_boolean(value: Any, default: bool = False) -> bool:
    """
    Normalize a value to a boolean
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        
    Returns:
        Boolean value
    """
    if value is None:
        return default
        
    if isinstance(value, bool):
        return value
        
    if isinstance(value, (int, float)):
        return bool(value)
        
    if isinstance(value, str):
        lower_value = value.lower().strip()
        if lower_value in ('true', 'yes', '1', 'y', 't'):
            return True
        if lower_value in ('false', 'no', '0', 'n', 'f'):
            return False
            
    return default


def normalize_list(value: Any, item_type: Type = str, default: List = None) -> List:
    """
    Normalize a value to a list
    
    Args:
        value: Value to normalize
        item_type: Type to convert list items to
        default: Default value if conversion fails
        
    Returns:
        List of normalized items
    """
    if default is None:
        default = []
        
    if value is None:
        return default.copy()
        
    if isinstance(value, str):
        # Try to parse JSON array
        if value.strip().startswith('[') and value.strip().endswith(']'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                # Fallback to comma-separated list
                value = [v.strip() for v in value.split(',') if v.strip()]
        else:
            # Treat as comma-separated list
            value = [v.strip() for v in value.split(',') if v.strip()]
            
    if not isinstance(value, (list, tuple, set)):
        # Convert single value to list
        value = [value]
        
    # Convert each item to the specified type
    result = []
    for item in value:
        try:
            if item_type == bool:
                result.append(normalize_boolean(item))
            elif item_type == int:
                result.append(normalize_int(item))
            elif item_type == float:
                result.append(normalize_float(item))
            elif item_type == str:
                result.append(normalize_string(item))
            else:
                result.append(item_type(item))
        except (ValueError, TypeError):
            # Skip items that can't be converted
            pass
            
    return result


def normalize_dict(value: Any, default: Dict = None) -> Dict:
    """
    Normalize a value to a dictionary
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        
    Returns:
        Dictionary
    """
    if default is None:
        default = {}
        
    if value is None:
        return default.copy()
        
    if isinstance(value, str):
        # Try to parse JSON object
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return default.copy()
            
    if isinstance(value, dict):
        return value
        
    return default.copy()


def normalize_date(value: Any, default: Optional[datetime.date] = None,
                  format_str: str = "%Y-%m-%d") -> Optional[datetime.date]:
    """
    Normalize a value to a date
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        format_str: Format string for parsing string dates
        
    Returns:
        Date object or default
    """
    if value is None:
        return default
        
    if isinstance(value, datetime.date):
        if isinstance(value, datetime.datetime):
            return value.date()
        return value
        
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(value, format_str).date()
        except ValueError:
            pass
            
    return default


def normalize_datetime(value: Any, default: Optional[datetime.datetime] = None,
                      format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime.datetime]:
    """
    Normalize a value to a datetime
    
    Args:
        value: Value to normalize
        default: Default value if conversion fails
        format_str: Format string for parsing string datetimes
        
    Returns:
        Datetime object or default
    """
    if value is None:
        return default
        
    if isinstance(value, datetime.datetime):
        return value
        
    if isinstance(value, datetime.date):
        # Convert date to datetime at midnight
        return datetime.datetime.combine(value, datetime.time.min)
        
    if isinstance(value, str):
        try:
            # Try multiple formats
            formats = [
                format_str,
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(value, fmt)
                except ValueError:
                    continue
        except ValueError:
            pass
            
    return default


def normalize_phone(value: str, country_code: str = "+1") -> str:
    """
    Normalize a phone number
    
    Args:
        value: Phone number to normalize
        country_code: Default country code
        
    Returns:
        Normalized phone number
    """
    if value is None:
        return ""
        
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', value)
    
    # Handle empty case
    if not digits_only:
        return ""
        
    # Add country code if needed
    if country_code and not digits_only.startswith(country_code.replace('+', '')):
        # If the number starts with a leading '1' for US/CA
        if country_code == "+1" and digits_only.startswith('1') and len(digits_only) > 10:
            # Already has country code without the plus
            pass
        else:
            # Add country code without the plus
            digits_only = country_code.replace('+', '') + digits_only
            
    # Format with plus
    if not digits_only.startswith('+'):
        return f"+{digits_only}"
        
    return digits_only


def normalize_email(value: str) -> str:
    """
    Normalize an email address
    
    Args:
        value: Email address to normalize
        
    Returns:
        Normalized email address
    """
    if value is None:
        return ""
        
    # Convert to lowercase and strip whitespace
    email = value.lower().strip()
    
    # Basic validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return ""
        
    return email 