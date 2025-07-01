"""
JSON Utilities - Optimized JSON handling and processing

This module provides utilities for efficient JSON handling:
- Custom JSON encoders/decoders
- Performance optimizations for JSON processing
- JSON schema validation
- JSON transformation and filtering
"""

import json
import datetime
import decimal
import uuid
import re
import base64
import zlib
import functools
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable, TypeVar, Type
from collections import OrderedDict
import time
import os
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Try to import optional packages
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    logger.info("orjson not available, falling back to ujson or json")

try:
    import ujson
    HAS_UJSON = True
except ImportError:
    HAS_UJSON = False
    logger.info("ujson not available, falling back to standard json")

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    logger.info("jsonschema not available, schema validation will be limited")

# Import LRU cache (for Python < 3.9 compatibility)
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


def memoize_json(ttl: int = 300, maxsize: int = 128):
    """
    Decorator to cache results of JSON serialization based on function arguments
    
    Args:
        ttl: Time-to-live for cached entries in seconds (0 = no expiry)
        maxsize: Maximum number of items to keep in cache (0 = unlimited)
        
    Returns:
        Decorated function
    """
    cache = OrderedDict()
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function arguments
            key_parts = []
            
            # Add args to key parts
            for arg in args:
                if isinstance(arg, (dict, list, tuple)):
                    # For complex types, use a hash of the JSON representation
                    key_parts.append(hash(dumps(arg)))
                else:
                    # For simple types, use the value directly
                    key_parts.append(arg)
            
            # Add kwargs to key parts (sorted for consistency)
            for k in sorted(kwargs.keys()):
                v = kwargs[k]
                if isinstance(v, (dict, list, tuple)):
                    key_parts.append((k, hash(dumps(v))))
                else:
                    key_parts.append((k, v))
            
            # Create a hash of the key parts
            cache_key = hash(str(key_parts))
            
            # Check if result is in cache and not expired
            now = time.time()
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if ttl == 0 or now - timestamp < ttl:
                    # Move item to end (most recently used)
                    cache.move_to_end(cache_key)
                    return result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, now)
            
            # Enforce maxsize by removing oldest items
            if maxsize > 0:
                while len(cache) > maxsize:
                    cache.popitem(last=False)  # Remove oldest item
            
            return result
        
        # Add methods to clear the cache or get cache stats
        wrapper.clear_cache = lambda: cache.clear()
        wrapper.get_cache_info = lambda: {
            'hits': sum(1 for _, (_, ts) in cache.items() if ttl == 0 or time.time() - ts < ttl),
            'size': len(cache),
            'maxsize': maxsize,
            'ttl': ttl
        }
        
        return wrapper
    
    return decorator


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder with extended type support
    
    Handles Python types that are not natively supported by JSON:
    - datetime, date, time objects
    - Decimal
    - UUID
    - Enum
    - bytes/bytearray
    - sets
    - custom objects with to_dict or as_dict methods
    """
    
    def default(self, obj: Any) -> Any:
        # Handle datetime objects
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
            
        # Handle date objects
        if isinstance(obj, datetime.date):
            return obj.isoformat()
            
        # Handle time objects
        if isinstance(obj, datetime.time):
            return obj.isoformat()
            
        # Handle Decimal objects
        if isinstance(obj, decimal.Decimal):
            return float(obj)
            
        # Handle UUID objects
        if isinstance(obj, uuid.UUID):
            return str(obj)
            
        # Handle Enum objects
        if isinstance(obj, Enum):
            return obj.value
            
        # Handle bytes/bytearray
        if isinstance(obj, (bytes, bytearray)):
            return base64.b64encode(obj).decode('ascii')
            
        # Handle sets by converting to list
        if isinstance(obj, set):
            return list(obj)
            
        # Handle objects with to_dict or as_dict methods
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
            
        if hasattr(obj, 'as_dict') and callable(getattr(obj, 'as_dict')):
            return obj.as_dict()
            
        # Let the base class handle it or raise TypeError
        return super().default(obj)


def compress_json(json_data: str, level: int = 6) -> bytes:
    """
    Compress a JSON string using zlib
    
    Args:
        json_data: JSON string to compress
        level: Compression level (0-9, higher is more compressed but slower)
        
    Returns:
        Compressed bytes
    """
    try:
        if isinstance(json_data, str):
            json_bytes = json_data.encode('utf-8')
        else:
            json_bytes = json_data
            
        return zlib.compress(json_bytes, level)
    except Exception as e:
        logger.error(f"Error compressing JSON: {str(e)}")
        if isinstance(json_data, str):
            return json_data.encode('utf-8')
        return json_data


def decompress_json(compressed_data: bytes) -> str:
    """
    Decompress zlib-compressed JSON data back into a string
    
    Args:
        compressed_data: Compressed bytes from compress_json
        
    Returns:
        Original JSON string
    """
    try:
        decompressed = zlib.decompress(compressed_data)
        return decompressed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error decompressing JSON: {str(e)}")
        # If decompression fails, return the original data if possible
        try:
            return compressed_data.decode('utf-8')
        except:
            return str(compressed_data)


def dumps(obj: Any, pretty: bool = False, ensure_ascii: bool = False, 
         sort_keys: bool = False, use_orjson: bool = True,
         use_ujson: bool = False) -> str:
    """
    Serialize object to JSON string using the best available JSON library
    
    Args:
        obj: Object to serialize
        pretty: Whether to format the output with indentation
        ensure_ascii: Whether to escape non-ASCII characters
        sort_keys: Whether to sort dictionary keys
        use_orjson: Whether to try using orjson (fastest)
        use_ujson: Whether to try using ujson (faster than standard)
        
    Returns:
        JSON string
    """
    indent = 2 if pretty else None
    
    # Try orjson first if available and requested (fastest)
    if use_orjson and HAS_ORJSON:
        orjson_opts = 0
        if pretty:
            orjson_opts |= orjson.OPT_INDENT_2
        if not ensure_ascii:
            orjson_opts |= orjson.OPT_NON_STR_KEYS
        if sort_keys:
            orjson_opts |= orjson.OPT_SORT_KEYS
            
        # orjson returns bytes, so decode to string
        return orjson.dumps(obj, option=orjson_opts).decode('utf-8')
        
    # Try ujson next if available and requested (faster than standard)
    if use_ujson and HAS_UJSON:
        return ujson.dumps(
            obj,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys
        )
        
    # Fall back to standard json with custom encoder
    return json.dumps(
        obj,
        cls=CustomJSONEncoder,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys
    )


def loads(json_str: Union[str, bytes], use_orjson: bool = True, 
         use_ujson: bool = False) -> Any:
    """
    Deserialize JSON string using the best available JSON library
    
    Args:
        json_str: JSON string or bytes to deserialize
        use_orjson: Whether to try using orjson (fastest)
        use_ujson: Whether to try using ujson (faster than standard)
        
    Returns:
        Deserialized object
    """
    # Try orjson first if available and requested (fastest)
    if use_orjson and HAS_ORJSON:
        if isinstance(json_str, str):
            json_str = json_str.encode('utf-8')
        return orjson.loads(json_str)
        
    # Try ujson next if available and requested (faster than standard)
    if use_ujson and HAS_UJSON:
        return ujson.loads(json_str)
        
    # Fall back to standard json
    return json.loads(json_str)


def dump(obj: Any, fp, pretty: bool = False, ensure_ascii: bool = False,
        sort_keys: bool = False) -> None:
    """
    Serialize object to JSON file
    
    Args:
        obj: Object to serialize
        fp: File-like object to write to
        pretty: Whether to format the output with indentation
        ensure_ascii: Whether to escape non-ASCII characters
        sort_keys: Whether to sort dictionary keys
    """
    indent = 2 if pretty else None
    
    # Currently using standard json with custom encoder
    # Other libraries may not support file objects directly
    json.dump(
        obj,
        fp,
        cls=CustomJSONEncoder,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys
    )


def load(fp) -> Any:
    """
    Deserialize JSON from file
    
    Args:
        fp: File-like object to read from
        
    Returns:
        Deserialized object
    """
    return json.load(fp)


def parse_json(json_str: Union[str, bytes, None], 
              default: Any = None, 
              silent: bool = True) -> Any:
    """
    Safely parse JSON string with fallback to default value
    
    Args:
        json_str: JSON string or bytes to parse
        default: Default value to return if parsing fails
        silent: Whether to suppress exceptions
        
    Returns:
        Parsed JSON or default value
    """
    if not json_str:
        return default
        
    try:
        return loads(json_str)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        if silent:
            return default
        raise e


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate data against a JSON schema
    
    Args:
        data: Data to validate
        schema: JSON schema
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if HAS_JSONSCHEMA:
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            return False, str(e)
    else:
        # Very basic schema validation if jsonschema is not available
        if 'type' in schema and schema['type'] == 'object':
            if not isinstance(data, dict):
                return False, "Data is not an object"
                
            # Check required properties
            required = schema.get('required', [])
            for prop in required:
                if prop not in data:
                    return False, f"Missing required property: {prop}"
                    
            # Check property types
            properties = schema.get('properties', {})
            for prop, prop_schema in properties.items():
                if prop not in data:
                    continue
                    
                if 'type' in prop_schema:
                    value = data[prop]
                    type_valid = False
                    
                    if prop_schema['type'] == 'string' and isinstance(value, str):
                        type_valid = True
                    elif prop_schema['type'] == 'number' and isinstance(value, (int, float)):
                        type_valid = True
                    elif prop_schema['type'] == 'integer' and isinstance(value, int):
                        type_valid = True
                    elif prop_schema['type'] == 'boolean' and isinstance(value, bool):
                        type_valid = True
                    elif prop_schema['type'] == 'array' and isinstance(value, list):
                        type_valid = True
                    elif prop_schema['type'] == 'object' and isinstance(value, dict):
                        type_valid = True
                    elif prop_schema['type'] == 'null' and value is None:
                        type_valid = True
                        
                    if not type_valid:
                        return False, f"Invalid type for property {prop}"
                        
        return True, None


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], 
               overwrite: bool = True, deep_merge: bool = True) -> Dict[str, Any]:
    """
    Merge two dictionaries with optional deep merging
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        overwrite: Whether to overwrite existing keys
        deep_merge: Whether to recursively merge nested dictionaries
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        # Skip if key exists and we're not overwriting
        if not overwrite and key in result:
            continue
            
        # Deep merge nested dictionaries if requested
        if deep_merge and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, overwrite, deep_merge)
        else:
            result[key] = value
            
    return result


def flatten_json(data: Dict[str, Any], delimiter: str = '.', 
                prefix: str = '', max_depth: int = 10) -> Dict[str, Any]:
    """
    Flatten a nested JSON object into a flat dictionary with delimited keys
    
    Args:
        data: Nested dictionary
        delimiter: Delimiter for nested keys
        prefix: Prefix for all keys
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Flattened dictionary
    """
    result = {}
    
    def _flatten(obj: Dict[str, Any], current_prefix: str, current_depth: int) -> None:
        # Prevent infinite recursion
        if current_depth > max_depth:
            result[current_prefix] = obj
            return
            
        for key, value in obj.items():
            new_key = f"{current_prefix}{delimiter}{key}" if current_prefix else key
            
            if isinstance(value, dict) and value:
                _flatten(value, new_key, current_depth + 1)
            elif isinstance(value, list) and value:
                # Convert list to dictionary with indices as keys
                list_dict = {str(i): item for i, item in enumerate(value)}
                _flatten(list_dict, new_key, current_depth + 1)
            else:
                result[new_key] = value
                
    _flatten(data, prefix, 0)
    return result


def unflatten_json(data: Dict[str, Any], delimiter: str = '.') -> Dict[str, Any]:
    """
    Unflatten a flat dictionary with delimited keys into a nested JSON object
    
    Args:
        data: Flattened dictionary
        delimiter: Delimiter used for nested keys
        
    Returns:
        Nested dictionary
    """
    result = {}
    
    for key, value in data.items():
        parts = key.split(delimiter)
        
        # Navigate to the correct nested dictionary
        current = result
        for i, part in enumerate(parts[:-1]):
            # Check if the part represents a list index
            is_index = re.match(r'^\d+$', part)
            next_part = parts[i + 1]
            next_is_index = re.match(r'^\d+$', next_part)
            
            # Determine whether to create a list or dict
            if part not in current:
                if is_index:
                    current[part] = [] if next_is_index else {}
                else:
                    current[part] = [] if next_is_index else {}
                    
            # Move to the next level
            current = current[part]
            
        # Set the value at the final level
        last_part = parts[-1]
        current[last_part] = value
        
    return result


def filter_json(data: Dict[str, Any], include_keys: Optional[List[str]] = None,
               exclude_keys: Optional[List[str]] = None,
               key_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Filter and transform a JSON object
    
    Args:
        data: Dictionary to filter
        include_keys: List of keys to include (all if None)
        exclude_keys: List of keys to exclude
        key_mapping: Dictionary mapping original keys to new keys
        
    Returns:
        Filtered dictionary
    """
    if not isinstance(data, dict):
        return data
        
    exclude_keys = exclude_keys or []
    key_mapping = key_mapping or {}
    
    result = {}
    
    for key, value in data.items():
        # Skip excluded keys
        if key in exclude_keys:
            continue
            
        # Skip keys not in include_keys if include_keys is provided
        if include_keys is not None and key not in include_keys:
            continue
            
        # Map key if it's in the mapping
        new_key = key_mapping.get(key, key)
        
        # Add to result
        result[new_key] = value
        
    return result


def transform_json(data: Any, transform_function: Callable[[Any], Any]) -> Any:
    """
    Transform a JSON object by applying a function to all values
    
    Args:
        data: JSON-compatible data structure
        transform_function: Function to apply to each value
        
    Returns:
        Transformed data structure
    """
    if isinstance(data, dict):
        return {k: transform_json(v, transform_function) for k, v in data.items()}
    elif isinstance(data, list):
        return [transform_json(item, transform_function) for item in data]
    else:
        return transform_function(data)


def minify_json(json_str: str) -> str:
    """
    Minify a JSON string by removing whitespace
    
    Args:
        json_str: JSON string to minify
        
    Returns:
        Minified JSON string
    """
    if not json_str:
        return ''
        
    # Parse and re-serialize without pretty printing
    try:
        return dumps(loads(json_str), pretty=False)
    except (json.JSONDecodeError, ValueError):
        # If parsing fails, do basic whitespace removal
        return re.sub(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', '', json_str)


def prettify_json(json_str: str) -> str:
    """
    Prettify a JSON string with indentation
    
    Args:
        json_str: JSON string to prettify
        
    Returns:
        Prettified JSON string
    """
    if not json_str:
        return ''
        
    # Parse and re-serialize with pretty printing
    try:
        return dumps(loads(json_str), pretty=True)
    except (json.JSONDecodeError, ValueError):
        # Return original string if parsing fails
        return json_str


def extract_path(data: Any, path: str, default: Any = None, 
                delimiter: str = '.') -> Any:
    """
    Extract a value from a nested JSON object using a path
    
    Args:
        data: JSON-compatible data structure
        path: Path to the value (e.g., 'user.profile.name')
        default: Default value if path doesn't exist
        delimiter: Delimiter used in the path
        
    Returns:
        Extracted value or default
    """
    if not path:
        return data
        
    parts = path.split(delimiter)
    current = data
    
    for part in parts:
        # Handle array indices
        if part.isdigit() and isinstance(current, list):
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
            else:
                return default
        # Handle dictionary keys
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
            
    return current


def set_path(data: Dict[str, Any], path: str, value: Any, 
            delimiter: str = '.', create_missing: bool = True) -> Dict[str, Any]:
    """
    Set a value in a nested JSON object using a path
    
    Args:
        data: Dictionary to modify
        path: Path to the value (e.g., 'user.profile.name')
        value: Value to set
        delimiter: Delimiter used in the path
        create_missing: Whether to create missing nested objects
        
    Returns:
        Modified dictionary
    """
    if not path:
        return data
        
    parts = path.split(delimiter)
    current = data
    
    # Navigate to the parent of the final value
    for i, part in enumerate(parts[:-1]):
        # If we're creating missing parts
        if create_missing and (part not in current or current[part] is None):
            # Check if the next part is a number, indicating an array
            next_part = parts[i + 1]
            if next_part.isdigit():
                current[part] = []
            else:
                current[part] = {}
                
        # If the current part exists but isn't a container
        if not isinstance(current.get(part), (dict, list)):
            if create_missing:
                current[part] = {}
            else:
                return data
                
        current = current[part]
        
        # If we hit a list, handle specially
        if isinstance(current, list):
            next_part = parts[i + 1]
            if next_part.isdigit():
                index = int(next_part)
                # Extend the list if needed
                while len(current) <= index:
                    current.append(None)
                    
                # If this is not the last part, ensure the indexed item is a container
                if i + 2 < len(parts):
                    if current[index] is None or not isinstance(current[index], (dict, list)):
                        current[index] = {}
                        
                current = current[index]
                
                # Skip the next part since we've consumed it
                i += 1
                
    # Set the value at the final level
    last_part = parts[-1]
    
    # Handle array indices in the final part
    if last_part.isdigit() and isinstance(current, list):
        index = int(last_part)
        # Extend the list if needed
        while len(current) <= index:
            current.append(None)
        current[index] = value
    else:
        current[last_part] = value
        
    return data


def diff_json(obj1: Any, obj2: Any, 
             path: str = '', 
             ignore_keys: Optional[List[str]] = None) -> Dict[str, Tuple[Any, Any]]:
    """
    Find differences between two JSON objects
    
    Args:
        obj1: First object
        obj2: Second object
        path: Current path (used in recursion)
        ignore_keys: Keys to ignore when comparing
        
    Returns:
        Dictionary with paths as keys and tuples of (obj1_value, obj2_value) as values
    """
    ignore_keys = ignore_keys or []
    differences = {}
    
    # Handle None values
    if obj1 is None and obj2 is None:
        return differences
    elif obj1 is None:
        return {path: (None, obj2)}
    elif obj2 is None:
        return {path: (obj1, None)}
        
    # Handle different types
    if type(obj1) != type(obj2):
        return {path: (obj1, obj2)}
        
    # Handle dictionaries
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        # Get all keys from both dictionaries
        all_keys = set(obj1.keys()) | set(obj2.keys())
        
        for key in all_keys:
            # Skip ignored keys
            if key in ignore_keys:
                continue
                
            # Compute the new path
            new_path = f"{path}.{key}" if path else key
            
            # Handle keys present only in one dictionary
            if key not in obj1:
                differences[new_path] = (None, obj2[key])
            elif key not in obj2:
                differences[new_path] = (obj1[key], None)
            else:
                # Recursive comparison
                nested_diff = diff_json(obj1[key], obj2[key], new_path, ignore_keys)
                differences.update(nested_diff)
                
    # Handle lists
    elif isinstance(obj1, list) and isinstance(obj2, list):
        # Compare items at the same indices
        for i in range(max(len(obj1), len(obj2))):
            # Compute the new path
            new_path = f"{path}[{i}]"
            
            # Handle indices present only in one list
            if i >= len(obj1):
                differences[new_path] = (None, obj2[i])
            elif i >= len(obj2):
                differences[new_path] = (obj1[i], None)
            else:
                # Recursive comparison
                nested_diff = diff_json(obj1[i], obj2[i], new_path, ignore_keys)
                differences.update(nested_diff)
                
    # Handle primitive values
    elif obj1 != obj2:
        differences[path] = (obj1, obj2)
        
    return differences


def json_to_csv(data: List[Dict[str, Any]], 
               include_headers: bool = True,
               delimiter: str = ',') -> str:
    """
    Convert a list of JSON objects to CSV string
    
    Args:
        data: List of dictionaries to convert
        include_headers: Whether to include headers
        delimiter: Delimiter for CSV fields
        
    Returns:
        CSV string
    """
    if not data:
        return ""
        
    # Get all unique keys from all objects
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
        
    # Sort keys for consistent output
    sorted_keys = sorted(all_keys)
    
    lines = []
    
    # Add headers
    if include_headers:
        header_line = delimiter.join(f'"{key}"' for key in sorted_keys)
        lines.append(header_line)
        
    # Add data rows
    for item in data:
        values = []
        for key in sorted_keys:
            value = item.get(key, "")
            
            # Format value based on type
            if value is None:
                formatted = ""
            elif isinstance(value, (dict, list)):
                formatted = f'"{dumps(value).replace('"', '""')}"'
            elif isinstance(value, str):
                formatted = f'"{value.replace('"', '""')}"'
            else:
                formatted = str(value)
                
            values.append(formatted)
            
        lines.append(delimiter.join(values))
        
    return "\n".join(lines)


def csv_to_json(csv_str: str, 
               has_headers: bool = True, 
               delimiter: str = ',') -> List[Dict[str, Any]]:
    """
    Convert a CSV string to a list of JSON objects
    
    Args:
        csv_str: CSV string to convert
        has_headers: Whether the CSV has headers
        delimiter: Delimiter for CSV fields
        
    Returns:
        List of dictionaries
    """
    if not csv_str:
        return []
        
    lines = csv_str.strip().split('\n')
    if not lines:
        return []
        
    result = []
    
    # Parse headers
    if has_headers:
        header_line = lines[0]
        headers = _parse_csv_line(header_line, delimiter)
        data_lines = lines[1:]
    else:
        # Generate numeric column names
        data_lines = lines
        first_line = _parse_csv_line(data_lines[0], delimiter)
        headers = [f"column{i}" for i in range(len(first_line))]
        
    # Parse data
    for line in data_lines:
        if not line.strip():
            continue
            
        values = _parse_csv_line(line, delimiter)
        
        # Create object with minimum of values and headers length
        obj = {}
        for i in range(min(len(headers), len(values))):
            value = values[i]
            
            # Try to parse JSON values
            if value and value[0] == '{' and value[-1] == '}':
                try:
                    value = loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
                    
            obj[headers[i]] = value
            
        result.append(obj)
        
    return result


def _parse_csv_line(line: str, delimiter: str) -> List[str]:
    """
    Parse a single CSV line handling quoted fields
    
    Args:
        line: CSV line to parse
        delimiter: Delimiter for CSV fields
        
    Returns:
        List of field values
    """
    result = []
    current = ""
    in_quotes = False
    i = 0
    
    while i < len(line):
        char = line[i]
        
        # Handle quotes
        if char == '"':
            # Check for escaped quotes
            if i + 1 < len(line) and line[i + 1] == '"':
                current += '"'
                i += 2
                continue
                
            # Toggle quote mode
            in_quotes = not in_quotes
            i += 1
            continue
            
        # Handle delimiters
        if char == delimiter and not in_quotes:
            result.append(current)
            current = ""
            i += 1
            continue
            
        # Add character to current field
        current += char
        i += 1
        
    # Add the last field
    result.append(current)
    
    return result


def is_json_serializable(obj: Any) -> bool:
    """
    Check if an object can be serialized to JSON
    
    Args:
        obj: Object to check
        
    Returns:
        True if serializable, False otherwise
    """
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def make_json_serializable(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable form
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable object
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
        
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode('ascii')
        
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
        
    if isinstance(obj, decimal.Decimal):
        return float(obj)
        
    if isinstance(obj, uuid.UUID):
        return str(obj)
        
    if isinstance(obj, Enum):
        return obj.value
        
    if isinstance(obj, set):
        return list(obj)
        
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
        
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
        
    if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        return make_json_serializable(obj.to_dict())
        
    if hasattr(obj, 'as_dict') and callable(getattr(obj, 'as_dict')):
        return make_json_serializable(obj.as_dict())
        
    if hasattr(obj, '__dict__'):
        return make_json_serializable(obj.__dict__)
        
    # Last resort: convert to string
    return str(obj)


def timed_json_operation(threshold_ms: float = 100):
    """
    Decorator to time JSON operations and log slow operations
    
    Args:
        threshold_ms: Threshold in milliseconds to consider operation slow
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = (time.time() - start_time) * 1000  # ms
            
            func_name = func.__name__
            if elapsed_time > threshold_ms:
                logger.warning(f"Slow JSON operation: {func_name} took {elapsed_time:.2f}ms")
            else:
                logger.debug(f"JSON operation: {func_name} took {elapsed_time:.2f}ms")
                
            return result
        return wrapper
    return decorator


@lru_cache(maxsize=128)
def cached_load(file_path: str) -> Any:
    """
    Load and cache JSON data from a file
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return loads(f.read())


def load_json_file(file_path: str, use_cache: bool = True) -> Any:
    """
    Load JSON data from a file, with optional caching
    
    Args:
        file_path: Path to JSON file
        use_cache: Whether to use cached result if available
        
    Returns:
        Parsed JSON data
    """
    try:
        if use_cache:
            # Use the cached version if available
            return cached_load(file_path)
        
        # Otherwise load directly
        with open(file_path, 'r', encoding='utf-8') as f:
            return loads(f.read())
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        return None


def save_json_file(file_path: str, data: Any, pretty: bool = False, 
                  compress: bool = False) -> bool:
    """
    Save JSON data to a file
    
    Args:
        file_path: Path to save JSON file
        data: Data to serialize and save
        pretty: Whether to format with indentation
        compress: Whether to compress the data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Serialize the data
        json_str = dumps(data, pretty=pretty)
        
        if compress:
            # Save compressed data
            compressed = compress_json(json_str)
            with open(file_path, 'wb') as f:
                f.write(compressed)
        else:
            # Save uncompressed
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
                
        # Invalidate cache for this file
        if file_path in cached_load.cache_info()[0]:
            cached_load.cache_clear()
            
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {str(e)}")
        return False


def json_response(data: Any, status: str = "success", code: int = 200, 
                 meta: Optional[Dict] = None) -> Dict:
    """
    Prepare a standard JSON response
    
    Args:
        data: Response data
        status: Status string (success, error, etc.)
        code: HTTP status code
        meta: Optional metadata
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "status": status,
        "code": code,
        "data": data,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    
    if meta:
        response["meta"] = meta
        
    return response


class JsonCache:
    """Cache handler for JSON data with TTL support"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize the cache
        
        Args:
            max_size: Maximum number of items to cache
            ttl: Default TTL in seconds
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = ttl
        self.expiry = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        # Check if key exists and not expired
        now = time.time()
        if key in self.cache and self.expiry.get(key, now + 1) > now:
            # Move to end (mark as recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
            
        # Remove if expired
        elif key in self.cache:
            self.cache.pop(key)
            self.expiry.pop(key, None)
            
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Add item to cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds, None for default
        """
        # Remove if exists
        if key in self.cache:
            self.cache.pop(key)
            self.expiry.pop(key, None)
            
        # If at max size, remove oldest
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            self.cache.pop(oldest)
            self.expiry.pop(oldest, None)
            
        # Add new item
        self.cache[key] = value
        
        # Set expiry
        if ttl is not None:
            self.expiry[key] = time.time() + ttl
        elif self.default_ttl:
            self.expiry[key] = time.time() + self.default_ttl
    
    def delete(self, key: str) -> bool:
        """
        Remove item from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if removed, False if not found
        """
        if key in self.cache:
            self.cache.pop(key)
            self.expiry.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached items"""
        self.cache.clear()
        self.expiry.clear()
    
    def cleanup(self) -> int:
        """
        Remove expired items
        
        Returns:
            Number of items removed
        """
        now = time.time()
        expired_keys = [
            key for key, expiry in self.expiry.items() 
            if expiry <= now
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
            
        return len(expired_keys)


def memoize_json(max_size: int = 100, ttl: Optional[int] = None, 
                compress: bool = False):
    """
    Decorator to memoize JSON serialization results
    
    Args:
        max_size: Maximum items to cache
        ttl: Time to live in seconds, None for no expiry
        compress: Whether to compress cached data
        
    Returns:
        Decorated function
    """
    # Create cache for this decorator instance
    cache = {}
    expiry = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function arguments
            key_parts = [func.__name__]
            
            # Add positional args to key
            for arg in args:
                key_parts.append(str(arg))
                
            # Add keyword args to key (sorted for consistency)
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                key_parts.append(f"{k}={v}")
                
            # Create key
            key = ":".join(key_parts)
            
            # Check for cached result
            now = time.time()
            if key in cache:
                # Check if expired
                if ttl is None or expiry.get(key, now + 1) > now:
                    # Use cached result
                    result = cache[key]
                    
                    # Decompress if needed
                    if compress and isinstance(result, bytes):
                        return decompress_json(result)
                    return result
                
                # Remove expired result
                cache.pop(key)
                expiry.pop(key, None)
            
            # Generate new result
            result = func(*args, **kwargs)
            
            # Store in cache
            if compress and isinstance(result, str):
                cache[key] = compress_json(result)
            else:
                cache[key] = result
                
            # Set expiry
            if ttl is not None:
                expiry[key] = now + ttl
                
            # Limit cache size
            if len(cache) > max_size:
                # Get oldest item (approximation)
                oldest_key = next(iter(cache))
                cache.pop(oldest_key)
                expiry.pop(oldest_key, None)
                
            return result
        
        # Add cache management functions
        def clear_cache():
            cache.clear()
            expiry.clear()
        
        def get_cache_info():
            return {
                "size": len(cache),
                "max_size": max_size,
                "ttl": ttl,
                "compress": compress
            }
        
        wrapper.clear_cache = clear_cache
        wrapper.cache_info = get_cache_info
        
        return wrapper
    
    return decorator 