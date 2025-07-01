#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Monitoring Module
------------------------------------------
نظام مراقبة وحظر متقدم للحماية من هجمات DDoS
"""

import logging
import threading
import time
import asyncio
from typing import Dict, Set, List, Optional, Tuple

# Import utility for IP validation
from ddos_protection.utils import is_valid_ip

# Setup logger
logger = logging.getLogger('ddos_protection.monitoring')

class MonitorSystem:
    """
    Advanced monitoring system for tracking and immediately blocking
    malicious IPs and devices at both application and network levels.
    """
    
    def __init__(self, storage_manager=None, ban_manager=None, device_manager=None):
        """
        Initialize the monitoring system with required components.
        
        Args:
            storage_manager: Storage manager for persistent data
            ban_manager: Ban manager for handling IP bans
            device_manager: Device manager for handling device bans
        """
        # Import required components if not provided
        if storage_manager is None:
            from ddos_protection.storage import storage_manager
        self.storage_manager = storage_manager
        
        if ban_manager is None:
            from ddos_protection.storage import ban_manager
        self.ban_manager = ban_manager
        
        if device_manager is None:
            from ddos_protection.storage import device_manager
        self.device_manager = device_manager
        
        # Import global caches for immediate blocking
        try:
            from ddos_protection import banned_ips_cache, banned_devices_cache
            self.banned_ips_cache = banned_ips_cache
            self.banned_devices_cache = banned_devices_cache
        except ImportError:
            # Fallback to local caches if global ones aren't available
            self.banned_ips_cache = set()
            self.banned_devices_cache = set()
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Track last time IP rate limits were checked
        self.last_ip_check = {}
        
        # Track IP request patterns
        self.ip_patterns = {}
        
        # Counters for statistics and reporting
        self.stats = {
            'blocked_requests': 0,
            'blocked_ips': 0,
            'blocked_devices': 0,
            'suspicious_requests': 0
        }
        
        # Load existing banned IPs and devices into memory
        self._load_banned_entities()
        
        logger.info("Monitor system initialized")
    
    def _load_banned_entities(self):
        """Load all banned IPs and devices into memory caches for instant blocking"""
        # Load banned IPs
        try:
            banned_ips = self.ban_manager.get_banned_ips()
            for ip in banned_ips:
                if hasattr(self.banned_ips_cache, 'add'):  # If it's a set
                    self.banned_ips_cache.add(ip)
                else:  # If it's a dict
                    self.banned_ips_cache[ip] = True
            logger.info(f"Loaded {len(banned_ips)} banned IPs into memory cache")
        except Exception as e:
            logger.error(f"Failed to load banned IPs: {e}")
        
        # Load banned devices
        try:
            banned_devices = self.device_manager.get_banned_devices()
            for device in banned_devices:
                if hasattr(self.banned_devices_cache, 'add'):  # If it's a set
                    self.banned_devices_cache.add(device)
                else:  # If it's a dict
                    self.banned_devices_cache[device] = True
            logger.info(f"Loaded {len(banned_devices)} banned devices into memory cache")
        except Exception as e:
            logger.error(f"Failed to load banned devices: {e}")
    
    def is_blocked(self, ip: str, device_fingerprint: Optional[str] = None, method: Optional[str] = None) -> bool:
        """
        Check if an IP or device is blocked using ultra-fast memory cache lookup.
        
        Args:
            ip: Client IP address
            device_fingerprint: Optional device fingerprint
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            bool: True if the IP or device should be blocked
        """
        # Always check IP first (fastest check)
        if not is_valid_ip(ip):
            logger.warning(f"Invalid IP format detected: {ip}")
            return True  # Block invalid IPs
        
        # Check banned IPs cache
        if hasattr(self.banned_ips_cache, '__contains__'):  # If it's a set
            if ip in self.banned_ips_cache:
                self.stats['blocked_requests'] += 1
                return True
        else:  # If it's a dict
            if ip in self.banned_ips_cache:
                self.stats['blocked_requests'] += 1
                return True
        
        # Check DB if not in cache
        if self.ban_manager.is_banned(ip):
            # Add to cache for future checks
            if hasattr(self.banned_ips_cache, 'add'):  # If it's a set
                self.banned_ips_cache.add(ip)
            else:  # If it's a dict
                self.banned_ips_cache[ip] = True
            self.stats['blocked_requests'] += 1
            return True
        
        # If we have a device fingerprint, check that too
        if device_fingerprint:
            # Check device cache first
            if hasattr(self.banned_devices_cache, '__contains__'):  # If it's a set
                if device_fingerprint in self.banned_devices_cache:
                    # Ban this IP too if it's associated with a banned device
                    self._ban_associated_ip(ip, device_fingerprint)
                    self.stats['blocked_requests'] += 1
                    return True
            else:  # If it's a dict
                if device_fingerprint in self.banned_devices_cache:
                    # Ban this IP too if it's associated with a banned device
                    self._ban_associated_ip(ip, device_fingerprint)
                    self.stats['blocked_requests'] += 1
                    return True
            
            # Check DB if not in cache
            if self.device_manager.is_banned(device_fingerprint):
                # Add to cache for future checks
                if hasattr(self.banned_devices_cache, 'add'):  # If it's a set
                    self.banned_devices_cache.add(device_fingerprint)
                else:  # If it's a dict
                    self.banned_devices_cache[device_fingerprint] = True
                
                # Ban this IP too if it's associated with a banned device
                self._ban_associated_ip(ip, device_fingerprint)
                self.stats['blocked_requests'] += 1
                return True
            
            # Check if this IP was used by any banned device
            banned_devices = self.device_manager.check_device_from_ip(ip)
            if banned_devices:
                # Ban this device too
                self._ban_device_with_ip(device_fingerprint, ip, f"Using IP associated with banned devices: {','.join(banned_devices[:3])}")
                self.stats['blocked_requests'] += 1
                return True
        
        return False
    
    def _ban_associated_ip(self, ip: str, device_fingerprint: str):
        """Ban an IP associated with a banned device"""
        try:
            # Ban the IP
            self.ban_manager.ban_ip(ip, f"Associated with banned device {device_fingerprint}", 86400)
            
            # Apply firewall block
            self._apply_firewall_block(ip)
            
            # Update stats
            self.stats['blocked_ips'] += 1
            
            logger.warning(f"Banned IP {ip} associated with banned device {device_fingerprint}")
        except Exception as e:
            logger.error(f"Failed to ban associated IP {ip}: {e}")
    
    def _ban_device_with_ip(self, device_fingerprint: str, ip: str, reason: str):
        """Ban a device and its associated IP"""
        try:
            # Ban the device
            self.device_manager.ban_device(
                device_fingerprint,
                ip,
                reason,
                None,  # No browser fingerprint
                None   # No user agent
            )
            
            # Ban the IP
            self.ban_manager.ban_ip(ip, f"Associated with banned device {device_fingerprint}", 86400)
            
            # Apply firewall block
            self._apply_firewall_block(ip)
            
            # Update stats
            self.stats['blocked_devices'] += 1
            self.stats['blocked_ips'] += 1
            
            logger.warning(f"Banned device {device_fingerprint} and IP {ip}: {reason}")
        except Exception as e:
            logger.error(f"Failed to ban device {device_fingerprint} with IP {ip}: {e}")
    
    async def _apply_firewall_block(self, ip: str):
        """Apply a firewall block to an IP address"""
        try:
            from ddos_protection.core.mitigator import DDoSMitigator
            mitigator = DDoSMitigator()
            await mitigator._apply_system_firewall_block(ip)
            logger.info(f"Applied firewall block to IP {ip}")
        except Exception as e:
            logger.error(f"Failed to apply firewall block to IP {ip}: {e}")
    
    def process_request_sync(self, ip: str, path: str, device_fingerprint: Optional[str] = None, 
                           user_agent: Optional[str] = None, request_size: int = 0, method: Optional[str] = None) -> bool:
        """
        Process a request synchronously and determine if it should be blocked.
        
        Args:
            ip: Client IP address
            path: Request path
            device_fingerprint: Optional device fingerprint
            user_agent: Optional user agent string
            request_size: Size of the request in bytes
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            bool: True if the request is allowed, False if it should be blocked
        """
        # First check if already blocked
        if self.is_blocked(ip, device_fingerprint, method):
            return False
        
        # Update request pattern data
        self._update_request_pattern(ip, path, request_size, method)
        
        # Check for rate limiting - more aggressive for POST
        if self._check_rate_limits(ip, device_fingerprint, method):
            return False
        
        # Track relationship between device and IP
        if device_fingerprint:
            self.device_manager.update_device_record(
                device_fingerprint,
                ip,
                None,  # No browser fingerprint
                user_agent
            )
        
        return True
    
    def _update_request_pattern(self, ip: str, path: str, request_size: int, method: Optional[str] = None):
        """Update tracking data for IP request patterns"""
        with self.lock:
            current_time = time.time()
            
            if ip not in self.ip_patterns:
                self.ip_patterns[ip] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'request_count': 1,
                    'paths': {path: 1},
                    'methods': {method: 1} if method else {},
                    'total_size': request_size,
                    'intervals': []
                }
            else:
                pattern = self.ip_patterns[ip]
                
                # Calculate time since last request
                if 'last_seen' in pattern:
                    interval = current_time - pattern['last_seen']
                    pattern['intervals'].append(interval)
                    # Keep only last 10 intervals
                    if len(pattern['intervals']) > 10:
                        pattern['intervals'] = pattern['intervals'][-10:]
                
                # Update counters
                pattern['last_seen'] = current_time
                pattern['request_count'] = pattern.get('request_count', 0) + 1
                
                # Track HTTP methods
                if method:
                    if 'methods' not in pattern:
                        pattern['methods'] = {}
                    pattern['methods'][method] = pattern['methods'].get(method, 0) + 1
                
                # Update path stats
                if 'paths' not in pattern:
                    pattern['paths'] = {}
                pattern['paths'][path] = pattern['paths'].get(path, 0) + 1
    
    def _check_rate_limits(self, ip: str, device_fingerprint: Optional[str] = None, method: Optional[str] = None) -> bool:
        """
        Check if rate limits are exceeded.
        
        Args:
            ip: Client IP address
            device_fingerprint: Optional device fingerprint
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            bool: True if request should be blocked, False if allowed
        """
        with self.lock:
            current_time = time.time()
            
            # Check if IP pattern data exists
            if ip not in self.ip_patterns:
                return False
            
            pattern = self.ip_patterns[ip]
            duration = current_time - pattern['first_seen']
            
            # Calculate request rate (requests per second)
            if duration > 0:
                request_rate = pattern['request_count'] / duration
            else:
                request_rate = pattern['request_count']  # Avoid division by zero
            
            # Check if method is POST and apply stricter limits
            if method == 'POST' and 'methods' in pattern and 'POST' in pattern['methods']:
                post_count = pattern['methods']['POST']
                
                # More than 5 POST requests in under 5 seconds is suspicious
                if post_count >= 5 and duration < 5:
                    logger.warning(f"Rate limit exceeded for POST requests: {ip} - {post_count} POST requests in {duration:.2f}s")
                    self._ban_for_rate_limit(ip, f"Excessive POST requests: {post_count} in {duration:.2f}s")
                    return True
                
                # POST should be less than 30% of all requests for normal browsing
                if post_count > 3 and (post_count / pattern['request_count']) > 0.3:
                    logger.warning(f"Abnormal POST ratio: {ip} - {post_count}/{pattern['request_count']} requests are POST")
                    self._ban_for_rate_limit(ip, f"Abnormal POST ratio: {post_count}/{pattern['request_count']} requests are POST")
                    return True
            
            # Standard rate limits
            
            # Check interval variance for bot detection
            if len(pattern.get('intervals', [])) >= 5:
                # Calculate standard deviation of request intervals
                mean_interval = sum(pattern['intervals']) / len(pattern['intervals'])
                variance = sum((x - mean_interval) ** 2 for x in pattern['intervals']) / len(pattern['intervals'])
                std_dev = variance ** 0.5
                
                # Very low standard deviation indicates bot-like behavior
                # Real humans have more variable intervals between requests
                if mean_interval < 1.0 and std_dev < 0.1 and pattern['request_count'] > 10:
                    logger.warning(f"Bot-like behavior detected: {ip} - Consistent intervals between requests")
                    self._ban_for_rate_limit(ip, "Bot-like behavior: Too consistent request timing")
                    return True
            
            # General rate limits - allow burst for small numbers of requests
            # but be strict after they've made many requests
            if pattern['request_count'] <= 10:
                # Allow higher rates for initial requests
                if request_rate > 10:  # More than 10 requests per second
                    logger.warning(f"High initial request rate: {ip} - {request_rate:.2f} req/s")
                    self._ban_for_rate_limit(ip, f"High initial request rate: {request_rate:.2f} req/s")
                    return True
            elif pattern['request_count'] <= 50:
                # Medium strict for established sessions
                if request_rate > 5:  # More than 5 requests per second
                    logger.warning(f"High sustained request rate: {ip} - {request_rate:.2f} req/s")
                    self._ban_for_rate_limit(ip, f"High sustained request rate: {request_rate:.2f} req/s")
                    return True
            else:
                # Very strict for long sessions
                if request_rate > 2:  # More than 2 requests per second over a long period
                    logger.warning(f"Excessive long-term request rate: {ip} - {request_rate:.2f} req/s")
                    self._ban_for_rate_limit(ip, f"Excessive long-term request rate: {request_rate:.2f} req/s")
                    return True
            
            # Check path diversity - normal users don't access many different URLs quickly
            if len(pattern['paths']) > 15 and duration < 10:
                logger.warning(f"Suspicious path scanning: {ip} - {len(pattern['paths'])} paths in {duration:.2f}s")
                self._ban_for_rate_limit(ip, f"Path scanning: {len(pattern['paths'])} paths in {duration:.2f}s")
                return True
            
            # Check method diversity - normal users don't use many different HTTP methods
            if 'methods' in pattern and len(pattern['methods']) >= 4 and duration < 30:
                logger.warning(f"Suspicious method usage: {ip} - {len(pattern['methods'])} methods in {duration:.2f}s")
                self._ban_for_rate_limit(ip, f"Unusual method usage: {len(pattern['methods'])} methods in {duration:.2f}s")
                return True
        
        return False
    
    def _ban_for_rate_limit(self, ip: str, reason: str):
        """Ban an IP for exceeding rate limits"""
        try:
            # Ban in database
            self.ban_manager.ban_ip(ip, f"Rate limit exceeded: {reason}", 86400)
            
            # Add to banned cache
            if hasattr(self.banned_ips_cache, 'add'):  # If it's a set
                self.banned_ips_cache.add(ip)
            else:  # If it's a dict
                self.banned_ips_cache[ip] = True
            
            # Apply firewall block
            self._apply_firewall_block(ip)
            
            # Update stats
            self.stats['rate_limited'] = self.stats.get('rate_limited', 0) + 1
            self.stats['blocked_ips'] += 1
            
            logger.warning(f"Banned IP {ip} for rate limiting: {reason}")
        except Exception as e:
            logger.error(f"Failed to ban IP {ip} for rate limiting: {e}")
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        with self.lock:
            return self.stats.copy()
    
    def reset_stats(self):
        """Reset monitoring statistics"""
        with self.lock:
            self.stats = {
                'blocked_requests': 0,
                'blocked_ips': 0,
                'blocked_devices': 0,
                'suspicious_requests': 0
            }

# Global instance for application-wide use
monitor_system = MonitorSystem() 