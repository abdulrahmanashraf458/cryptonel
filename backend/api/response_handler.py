"""
Response Handler - Optimized API response handling

This module provides utilities for standardizing and optimizing API responses,
including compression, caching, and proper error handling.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from http import HTTPStatus

from backend.utils.json_utils import dumps as json_dumps, compress_json, merge_dicts, json_response, memoize_json

# Configure logger
logger = logging.getLogger(__name__)


class ApiResponse:
    """Standardized API response format with performance optimizations"""
    
    def __init__(self, data: Any = None, status_code: int = HTTPStatus.OK, 
                 message: str = "", errors: List[Dict] = None):
        """
        Initialize an API response
        
        Args:
            data: Response payload
            status_code: HTTP status code
            message: Response message
            errors: List of error details
        """
        self.data = data
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        self.meta = {
            "timestamp": time.time(),
            "version": "1.0"
        }
        
    def to_dict(self, compress: bool = False) -> Dict[str, Any]:
        """
        Convert response to dictionary format
        
        Args:
            compress: Whether to compress large response data
            
        Returns:
            Response as dictionary
        """
        response = {
            "data": self.data,
            "meta": self.meta,
            "message": self.message,
            "status": self.status_code
        }
        
        if self.errors:
            response["errors"] = self.errors
            
        # Apply compression for large responses if requested
        if compress and self.data is not None and isinstance(self.data, (dict, list)):
            data_str = json_dumps(self.data)
            if len(data_str) > 1024:  # Only compress if larger than 1KB
                compressed_data = compress_json(self.data)
                response["meta"]["compressed"] = True
                response["data"] = compressed_data.hex()
                
        return response
        
    def to_json(self, compress: bool = False) -> str:
        """
        Convert response to JSON string
        
        Args:
            compress: Whether to compress large response data
            
        Returns:
            JSON string
        """
        return json_dumps(self.to_dict(compress=compress))
        
    @classmethod
    def success(cls, data: Any = None, message: str = "Operation successful", 
               status_code: int = HTTPStatus.OK) -> 'ApiResponse':
        """
        Create a success response
        
        Args:
            data: Response payload
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Success response
        """
        return cls(data=data, message=message, status_code=status_code)
        
    @classmethod
    def error(cls, message: str = "Operation failed", 
             status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
             errors: List[Dict] = None) -> 'ApiResponse':
        """
        Create an error response
        
        Args:
            message: Error message
            status_code: HTTP status code
            errors: Detailed error information
            
        Returns:
            Error response
        """
        return cls(message=message, status_code=status_code, errors=errors)
        
    @classmethod
    def bad_request(cls, message: str = "Invalid request", 
                   errors: List[Dict] = None) -> 'ApiResponse':
        """
        Create a bad request response
        
        Args:
            message: Error message
            errors: Validation errors
            
        Returns:
            Bad request response
        """
        return cls(message=message, status_code=HTTPStatus.BAD_REQUEST, errors=errors)
        
    @classmethod
    def not_found(cls, message: str = "Resource not found") -> 'ApiResponse':
        """
        Create a not found response
        
        Args:
            message: Error message
            
        Returns:
            Not found response
        """
        return cls(message=message, status_code=HTTPStatus.NOT_FOUND)
        
    @classmethod
    def unauthorized(cls, message: str = "Unauthorized access") -> 'ApiResponse':
        """
        Create an unauthorized response
        
        Args:
            message: Error message
            
        Returns:
            Unauthorized response
        """
        return cls(message=message, status_code=HTTPStatus.UNAUTHORIZED)


@memoize_json(ttl=60)  # Cache responses for 60 seconds
def generate_paginated_response(data: List[Any], page: int = 1, 
                               page_size: int = 20, total: int = None) -> Dict[str, Any]:
    """
    Generate a paginated response for list data
    
    Args:
        data: List of items
        page: Current page number
        page_size: Number of items per page
        total: Total number of items (calculated from data if None)
        
    Returns:
        Paginated response structure
    """
    if total is None:
        total = len(data)
        
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return {
        "items": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def handle_api_error(func: Callable) -> Callable:
    """
    Decorator to standardize API error handling
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs) -> ApiResponse:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return ApiResponse.bad_request(message=str(e))
        except KeyError as e:
            logger.warning(f"Missing key in {func.__name__}: {str(e)}")
            return ApiResponse.bad_request(message=f"Missing required field: {str(e)}")
        except FileNotFoundError as e:
            logger.warning(f"Resource not found in {func.__name__}: {str(e)}")
            return ApiResponse.not_found(message=str(e))
        except PermissionError as e:
            logger.warning(f"Permission denied in {func.__name__}: {str(e)}")
            return ApiResponse.unauthorized(message=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            return ApiResponse.error(message="An unexpected error occurred")
    
    return wrapper


def create_error_detail(field: str, code: str, message: str) -> Dict[str, str]:
    """
    Create a standardized error detail object
    
    Args:
        field: Field that caused the error
        code: Error code
        message: Error message
        
    Returns:
        Error detail dictionary
    """
    return {
        "field": field,
        "code": code,
        "message": message
    }


def validation_error_response(validation_errors: Dict[str, List[str]]) -> ApiResponse:
    """
    Create a response for validation errors
    
    Args:
        validation_errors: Dictionary mapping field names to error messages
        
    Returns:
        Bad request response with validation errors
    """
    errors = []
    for field, messages in validation_errors.items():
        for message in messages:
            errors.append(create_error_detail(
                field=field,
                code="validation_error",
                message=message
            ))
            
    return ApiResponse.bad_request(
        message="Validation failed",
        errors=errors
    )


def throttled_response(retry_after: int) -> ApiResponse:
    """
    Create a response for rate-limited requests
    
    Args:
        retry_after: Seconds until retry is allowed
        
    Returns:
        Rate limit response
    """
    return ApiResponse(
        message="Rate limit exceeded",
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
        errors=[{
            "code": "rate_limit_exceeded",
            "message": f"Too many requests, retry after {retry_after} seconds",
            "retry_after": retry_after
        }]
    )


def health_check_response() -> Dict[str, Any]:
    """
    Generate a health check response
    
    Returns:
        Health status information
    """
    return {
        "status": "ok",
        "timestamp": time.time(),
        "uptime": time.time() - _start_time,  # Global from module initialization
        "version": "1.0"
    }


# Initialize module
_start_time = time.time() 