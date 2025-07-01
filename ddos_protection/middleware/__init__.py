#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Middleware
--------------------------------
Simplified middleware for Cloudflare-only mode.
"""

import logging
from typing import Tuple, Any

# Configure logging
logger = logging.getLogger('ddos_protection.middleware')

def should_block_request(request: Any) -> Tuple[bool, str]:
    """
    Simplified version of should_block_request for Cloudflare-only mode
    
    Args:
        request: Flask request object
        
    Returns:
        tuple: (should_block, reason)
    """
    # Skip OPTIONS requests completely
    if request.method == "OPTIONS":
        return False, "OPTIONS request allowed"
    
    # Allow all GET requests to avoid blocking normal web traffic
    if request.method == "GET":
        return False, "GET request allowed"
        
    # Allow quicktransfer API endpoints
    if request.path and request.path.startswith('/api/quicktransfer'):
        return False, "QuickTransfer API request allowed"
        
    # Check if IP is banned in Cloudflare
    try:
        from ddos_protection.network.cloudflare.api import blocked_ips_cache
        
        # Get real IP
        real_ip = getattr(request, 'real_ip', request.remote_addr)
        
        if real_ip in blocked_ips_cache:
            return True, f"IP {real_ip} is banned in Cloudflare"
    except ImportError:
        pass
    
    # Allow the request by default
    return False, "Request allowed" 