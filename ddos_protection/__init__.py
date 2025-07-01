#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System
---------------------
نظام حماية متكامل ضد هجمات رفض الخدمة
"""

import os
import logging
import time
import yaml
import asyncio
from typing import Dict, Set, List, Optional, Any

# Configure logging
logger = logging.getLogger('ddos_protection')

# Global caches for ultra-fast lookups - used throughout the system
# Use Python sets for O(1) lookup performance
banned_ips_cache = set()
banned_devices_cache = set()
trusted_ips_cache = set()

# Expose these explicitly for importing in other modules
__all__ = [
    'banned_ips_cache', 
    'banned_devices_cache', 
    'trusted_ips_cache',
    'load_config',
    'DDoSProtectionSystem',
    'Config'
]

def load_config(config_path):
    """Load DDoS protection config from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Convert to object for easier access
        class Config:
            def __init__(self, config_dict):
                for key, value in config_dict.items():
                    if isinstance(value, dict):
                        setattr(self, key, Config(value))
                    else:
                        setattr(self, key, value)
                        
            def __str__(self):
                return str(vars(self))
        
        return Config(config)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        # Return default config
        class DefaultConfig:
            def __init__(self):
                self.enabled = True
                self.rate_limit = 60
                self.ban_threshold = 100
                self.ban_duration = 3600
                self.log_requests = True
                self.bypass_on_error = False
        
        return DefaultConfig()

# Alias for Config class
Config = type('Config', (), {})

class DDoSProtectionSystem:
    """
    Main DDoS protection system integrating all components.
    Provides a centralized interface to the protection features.
    This version uses Cloudflare exclusively.
    """
    
    def __init__(self, config=None):
        """Initialize DDoS protection system with config"""
        self.config = config
        
        # Check if we're in development mode
        self.dev_mode = os.environ.get('CF_DEV_MODE', 'false').lower() == 'true'
        
        # Reference to components - simplified for Cloudflare only
        self.mitigator = None
        self.analyzer = None
        self.monitor = None
        
        # Set as empty sets for compatibility
        global banned_ips_cache, trusted_ips_cache, banned_devices_cache
        banned_ips_cache = set()
        trusted_ips_cache = set()
        banned_devices_cache = set()
        
        if self.dev_mode:
            logger.info("DDoS Protection System initialized in DEVELOPMENT MODE")
        else:
            logger.info("DDoS Protection System initialized")
    
    async def start(self):
        """Start the DDoS protection system in Cloudflare-only mode"""
        # Initialize stats
        self.stats = {
            'started_at': time.time(),
            'requests_processed': 0,
            'attacks_mitigated': 0,
            'ips_banned': 0,
            'devices_banned': 0
        }
        
        logger.info("DDoS Protection System started in Cloudflare-only mode")
        return True
    
    async def process_request(self, ip: str, path: str, user_agent: Optional[str] = None, 
                          device_fingerprint: Optional[str] = None, 
                          request_size: int = 0, method: Optional[str] = None):
        """
        Process an incoming request (Cloudflare-only mode).
        
        Args:
            ip: Client IP address
            path: Request path
            user_agent: Optional user agent string
            device_fingerprint: Optional device fingerprint
            request_size: Size of the request in bytes
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            tuple: (allowed, challenge_data)
        """
        # All requests allowed since Cloudflare handles the protection
        self.stats['requests_processed'] += 1
        return True, None
    
    def get_stats(self) -> Dict:
        """Get current stats of the DDoS protection system"""
        stats = self.stats.copy()
        stats['uptime'] = time.time() - stats['started_at']
        stats['cloudflare_only_mode'] = True
        return stats

__all__ = [
    "Config", 
    "load_config",
    "AttackDetector",
    "AttackMitigator",
    "create_api_server",
    "integrate_with_flask",
    "integrate_with_fastapi",
    "DDoSProtectionSystem",
    "get_real_ip_from_request",
    "is_valid_ip",
    "is_private_ip",
    "storage_manager",
    "JsonStorage",
    "is_ip_banned",
    "is_device_banned",
    "is_ip_trusted",
    "add_to_banned_cache",
    "add_to_device_banned_cache",
    "load_banned_ips",
    "load_trusted_ips",
    "load_banned_devices"
] 