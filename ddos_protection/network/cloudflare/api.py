#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloudflare API Client for DDoS Protection
----------------------------------------
Handles integration with Cloudflare API for IP blocking and unblocking.
This is the PRIMARY protection mechanism, not a fallback.

Features:
- Block/unblock IPs via Cloudflare API
- List currently blocked IPs
- Retrieve analytics data
- Support for firewall rules
"""

import os
import time
import json
import logging
import asyncio
import hmac
import hashlib
from typing import Dict, Tuple, List, Any, Optional, Set, Union
import ipaddress
import aiohttp
import threading
from datetime import datetime, timedelta

# Configure environment variables
CF_API_EMAIL = os.environ.get('CF_API_EMAIL', '')
CF_API_KEY = os.environ.get('CF_API_KEY', '')
CF_ZONE_ID = os.environ.get('CF_ZONE_ID', '')

# Check if we're in development mode
CF_DEV_MODE = os.environ.get('CF_DEV_MODE', 'false').lower() == 'true'

# Configure logger
logger = logging.getLogger('ddos_protection.cloudflare.api')

# Fast lookup cache to minimize API calls
blocked_ips_cache: Set[str] = set()

class CloudflareAPIClient:
    """Cloudflare API client for DDoS protection."""
    
    def __init__(self, email=CF_API_EMAIL, api_key=CF_API_KEY, zone_id=CF_ZONE_ID):
        """
        Initialize Cloudflare API client.
        
        Args:
            email: Cloudflare account email
            api_key: Cloudflare API key
            zone_id: Cloudflare zone ID
        """
        self.email = email
        self.api_key = api_key
        self.zone_id = zone_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        # Define headers used for API requests
        self.headers = {
            "X-Auth-Email": self.email,
            "X-Auth-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Rate limiting parameters to avoid hitting Cloudflare API limits
        self.request_count = 0
        self.last_reset = time.time()
        self.max_requests = 1000  # Maximum requests per 5 minute period
        self.reset_interval = 300  # 5 minutes
        self.lock = threading.Lock()
        
        # For development mode
        self.dev_mode = CF_DEV_MODE
        if self.dev_mode:
            logger.info("Cloudflare API client initialized in DEVELOPMENT MODE (simulated API)")
            # In dev mode, store blocked IPs locally
            self.dev_blocked_ips = {}
        else:
            logger.info("Cloudflare API client initialized")
    
    async def _check_rate_limit(self):
        """Check and limit API request rate to avoid hitting Cloudflare limits."""
        with self.lock:
            current_time = time.time()
            
            # Reset counter if reset interval has passed
            if current_time - self.last_reset > self.reset_interval:
                self.request_count = 0
                self.last_reset = current_time
            
            # Check if we've hit the limit
            if self.request_count >= self.max_requests:
                # Wait until reset
                wait_time = self.reset_interval - (current_time - self.last_reset)
                if wait_time > 0:
                    logger.warning(f"Cloudflare API rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Reset counter
                    self.request_count = 0
                    self.last_reset = time.time()
            
            # Increment counter
            self.request_count += 1
    
    async def block_ip(self, ip_address: str, reason: str, duration: int = 86400) -> Tuple[bool, Dict]:
        """
        Block an IP address using Cloudflare Firewall Rules.
        
        Args:
            ip_address: IP address to block
            reason: Reason for blocking
            duration: Duration in seconds (default: 24 hours)
            
        Returns:
            Tuple[bool, Dict]: (success, response data)
        """
        global blocked_ips_cache
        
        # Skip OPTIONS requests
        if reason and "OPTIONS" in reason:
            logger.info(f"Skipping block for IP {ip_address} using OPTIONS request: {reason}")
            return True, {"success": True, "message": "Skipped OPTIONS request block"}
            
        # Skip device/fingerprint related blocks when using Cloudflare exclusively
        if reason and ("device" in reason.lower() or "fingerprint" in reason.lower()):
            logger.info(f"Skipping device-related block for IP {ip_address}: {reason}")
            return True, {"success": True, "message": "Skipped device-related block"}
        
        # Check if IP is already blocked (avoid unnecessary API calls)
        if ip_address in blocked_ips_cache:
            logger.debug(f"IP {ip_address} already blocked in Cloudflare")
            return True, {"success": True, "message": "IP already blocked"}
        
        # Development mode - simulate API call
        if self.dev_mode:
            logger.info(f"[DEV MODE] Simulating blocking IP {ip_address}: {reason}")
            blocked_ips_cache.add(ip_address)
            self.dev_blocked_ips[ip_address] = {
                "reason": reason,
                "added": time.time(),
                "duration": duration,
                "rule_id": f"dev-rule-{int(time.time())}-{hash(ip_address) % 10000}"
            }
            return True, {"success": True, "message": f"IP {ip_address} blocked (simulated in dev mode)"}
            
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Check if valid IP
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                logger.error(f"Invalid IP address: {ip_address}")
                return False, {"success": False, "message": "Invalid IP address"}
            
            # Check if rule already exists
            rule_id = await self._find_rule_by_ip(ip_address)
            if rule_id:
                # IP already blocked
                blocked_ips_cache.add(ip_address)
                return True, {"success": True, "message": "IP already blocked", "rule_id": rule_id}
                
            # Create rule description (truncate to avoid issues)
            max_reason_length = 128
            description = f"DDoS Protection: {reason[:max_reason_length]}" if reason else "DDoS Protection"
                
            # Create firewall rule to block IP
            expression = f"(ip.src eq {ip_address})"
            
            # Make request to Cloudflare API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/zones/{self.zone_id}/firewall/rules"
                
                # Prepare data
                data = {
                    "name": f"Block {ip_address} - {int(time.time())}",
                    "description": description,
                    "action": "block",
                    "filter": {
                        "expression": expression,
                        "paused": False
                    },
                    "products": ["firewall"]
                }
                
                # Send request
                async with session.post(url, headers=self.headers, json=data) as response:
                    result = await response.json()
                    
                    # Check if request was successful
                    if result.get("success", False):
                        logger.info(f"Successfully blocked IP {ip_address} in Cloudflare")
                        blocked_ips_cache.add(ip_address)
                        return True, result
                    else:
                        logger.error(f"Failed to block IP {ip_address} in Cloudflare: {result.get('errors', [])}")
                        return False, result
        except Exception as e:
            logger.error(f"Error blocking IP {ip_address} in Cloudflare: {e}")
            return False, {"success": False, "message": str(e)}
    
    async def unblock_ip(self, ip_address: str) -> Tuple[bool, Dict]:
        """
        Unblock an IP address in Cloudflare.
        
        Args:
            ip_address: IP address to unblock
            
        Returns:
            Tuple[bool, Dict]: (success, response data)
        """
        global blocked_ips_cache
        
        # Development mode - simulate API call
        if self.dev_mode:
            logger.info(f"[DEV MODE] Simulating unblocking IP {ip_address}")
            if ip_address in blocked_ips_cache:
                blocked_ips_cache.remove(ip_address)
            if ip_address in self.dev_blocked_ips:
                del self.dev_blocked_ips[ip_address]
            return True, {"success": True, "message": f"IP {ip_address} unblocked (simulated in dev mode)"}
        
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Find the rule ID for the IP
            rule_id = await self._find_rule_by_ip(ip_address)
            
            if not rule_id:
                logger.warning(f"IP {ip_address} not found in Cloudflare rules")
                # Remove from cache anyway
                if ip_address in blocked_ips_cache:
                    blocked_ips_cache.remove(ip_address)
                return True, {"success": True, "message": "IP not found in Cloudflare rules"}
                
            # Delete the rule
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/zones/{self.zone_id}/firewall/rules/{rule_id}"
                
                async with session.delete(url, headers=self.headers) as response:
                    result = await response.json()
                    
                    if result.get("success", False):
                        logger.info(f"Successfully unblocked IP {ip_address} in Cloudflare")
                        
                        # Remove from cache
                        if ip_address in blocked_ips_cache:
                            blocked_ips_cache.remove(ip_address)
                            
                        return True, result
                    else:
                        logger.error(f"Failed to unblock IP {ip_address} in Cloudflare: {result.get('errors', [])}")
                        return False, result
        except Exception as e:
            logger.error(f"Error unblocking IP {ip_address} in Cloudflare: {e}")
            return False, {"success": False, "message": str(e)}
    
    async def _find_rule_by_ip(self, ip_address: str) -> Optional[str]:
        """
        Find firewall rule ID for an IP address.
        
        Args:
            ip_address: IP address to find
            
        Returns:
            Optional[str]: Rule ID if found, None otherwise
        """
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Find firewall rule for the IP
            async with aiohttp.ClientSession() as session:
                # Use paging to get all rules (100 per page)
                page = 1
                per_page = 100
                
                while True:
                    url = f"{self.base_url}/zones/{self.zone_id}/firewall/rules?page={page}&per_page={per_page}"
                    
                    async with session.get(url, headers=self.headers) as response:
                        result = await response.json()
                        
                        if not result.get("success", False):
                            logger.error(f"Failed to fetch firewall rules: {result.get('errors', [])}")
                            return None
                            
                        # Check if any rule matches the IP
                        rules = result.get("result", [])
                        for rule in rules:
                            # Check if rule targets our IP
                            filter_expr = rule.get("filter", {}).get("expression", "")
                            if f"ip.src eq {ip_address}" in filter_expr:
                                return rule.get("id")
                        
                        # Check if there are more pages
                        result_info = result.get("result_info", {})
                        if page >= result_info.get("total_pages", 0) or not rules:
                            break
                            
                        # Move to next page
                        page += 1
                
                return None
        except Exception as e:
            logger.error(f"Error finding rule for IP {ip_address}: {e}")
            return None
    
    async def get_blocked_ips(self) -> List[Dict]:
        """
        Get list of blocked IPs in Cloudflare.
        
        Returns:
            List[Dict]: List of blocked IPs with rule details
        """
        global blocked_ips_cache
        
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Get all firewall rules
            async with aiohttp.ClientSession() as session:
                # Use paging to get all rules (100 per page)
                page = 1
                per_page = 100
                blocked_ips = []
                
                while True:
                    url = f"{self.base_url}/zones/{self.zone_id}/firewall/rules?page={page}&per_page={per_page}"
                    
                    async with session.get(url, headers=self.headers) as response:
                        result = await response.json()
                        
                        if not result.get("success", False):
                            logger.error(f"Failed to fetch firewall rules: {result.get('errors', [])}")
                            return []
                            
                        # Find rules that block IPs
                        rules = result.get("result", [])
                        for rule in rules:
                            # Check if rule targets an IP
                            filter_expr = rule.get("filter", {}).get("expression", "")
                            if "ip.src eq " in filter_expr:
                                # Extract IP address
                                import re
                                ip_match = re.search(r'ip\.src eq (\d+\.\d+\.\d+\.\d+)', filter_expr)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    blocked_ips.append({
                                        "ip": ip,
                                        "rule_id": rule.get("id"),
                                        "description": rule.get("description", ""),
                                        "created_on": rule.get("created_on")
                                    })
                                    
                                    # Update cache
                                    blocked_ips_cache.add(ip)
                        
                        # Check if there are more pages
                        result_info = result.get("result_info", {})
                        if page >= result_info.get("total_pages", 0) or not rules:
                            break
                            
                        # Move to next page
                        page += 1
                
                return blocked_ips
        except Exception as e:
            logger.error(f"Error fetching blocked IPs: {e}")
            return []
    
    async def create_firewall_rule(self, expression: str, action: str, description: str) -> Tuple[bool, Dict]:
        """
        Create a custom firewall rule in Cloudflare.
        
        Args:
            expression: Filter expression
            action: Action (block, challenge, js_challenge)
            description: Rule description
            
        Returns:
            Tuple[bool, Dict]: (success, response data)
        """
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Make request to Cloudflare API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/zones/{self.zone_id}/firewall/rules"
                
                # Prepare data
                data = {
                    "name": f"Rule {int(time.time())}",
                    "description": description,
                    "action": action,
                    "filter": {
                        "expression": expression,
                        "paused": False
                    },
                    "products": ["firewall"]
                }
                
                # Send request
                async with session.post(url, headers=self.headers, json=data) as response:
                    result = await response.json()
                    
                    # Check if request was successful
                    if result.get("success", False):
                        logger.info(f"Successfully created firewall rule in Cloudflare")
                        return True, result
                    else:
                        logger.error(f"Failed to create firewall rule in Cloudflare: {result.get('errors', [])}")
                        return False, result
        except Exception as e:
            logger.error(f"Error creating firewall rule in Cloudflare: {e}")
            return False, {"success": False, "message": str(e)}
    
    async def list_blocked_ips(self) -> Dict[str, str]:
        """
        Get list of blocked IPs in Cloudflare.
        
        Returns:
            Dict[str, str]: Dictionary of blocked IPs and reasons
        """
        # Development mode - return simulated blocked IPs
        if self.dev_mode:
            logger.info("[DEV MODE] Simulating list_blocked_ips call")
            return self.dev_blocked_ips
        
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        try:
            # Get all firewall rules
            rules = await self.get_blocked_ips()
            
            # Extract IPs and reasons
            blocked_ips = {}
            for rule in rules:
                ip = rule.get("ip")
                description = rule.get("description", "")
                
                if ip:
                    blocked_ips[ip] = description
                    # Update cache
                    blocked_ips_cache.add(ip)
            
            return blocked_ips
        except Exception as e:
            logger.error(f"Error listing blocked IPs: {e}")
            return {}
    
    async def is_ip_blocked(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an IP is blocked in Cloudflare.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Tuple[bool, Optional[str]]: (is_blocked, reason)
        """
        # Fast check using local cache first
        if ip_address in blocked_ips_cache:
            return True, "IP in local block cache"
        
        # Development mode - check simulated blocked IPs
        if self.dev_mode:
            is_blocked = ip_address in self.dev_blocked_ips
            reason = self.dev_blocked_ips.get(ip_address, {}).get("reason", "Unknown") if is_blocked else None
            return is_blocked, reason
            
        # Avoid rate limit issues
        await self._check_rate_limit()
        
        # Not in cache, check with API
        rule_id = await self._find_rule_by_ip(ip_address)
        if rule_id:
            # IP is blocked, add to cache
            blocked_ips_cache.add(ip_address)
            return True, rule_id
            
        return False, None

# Initialize global client
cf_client = CloudflareAPIClient() if CF_API_EMAIL and CF_API_KEY and CF_ZONE_ID else None

# Integration with the existing ban system
def integrate_with_ban_manager():
    """Integrate Cloudflare with the ban manager system."""
    try:
        from ddos_protection.storage import ban_manager
        
        # Save original methods to call them later
        original_ban_ip = ban_manager.ban_ip
        original_unban_ip = ban_manager.unban_ip
        
        # جمع العناوين المحظورة لإخراج تقرير مجمع
        _blocked_ips_batch = []
        _last_log_time = [time.time()]  # استخدام قائمة للمشاركة بين الدوال
        _BATCH_LOG_INTERVAL = 10  # ثواني
        
        # Override the ban_ip method to also block on Cloudflare
        def enhanced_ban_ip(ip, reason, duration=None):
            # Call the original method first
            original_ban_ip(ip, reason, duration)
            
            # جمع العناوين المحظورة في دفعة
            _blocked_ips_batch.append(ip)
            
            # Then block on Cloudflare if enabled - without duplicate log
            if CF_API_EMAIL and CF_API_KEY and CF_ZONE_ID and cf_client:
                cf_client.block_ip(ip, reason, duration)
            
            # طباعة تقرير مجمع كل فترة زمنية 
            current_time = time.time()
            if current_time - _last_log_time[0] >= _BATCH_LOG_INTERVAL and _blocked_ips_batch:
                logger.info(f"Batch summary: Blocked {len(_blocked_ips_batch)} IPs in Cloudflare")
                _blocked_ips_batch.clear()
                _last_log_time[0] = current_time
        
        # Override the unban_ip method to also unblock on Cloudflare
        def enhanced_unban_ip(ip):
            # Call the original method first
            result = original_unban_ip(ip)
            
            # Then unblock on Cloudflare if enabled
            if CF_API_EMAIL and CF_API_KEY and CF_ZONE_ID and cf_client:
                cf_client.unblock_ip(ip)
                
            return result
        
        # Replace the original methods with enhanced ones
        ban_manager.ban_ip = enhanced_ban_ip
        ban_manager.unban_ip = enhanced_unban_ip
        
        logger.info("Successfully integrated Cloudflare with the ban manager")
        return True
    except ImportError:
        logger.error("Failed to import ban_manager, integration not completed")
        return False
    except Exception as e:
        logger.error(f"Error integrating with ban manager: {e}")
        return False

def sync_from_cloudflare():
    """Sync blocked IPs from Cloudflare to the local ban system."""
    if not CF_API_EMAIL or not CF_API_KEY or not CF_ZONE_ID or not cf_client:
        logger.warning("Cloudflare integration not enabled, skipping sync")
        return False
        
    try:
        from ddos_protection.storage import ban_manager
        
        # Save original method to avoid infinite recursion
        original_ban_ip = ban_manager.ban_ip
        
        # Get blocked IPs from Cloudflare
        blocked_ips = cf_client.get_blocked_ips()
        
        # Add each IP to the local ban system
        count = 0
        for ip_data in blocked_ips:
            ip = ip_data.get("ip")
            reason = ip_data.get("description", "Synced from Cloudflare")
            
            # Check if the IP is already banned locally
            if not ban_manager.is_banned(ip):
                # Call the original method to avoid recursion
                original_ban_ip(ip, reason)
                count += 1
        
        # طباعة رسالة واحدة تلخص عدد العناوين المحظورة
        if count > 0:
            logger.info(f"Summary: Synced {count} blocked IPs from Cloudflare")
        return True
    except ImportError:
        logger.error("Failed to import ban_manager, sync not completed")
        return False
    except Exception as e:
        logger.error(f"Error syncing from Cloudflare: {e}")
        return False

# Schedule periodic sync
def start_periodic_sync(interval=3600):
    """Start periodic sync from Cloudflare to local ban system.
    
    Args:
        interval: Sync interval in seconds (default: 1 hour)
    """
    if not CF_API_EMAIL or not CF_API_KEY or not CF_ZONE_ID or not cf_client:
        logger.warning("Cloudflare integration not enabled, periodic sync not started")
        return False
    
    # منع تشغيل مهام متعددة - استخدام متغير ثابت
    if hasattr(start_periodic_sync, '_is_running') and start_periodic_sync._is_running:
        logger.info("Periodic sync already running, not starting another one")
        return True
    
    try:
        import threading
        
        def sync_job():
            while True:
                try:
                    # تنفيذ المزامنة بدون رسائل سجل متكررة
                    sync_from_cloudflare()
                except Exception as e:
                    logger.error(f"Error in periodic sync: {e}")
                time.sleep(interval)
        
        # تعيين علامة لمنع تشغيل مهام متعددة
        start_periodic_sync._is_running = True
        
        sync_thread = threading.Thread(target=sync_job, daemon=True)
        sync_thread.start()
        logger.info(f"Started periodic sync from Cloudflare every {interval} seconds")
        return True
    except Exception as e:
        logger.error(f"Failed to start periodic sync: {e}")
        return False 