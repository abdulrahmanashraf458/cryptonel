#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Utility Functions
----------------------------------------
Helper functions for various components of the DDoS protection system:
- IP validation and analysis
- Geolocation
- Challenge generation and verification
- Server resource monitoring
- Command execution
- Path and pattern analysis
"""

import asyncio
import os
import re
import math
import time
import random
import logging
import socket
import hashlib
import ipaddress
import subprocess
import statistics
from typing import Dict, List, Tuple, Set, Any, Optional, Union
from collections import Counter
import json
import urllib.parse
import base64
from pathlib import Path
import platform

# Configure logger
logger = logging.getLogger("ddos_protection.utils")

# Try to import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, resource monitoring will be limited")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not available, using fallback methods for calculations")

try:
    import maxminddb
    MAXMIND_AVAILABLE = True
except ImportError:
    MAXMIND_AVAILABLE = False
    logger.warning("maxminddb not available, geolocation features will be disabled")


def is_valid_ip(ip: str) -> bool:
    """
    Check if a string is a valid IPv4 or IPv6 address.
    
    Args:
        ip: IP address to check
        
    Returns:
        bool: True if valid IP address
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_ip_in_network(ip: str, network: str) -> bool:
    """
    Check if an IP address is in a specific network range.
    
    Args:
        ip: IP address to check
        network: Network in CIDR notation (e.g., "10.0.0.0/8")
        
    Returns:
        bool: True if IP is in the network, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        network_obj = ipaddress.ip_network(network, strict=False)
        return ip_obj in network_obj
    except ValueError:
        return False


def is_ip_in_any_network(ip: str, networks: List[str]) -> bool:
    """
    Check if an IP address is in any of the specified networks.
    
    Args:
        ip: IP address to check
        networks: List of networks in CIDR notation
        
    Returns:
        bool: True if IP is in any network, False otherwise
    """
    return any(is_ip_in_network(ip, network) for network in networks)


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is private/internal.
    
    Args:
        ip: IP address to check
        
    Returns:
        bool: True if private IP address
    """
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def is_known_good_bot(user_agent: str) -> bool:
    """
    Check if a user agent belongs to a known good bot.
    
    Args:
        user_agent: User agent string to check
        
    Returns:
        bool: True if user agent is a known good bot, False otherwise
    """
    # List of patterns for known good bots
    good_bot_patterns = [
        r"Googlebot", 
        r"Bingbot",
        r"Slurp",  # Yahoo
        r"DuckDuckBot",
        r"Baiduspider",
        r"YandexBot",
        r"facebookexternalhit",
        r"Twitterbot",
        r"Applebot",
        r"GoogleProber",
        r"PingdomTMS",
        r"UptimeRobot",
        r"StatusCake"
    ]
    
    # Check if user agent matches any known good bot pattern
    if user_agent:
        return any(re.search(pattern, user_agent, re.IGNORECASE) for pattern in good_bot_patterns)
    
    return False


def calculate_entropy(values: List[int]) -> float:
    """
    Calculate Shannon entropy for a list of values.
    Lower entropy indicates more predictable patterns.
    
    Args:
        values: List of frequency values
        
    Returns:
        float: Entropy value
    """
    if not values or sum(values) == 0:
        return 0.0
        
    # Calculate probabilities
    total = sum(values)
    probabilities = [count / total for count in values if count > 0]
    
    # Calculate entropy using Shannon formula
    if NUMPY_AVAILABLE:
        return -np.sum(probabilities * np.log2(probabilities))
    else:
        return -sum(p * math.log2(p) for p in probabilities)


def analyze_path_distribution(paths: List[str]) -> Dict[str, float]:
    """
    Analyze distribution of request paths to detect abnormal patterns.
    
    Args:
        paths: List of request paths
        
    Returns:
        Dict[str, float]: Analysis results including entropy and other metrics
    """
    if not paths:
        return {
            "entropy": 0.0,
            "unique_ratio": 0.0,
            "most_common_ratio": 0.0,
            "static_ratio": 0.0
        }
    
    # Count occurrences of each path
    path_counter = Counter(paths)
    
    # Calculate metrics
    unique_count = len(path_counter)
    unique_ratio = unique_count / len(paths)
    
    # Most common path ratio
    most_common = path_counter.most_common(1)
    most_common_ratio = most_common[0][1] / len(paths) if most_common else 0
    
    # Static vs. dynamic path ratio
    static_extensions = ['.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.woff', '.woff2']
    static_paths = sum(path_counter[p] for p in path_counter if any(p.endswith(ext) for ext in static_extensions))
    static_ratio = static_paths / len(paths)
    
    # Entropy of path distribution
    entropy = calculate_entropy(list(path_counter.values()))
    
    return {
        "entropy": entropy,
        "unique_ratio": unique_ratio,
        "most_common_ratio": most_common_ratio,
        "static_ratio": static_ratio
    }


def extract_request_features(
    path: str, 
    method: str, 
    headers: Dict[str, str], 
    query: Dict[str, str],
    body_size: int
) -> Dict[str, Any]:
    """
    Extract features from a request for analysis.
    
    Args:
        path: Request path
        method: HTTP method
        headers: HTTP headers
        query: Query parameters
        body_size: Size of request body in bytes
        
    Returns:
        Dict[str, Any]: Extracted request features
    """
    features = {
        "path_length": len(path),
        "path_depth": path.count('/'),
        "method": method,
        "has_query": bool(query),
        "query_param_count": len(query),
        "body_size": body_size,
        "has_user_agent": "user-agent" in headers or "User-Agent" in headers,
        "has_referer": "referer" in headers or "Referer" in headers,
        "has_cookies": "cookie" in headers or "Cookie" in headers,
        "header_count": len(headers),
        "is_ajax": headers.get("X-Requested-With") == "XMLHttpRequest",
        "is_json": headers.get("Content-Type", "").startswith("application/json"),
        "is_form": headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"),
        "is_multipart": headers.get("Content-Type", "").startswith("multipart/form-data"),
    }
    
    # Extract user agent features if present
    ua = headers.get("user-agent") or headers.get("User-Agent", "")
    if ua:
        features.update({
            "ua_length": len(ua),
            "ua_is_mobile": "mobile" in ua.lower() or "android" in ua.lower(),
            "ua_is_bot": is_known_good_bot(ua) or "bot" in ua.lower() or "spider" in ua.lower(),
            "ua_has_platform": any(platform in ua.lower() for platform in ["windows", "mac", "linux", "android", "ios"]),
        })
    else:
        features.update({
            "ua_length": 0,
            "ua_is_mobile": False,
            "ua_is_bot": False,
            "ua_has_platform": False,
        })
    
    return features


def load_geolocation_db(db_path: str) -> Optional[Any]:
    """
    Load MaxMind GeoLite2 database for IP geolocation.
    
    Args:
        db_path: Path to MaxMind GeoLite2 database file
        
    Returns:
        Optional[Any]: Database reader object or None if not available
    """
    if not MAXMIND_AVAILABLE:
        logger.warning("Geolocation database loading failed: maxminddb not installed")
        return None
    
    try:
        if os.path.exists(db_path):
            return maxminddb.open_database(db_path)
        else:
            logger.warning(f"Geolocation database not found at {db_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading geolocation database: {e}")
        return None


def get_ip_info_from_api(ip: str, token: str = None) -> Optional[Dict[str, Any]]:
    """
    Get IP information from IPinfo API.
    
    Args:
        ip: IP address to look up
        token: IPinfo API token (optional)
        
    Returns:
        Dict with IP information or None if lookup failed
    """
    if not is_valid_ip(ip):
        logger.warning(f"Invalid IP for IPinfo lookup: {ip}")
        return None
        
    # Skip private IPs
    if is_private_ip(ip):
        return {"country_code": "PRIVATE", "country": "Private IP"}
        
    try:
        import requests
        
        # Construct the API URL
        api_url = f"https://api.ipinfo.io/lite/{ip}"
        
        # Add token if provided
        headers = {}
        params = {}
        if token:
            params["token"] = token
        
        # Send request with timeout
        response = requests.get(api_url, headers=headers, params=params, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"IPinfo lookup successful for {ip}")
            return data
        else:
            logger.warning(f"IPinfo API returned status {response.status_code} for {ip}")
            return None
            
    except Exception as e:
        logger.error(f"Error in IPinfo API lookup for {ip}: {e}")
        return None


def get_ip_geolocation(ip: str, geo_db: Any = None, api_token: str = None) -> Optional[Dict[str, Any]]:
    """
    Get geolocation information for an IP address.
    
    Args:
        ip: IP address to look up
        geo_db: MaxMind GeoLite2 database reader
        api_token: IPinfo API token (optional)
        
    Returns:
        Dict with geolocation information or None if lookup failed
    """
    # First try local database if available
    if geo_db:
        try:
            if not is_valid_ip(ip):
                logger.warning(f"Invalid IP for geolocation: {ip}")
                return None
                
            # Skip private IPs
            if is_private_ip(ip):
                return {"country_code": "PRIVATE", "country": "Private IP"}
                
            # Get geolocation from database
            data = geo_db.get(ip)
            if data and "country" in data:
                logger.debug(f"Geolocation found for {ip}: {data['country']['iso_code']}")
                return {
                    "country_code": data["country"]["iso_code"],
                    "country": data["country"]["names"]["en"],
                    "continent_code": data.get("continent", {}).get("code"),
                    "continent": data.get("continent", {}).get("names", {}).get("en")
                }
                
        except Exception as e:
            logger.error(f"Error in local geolocation lookup for {ip}: {e}")
    
    # If local database lookup failed or not available, try API
    if api_token:
        api_data = get_ip_info_from_api(ip, api_token)
        if api_data:
            return {
                "country_code": api_data.get("country_code"),
                "country": api_data.get("country"),
                "continent_code": api_data.get("continent_code"),
                "continent": api_data.get("continent"),
                "asn": api_data.get("asn"),
                "as_name": api_data.get("as_name"),
                "as_domain": api_data.get("as_domain")
            }
    
    # If all lookups failed
    logger.warning(f"Geolocation lookup failed for {ip}")
    return None


async def get_server_resources() -> Tuple[float, float, float]:
    """
    Get current server resource usage (CPU, memory, network).
    
    Returns:
        Tuple[float, float, float]: CPU usage (%), memory usage (%), network usage (%)
    """
    if PSUTIL_AVAILABLE:
        try:
            # Run intensive operations in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Get CPU usage (percent)
            cpu_usage = await loop.run_in_executor(None, psutil.cpu_percent, 1)
            
            # Get memory usage (percent)
            memory = await loop.run_in_executor(None, psutil.virtual_memory)
            memory_usage = memory.percent
            
            # Get network usage (percent of capacity, estimated)
            # This is an approximation as we don't know the maximum bandwidth
            net_before = await loop.run_in_executor(None, psutil.net_io_counters)
            await asyncio.sleep(0.5)
            net_after = await loop.run_in_executor(None, psutil.net_io_counters)
            
            # Calculate bytes per second
            bytes_sent = net_after.bytes_sent - net_before.bytes_sent
            bytes_recv = net_after.bytes_recv - net_before.bytes_recv
            bytes_total = (bytes_sent + bytes_recv) * 2  # Multiply by 2 to convert to bits
            
            # Estimate network usage as percentage of a typical 1Gbps link
            # Adjust this based on your actual network capacity
            network_capacity_bits = 1000 * 1000 * 1000  # 1 Gbps in bits
            network_usage = min(100, (bytes_total / 0.5) / (network_capacity_bits / 100))
            
            return cpu_usage, memory_usage, network_usage
            
        except Exception as e:
            logger.error(f"Error getting server resources: {e}")
    
    # Fallback to basic system calls if psutil is not available
    try:
        # Try to get CPU usage with basic commands
        if platform.system() == "Linux":
            # Use top command to get CPU usage
            proc = await asyncio.create_subprocess_shell(
                "top -b -n 1 | grep '%Cpu' | awk '{print $2}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            cpu_usage = float(stdout.decode().strip()) if stdout else 50.0
            
            # Use free command to get memory usage
            proc = await asyncio.create_subprocess_shell(
                "free | grep Mem | awk '{print $3/$2 * 100.0}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            memory_usage = float(stdout.decode().strip()) if stdout else 50.0
            
            # Use ifstat to get network usage (if available)
            proc = await asyncio.create_subprocess_shell(
                "ifstat 1 1 | tail -n 1 | awk '{print $1+$2}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            network_kbps = float(stdout.decode().strip()) if stdout and stdout.decode().strip() else 5000
            network_usage = min(100, network_kbps / 100000 * 100)  # Assuming 1Gbps max
            
            return cpu_usage, memory_usage, network_usage
            
        elif platform.system() == "Windows":
            # For Windows, we provide conservative estimates without psutil
            return 50.0, 50.0, 30.0
        else:
            # For other platforms, provide conservative estimates
            return 50.0, 50.0, 30.0
            
    except Exception as e:
        logger.error(f"Error getting server resources with fallback method: {e}")
        # Return conservative estimates
        return 50.0, 50.0, 30.0


def execute_command(command: List[str], raise_on_error: bool = True) -> subprocess.CompletedProcess:
    """
    Execute a shell command and return the result.
    
    Args:
        command: Command to execute as list of strings
        raise_on_error: Whether to raise an exception on non-zero exit code
        
    Returns:
        subprocess.CompletedProcess: Command execution result
    """
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=raise_on_error
        )
    except subprocess.CalledProcessError as e:
        if raise_on_error:
            logger.error(f"Command failed: {' '.join(command)}, error: {e.stderr}")
            raise
        return e


def generate_challenge(difficulty: int = 1) -> Tuple[str, str]:
    """
    Generate a JavaScript challenge for client verification.
    
    Args:
        difficulty: Challenge difficulty level (1-5)
        
    Returns:
        Tuple[str, str]: JavaScript challenge code and expected answer
    """
    # Scale iterations based on difficulty (1-5)
    iterations = int(10000 * difficulty)
    
    # Generate random values for the challenge
    a = random.randint(10000, 99999)
    b = random.randint(10000, 99999)
    c = random.randint(10000, 99999)
    
    # Generate a unique salt for this challenge
    salt = os.urandom(8).hex()
    
    # Create expected answer
    answer_base = f"{a}{b}{c}{salt}"
    expected_answer = hashlib.sha256(answer_base.encode()).hexdigest()
    
    # Create JavaScript challenge that will compute the same hash
    # More difficult challenges use more iterations and operations
    js_challenge = f"""
    function solveChallenge() {{
        // Challenge parameters
        const a = {a};
        const b = {b};
        const c = {c};
        const salt = "{salt}";
        const iterations = {iterations};
        
        // Compute result with artificial delay
        let result = a;
        for (let i = 0; i < iterations; i++) {{
            if (i % 2 === 0) {{
                result = (result + b) % 1000000;
            }} else {{
                result = (result * c) % 1000000;
            }}
        }}
        
        // Create final value to hash
        const valueToHash = `${{a}}${{b}}${{c}}${{salt}}`;
        
        // Hash the result using SHA-256
        return crypto.subtle.digest('SHA-256', new TextEncoder().encode(valueToHash))
            .then(buffer => {{
                const hashArray = Array.from(new Uint8Array(buffer));
                const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                return hashHex;
            }});
    }}
    
    // Execute the challenge and send result to server
    solveChallenge().then(result => {{
        // Send result to server using provided callback function
        submitChallengeResponse(result);
    }});
    """
    
    return js_challenge, expected_answer


def verify_challenge_response(response: str, expected: str) -> bool:
    """
    Verify a client's challenge response.
    
    Args:
        response: Client's answer to the challenge
        expected: Expected answer
        
    Returns:
        bool: True if the response is correct, False otherwise
    """
    # Simple string comparison (constant time comparison would be better in production)
    return response is not None and response == expected


def get_client_ip_from_request(request: Any) -> str:
    """
    Extract the real client IP from any request object.
    Works with Flask, FastAPI, Django, etc.
    
    Args:
        request: Any request object
        
    Returns:
        str: The real client IP address
    """
    # Check for custom attribute first (might have been set by middleware)
    if hasattr(request, 'real_ip'):
        return request.real_ip
    
    # If using Flask or similar
    if hasattr(request, 'remote_addr'):
        remote_addr = request.remote_addr
    # If using aiohttp
    elif hasattr(request, 'remote'):
        remote_addr = request.remote
    # If using Django
    elif hasattr(request, 'META') and 'REMOTE_ADDR' in request.META:
        remote_addr = request.META['REMOTE_ADDR']
    else:
        # Default to empty
        remote_addr = ''
    
    # Check for forwarded IPs
    forwarded_for = None
    
    # Extract from different headers based on server setup
    if hasattr(request, 'headers'):
        # Flask/FastAPI style
        headers = request.headers
        
        if isinstance(headers, dict):
            # Dictionary-like headers
            forwarded_for = headers.get('X-Forwarded-For') or headers.get('X-Real-IP')
        else:
            # Object-like headers with get method
            if hasattr(headers, 'get'):
                forwarded_for = headers.get('X-Forwarded-For') or headers.get('X-Real-IP')
            # Direct attribute access
            elif hasattr(headers, 'x_forwarded_for'):
                forwarded_for = headers.x_forwarded_for
            elif hasattr(headers, 'x_real_ip'):
                forwarded_for = headers.x_real_ip
    
    # Django style
    elif hasattr(request, 'META'):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('HTTP_X_REAL_IP')
    
    # Process the forwarded-for header if present
    if forwarded_for:
        # Take the first IP in the chain (client IP)
        try:
            # If it's a string with multiple IPs, split and take the first
            if isinstance(forwarded_for, str) and ',' in forwarded_for:
                forwarded_ips = [ip.strip() for ip in forwarded_for.split(',')]
                client_ip = forwarded_ips[0]
            else:
                client_ip = forwarded_for
            
            # Validate it's a real IP
            if is_valid_ip(client_ip):
                return client_ip
        except Exception as e:
            logger.warning(f"Error parsing X-Forwarded-For header: {e}")
    
    # Fallback to remote_addr
    return remote_addr


# Add alias for the function to maintain compatibility
def get_real_ip_from_request(request: Any, trusted_proxies: List[str] = None) -> str:
    """
    Alias for get_client_ip_from_request, maintains compatibility.
    
    Args:
        request: HTTP request object
        trusted_proxies: List of trusted proxy IP addresses
        
    Returns:
        str: Client IP address
    """
    return get_client_ip_from_request(request) 