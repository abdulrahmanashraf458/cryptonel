#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Attack Mitigator Module
-----------------------------------------------
Responsible for implementing various DDoS mitigation strategies:
1. Rate limiting with adaptive thresholds
2. Circuit breaker pattern for endpoint protection
3. Tarpitting for suspicious clients
4. Traffic redirection (honeypot/nullroute)
5. Challenge-response mechanisms
"""

import asyncio
import logging
import time
import random
import os
import json
import base64
import hashlib
import hmac
from typing import Dict, List, Set, Tuple, Optional, Union, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import subprocess
import ipaddress
import traceback
import sys

# Local imports
from ddos_protection.config import Config
from ddos_protection.utils import (
    is_valid_ip,
    get_server_resources,
    generate_challenge,
    verify_challenge_response,
    execute_command
)
from ddos_protection.storage import storage_manager
from ddos_protection.storage import ban_manager

# Configure logger
logger = logging.getLogger("ddos_protection.mitigator")

# إضافة فلتر لتقليل تكرار سجلات الحظر
class DuplicateBlockFilter(logging.Filter):
    """فلتر لتجنب تكرار رسائل الحظر للعناوين IP المتكررة"""
    
    def __init__(self, name=""):
        super().__init__(name)
        self.blocked_ips = set()
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # ساعة واحدة
        self.max_log_count = {}  # عدد مرات تسجيل كل عنوان IP
        self.log_limit = 3  # الحد الأقصى للسجلات لكل عنوان IP
    
    def filter(self, record):
        """تحقق مما إذا كان يجب تسجيل هذه الرسالة أم لا"""
        # تنظيف دوري للسجلات القديمة
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.blocked_ips.clear()
            self.max_log_count.clear()
            self.last_cleanup = current_time
        
        # تحقق مما إذا كانت رسالة تتعلق بحظر IP
        message = record.getMessage()
        if "block" in message.lower() and "ip" in message.lower():
            # استخراج عنوان IP من الرسالة
            import re
            ip_match = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", message)
            
            if ip_match:
                ip = ip_match.group(0)
                
                # تتبع عدد مرات تسجيل هذا العنوان
                if ip not in self.max_log_count:
                    self.max_log_count[ip] = 0
                
                self.max_log_count[ip] += 1
                
                # إذا كان عدد مرات التسجيل أكبر من الحد الأقصى، تجاهل التسجيل
                if self.max_log_count[ip] > self.log_limit:
                    if self.max_log_count[ip] % 100 == 0:  # تسجيل كل 100 مرة للإشارة إلى استمرار النشاط
                        record.msg = f"[Summarized] {record.msg} (logged 1/{100} events)"
                        return True
                    return False
                
                # إذا كان هذا العنوان محظورًا بالفعل، تجاهل التسجيل المتكرر
                if ip in self.blocked_ips and "applied network-level" in message.lower():
                    return False
                
                # إضافة العنوان إلى قائمة العناوين المحظورة
                self.blocked_ips.add(ip)
        
        # تسجيل جميع الرسائل الأخرى
        return True

# تطبيق الفلتر على السجل
block_filter = DuplicateBlockFilter()
logger.addFilter(block_filter)

# إضافة فلتر لسجل الأمان أيضًا
security_logger = logging.getLogger("security")
security_logger.addFilter(block_filter)

class RateLimiter:
    """
    Implements adaptive rate limiting for requests
    with dynamic thresholds based on server load.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.ip_counters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.endpoint_counters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.global_counter: deque = deque(maxlen=10000)
        self.last_resource_check = 0
        self.current_threshold_multiplier = 1.0
        self.last_cleanup = time.time()
    
    async def update_thresholds(self):
        """Update rate limiting thresholds based on current server resources."""
        current_time = time.time()
        
        # Only check resources periodically to reduce overhead
        if current_time - self.last_resource_check < self.config.mitigator.resource_check_interval:
            return
            
        self.last_resource_check = current_time
        
        try:
            # Get current server resource usage
            cpu_usage, memory_usage, network_usage = await get_server_resources()
            
            # Calculate a dynamic multiplier based on resource usage
            # Lower value when resources are constrained
            cpu_factor = max(0.5, 1.0 - (cpu_usage / 100) * 0.8)
            memory_factor = max(0.5, 1.0 - (memory_usage / 100) * 0.8)
            
            # Network usage is most critical for DDoS
            network_factor = max(0.3, 1.0 - (network_usage / 100) * 0.9)
            
            # Final multiplier with minimum value of 0.3 (30% of normal rate)
            self.current_threshold_multiplier = max(0.3, min(1.0, 
                                                          (cpu_factor + memory_factor + network_factor) / 3))
            
            logger.debug(f"Rate limit multiplier updated: {self.current_threshold_multiplier:.2f} "
                       f"(CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%, Network: {network_usage:.1f}%)")
        
        except Exception as e:
            logger.error(f"Error updating rate limit thresholds: {e}")
            # Default to more restrictive limits on error
            self.current_threshold_multiplier = 0.7
    
    def cleanup_old_records(self):
        """Remove expired timestamps from counters."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.config.mitigator.cleanup_interval:
            return
            
        self.last_cleanup = current_time
        window = self.config.mitigator.rate_window
        cutoff = current_time - window
        
        # Cleanup global counter
        while self.global_counter and self.global_counter[0] < cutoff:
            self.global_counter.popleft()
        
        # Cleanup IP counters
        for ip in list(self.ip_counters.keys()):
            while self.ip_counters[ip] and self.ip_counters[ip][0] < cutoff:
                self.ip_counters[ip].popleft()
            
            # Remove empty counters
            if not self.ip_counters[ip]:
                del self.ip_counters[ip]
        
        # Cleanup endpoint counters
        for endpoint in list(self.endpoint_counters.keys()):
            while self.endpoint_counters[endpoint] and self.endpoint_counters[endpoint][0] < cutoff:
                self.endpoint_counters[endpoint].popleft()
            
            # Remove empty counters
            if not self.endpoint_counters[endpoint]:
                del self.endpoint_counters[endpoint]
    
    async def check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """
        Check if request exceeds rate limits.
        
        Args:
            ip: Client IP address
            endpoint: Request endpoint path
            
        Returns:
            bool: True if request is allowed, False if it should be blocked
        """
        current_time = time.time()
        
        # Add timestamp to counters
        self.global_counter.append(current_time)
        self.ip_counters[ip].append(current_time)
        self.endpoint_counters[endpoint].append(current_time)
        
        # Update thresholds and clean up periodically
        await self.update_thresholds()
        self.cleanup_old_records()
        
        # Get effective rate limits with dynamic adjustment
        window = self.config.mitigator.rate_window
        global_limit = int(self.config.mitigator.global_rate_limit * self.current_threshold_multiplier)
        ip_limit = int(self.config.mitigator.ip_rate_limit * self.current_threshold_multiplier)
        endpoint_limit = int(self.config.mitigator.endpoint_rate_limit * self.current_threshold_multiplier)
        
        # Apply stricter limits for critical endpoints
        if endpoint in self.config.mitigator.critical_endpoints:
            endpoint_limit = int(endpoint_limit * 0.7)  # 70% of normal limit
            
        # Calculate current rates
        global_count = len(self.global_counter)
        ip_count = len(self.ip_counters[ip])
        endpoint_count = len(self.endpoint_counters[endpoint])
        
        # ----------------- IMPROVED LOGIC TO PREVENT FALSE POSITIVES -----------------
        
        # 1. Add progressive rate limiting - first warn, then enforce
        is_localhost = ip == "127.0.0.1" or ip == "::1" or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")
        
        # 2. Check if it's a legitimate user based on previous successful interactions
        # We'll need to add tracking of successful responses somewhere else
        
        # 3. Only block if multiple thresholds are exceeded
        thresholds_exceeded = 0
        thresholds_exceeded += 1 if global_count > global_limit else 0
        thresholds_exceeded += 1 if ip_count > ip_limit else 0
        thresholds_exceeded += 1 if endpoint_count > endpoint_limit else 0
        
        # Critical: For effective protection while preventing site self-DoS:
        # - Set higher threshold for local/internal IPs
        # - Multiple threshold violations required before blocking
        blocking_threshold = 3  # Default: require all 3 limits to be exceeded for blocking
        
        # For non-critical endpoints, give more leeway to internal IPs 
        if is_localhost and endpoint not in self.config.mitigator.critical_endpoints:
            blocking_threshold = 5  # Effectively never block internal IPs on non-critical endpoints
        
        if thresholds_exceeded >= blocking_threshold:
            # If this happens during high server load, likely a real attack
            if self.current_threshold_multiplier < 0.7:
                logger.warning(f"Under heavy load, rate limit exceeded for {ip}: {ip_count}/{ip_limit} requests in {window}s")
                return False  # Block the request
            
            # If server load is normal, log but still allow most requests (adaptive policy)
            if global_count > global_limit * 1.5:  # If extremely high global rate
                logger.warning(f"Extreme global rate limit exceeded: {global_count}/{global_limit} requests in {window}s")
                return False  # Block the request only in extreme cases
        
        # Always allow legitimate traffic
        return True


class CircuitBreaker:
    """
    Implements circuit breaker pattern to temporarily disable endpoints 
    that are overwhelmed during attacks.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.circuits: Dict[str, Dict[str, Any]] = {}
        self.global_circuit = {
            "state": "closed",  # closed, open, or half-open
            "failure_count": 0,
            "last_failure": 0,
            "last_success": time.time(),
            "next_attempt": 0
        }
    
    def _get_circuit(self, endpoint: str) -> Dict[str, Any]:
        """Get or create circuit for an endpoint."""
        if endpoint not in self.circuits:
            self.circuits[endpoint] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": 0,
                "last_success": time.time(),
                "next_attempt": 0
            }
        return self.circuits[endpoint]
    
    def record_success(self, endpoint: str):
        """Record a successful request for an endpoint."""
        circuit = self._get_circuit(endpoint)
        current_time = time.time()
        
        circuit["last_success"] = current_time
        
        # If in half-open state, close the circuit after success
        if circuit["state"] == "half-open":
            circuit["state"] = "closed"
            circuit["failure_count"] = 0
            logger.info(f"Circuit closed for endpoint {endpoint} after successful request")
        
        # For global circuit
        if self.global_circuit["state"] == "half-open":
            self.global_circuit["state"] = "closed"
            self.global_circuit["failure_count"] = 0
            logger.info("Global circuit closed after successful request")
    
    def record_failure(self, endpoint: str):
        """Record a failed request for an endpoint."""
        circuit = self._get_circuit(endpoint)
        current_time = time.time()
        
        circuit["last_failure"] = current_time
        circuit["failure_count"] += 1
        
        # Check if we should open the circuit
        threshold = (self.config.mitigator.circuit_threshold_critical 
                   if endpoint in self.config.mitigator.critical_endpoints 
                   else self.config.mitigator.circuit_threshold)
                   
        if circuit["failure_count"] >= threshold and circuit["state"] == "closed":
            circuit["state"] = "open"
            circuit["next_attempt"] = current_time + self.config.mitigator.circuit_reset_timeout
            logger.warning(f"Circuit opened for endpoint {endpoint} after {threshold} failures")
        
        # For global circuit
        self.global_circuit["last_failure"] = current_time
        self.global_circuit["failure_count"] += 1
        
        if (self.global_circuit["failure_count"] >= self.config.mitigator.global_circuit_threshold 
            and self.global_circuit["state"] == "closed"):
            self.global_circuit["state"] = "open"
            self.global_circuit["next_attempt"] = current_time + self.config.mitigator.circuit_reset_timeout
            logger.warning(f"Global circuit opened after {self.config.mitigator.global_circuit_threshold} failures")
    
    def check_circuit_status(self, endpoint: str) -> bool:
        """
        Check if request should be allowed based on circuit status.
        
        Args:
            endpoint: Request endpoint path
            
        Returns:
            bool: True if request is allowed, False if circuit is open
        """
        circuit = self._get_circuit(endpoint)
        current_time = time.time()
        
        # Check global circuit first
        if self.global_circuit["state"] == "open":
            # Check if it's time to try again
            if current_time >= self.global_circuit["next_attempt"]:
                self.global_circuit["state"] = "half-open"
                logger.info("Global circuit changed to half-open state")
            else:
                return False  # Global circuit is open
        
        # Then check endpoint-specific circuit
        if circuit["state"] == "open":
            # Check if it's time to try again
            if current_time >= circuit["next_attempt"]:
                circuit["state"] = "half-open"
                logger.info(f"Circuit for endpoint {endpoint} changed to half-open state")
            else:
                return False  # Circuit is open
        
        return True  # Circuit is closed or half-open, allow the request


class Tarpitter:
    """Implementation of Tarpitting technique to delay suspicious requests."""
    
    def __init__(self, config: Config):
        """
        Create a new tarpitting system.
        
        Args:
            config: DDoS protection system configuration
        """
        self.config = config
        
        # Use persistent storage to track suspicious IPs
        self.suspicious_ips = storage_manager.behavior_tracking
        logger.debug("Tarpitting system initialized")
    
    async def apply_tarpit(self, ip: str, severity: float = 1.0) -> float:
        """
        Apply tarpitting to a suspicious client.
        
        Args:
            ip: Client IP address
            severity: Severity factor (1.0 = normal, higher = more delay)
            
        Returns:
            float: Applied delay in seconds
        """
        # تعديل مؤقت: تعطيل استثناء العناوين المحلية للاختبار
        # Skip tarpitting for local/internal addresses
        #if ip == "127.0.0.1" or ip == "::1" or ip.startswith("192.168.") or ip.startswith("10."):
        #    logger.debug(f"Skipping tarpit for local address: {ip}")
        #    return 0.0
        
        # Get suspicious client data
        info = self.suspicious_ips.get(ip)
        
        # If IP is not in suspicious list, don't apply any delay
        if not info:
            return 0.0
        
        # Calculate suspicion level from 0-10
        suspicion_level = info.get('level', 0)
        
        # Determine delay based on suspicion level
        if suspicion_level < 3:
            # Low suspicion clients get minimal delay
            delay = self.config.mitigator.tarpit_base_delay
        elif suspicion_level < 7:
            # Medium suspicion clients get moderate delay
            delay_range = self.config.mitigator.tarpit_max_delay - self.config.mitigator.tarpit_base_delay
            delay = self.config.mitigator.tarpit_base_delay + (delay_range * 0.5)
        else:
            # High suspicion clients get full delay
            delay = self.config.mitigator.tarpit_max_delay
        
        # Apply severity factor
        delay *= severity
        
        # Add random element to avoid detection
        random_factor = 1.0 + random.uniform(-0.2, 0.2)
        delay *= random_factor
        
        # Trim delay to maximum
        delay = min(delay, self.config.mitigator.tarpit_max_delay)
        
        logger.debug(f"Applied delay {delay:.2f}s to {ip} (suspicion level: {suspicion_level})")
        return delay
    
    def add_suspicious_ip(self, ip: str, level: int = 1) -> None:
        """
        Add an IP address to the suspicious list.
        
        Args:
            ip: IP address to add
            level: Initial suspicion level (1-10)
        """
        # Get current suspicious client data if exists
        info = self.suspicious_ips.get(ip, {
            'level': 0,
            'first_seen': time.time(),
            'hits': 0
        })
        
        # Increase suspicion level
        current_level = info.get('level', 0)
        info['level'] = min(10, current_level + level)
        info['hits'] = info.get('hits', 0) + 1
        info['last_update'] = time.time()
        
        # Store updated data
        # Use 1 day TTL for low suspicion IPs
        # Use 1 week TTL for high suspicion IPs
        ttl = 86400 if info['level'] < 5 else 604800
        self.suspicious_ips.set(ip, info, ttl)
        
        logger.debug(f"Added/updated suspicious IP: {ip} (level: {info['level']})")
    
    def remove_suspicious_ip(self, ip: str) -> bool:
        """
        Remove an IP address from the suspicious list.
        
        Args:
            ip: IP address to remove
            
        Returns:
            bool: True if removal was successful
        """
        return self.suspicious_ips.delete(ip)
    
    def is_suspicious(self, ip: str) -> bool:
        """
        Check if an IP address is suspicious.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if IP is suspicious
        """
        return self.suspicious_ips.get(ip) is not None
    
    def get_suspicious_level(self, ip: str) -> int:
        """
        Get suspicion level for an IP address.
        
        Args:
            ip: IP address to check
            
        Returns:
            int: Suspicion level (0 if not suspicious)
        """
        info = self.suspicious_ips.get(ip)
        return info.get('level', 0) if info else 0
    
    def cleanup_old_records(self) -> None:
        """
        Clean up expired suspicious IP records.
        This method is called periodically from AttackMitigator._periodic_cleanup().
        """
        try:
            # Use storage manager's built-in cleanup function
            if hasattr(self, 'suspicious_ips') and self.suspicious_ips:
                self.suspicious_ips.maybe_cleanup()
                logger.debug("Tarpitter cleanup completed")
        except Exception as e:
            logger.error(f"Error during tarpitter cleanup: {e}")


class TrafficRedirector:
    """
    Redirects malicious traffic to honeypots or null routes
    using iptables/nftables rules.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.redirected_ips: Dict[str, datetime] = {}
        self.redirect_enabled = self._check_redirect_capability()
        
        if not self.redirect_enabled:
            logger.warning("Traffic redirection disabled: required tools not available or insufficient permissions")
    
    def _check_redirect_capability(self) -> bool:
        """Check if system has necessary permissions and tools for traffic redirection."""
        try:
            import platform
            os_name = platform.system().lower()
            
            # For Windows systems, check for netsh
            if os_name == 'windows':
                # Check if we have access to netsh
                try:
                    result = subprocess.run(
                        ["where", "netsh"], 
                        capture_output=True, 
                        text=True,
                        timeout=2,
                        check=False
                    )
                    has_netsh = result.returncode == 0
                    
                    if not has_netsh:
                        logger.debug("netsh command not found on Windows system")
                        return False
                    
                    # Check if we have permission to use netsh
                    has_permission = True  # Assume we have permission initially
                    return has_permission and has_netsh
                except Exception as e:
                    logger.debug(f"Error checking netsh on Windows: {e}")
                    return False
            else:
                # For Linux/Unix systems
                # Check if we're running as root or have sudo capability
                has_permission = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
                
                # If not root, check for sudo
                if not has_permission:
                    try:
                        result = subprocess.run(
                            ["sudo", "-n", "true"], 
                            capture_output=True,
                            timeout=2,
                            check=False
                        )
                        has_permission = result.returncode == 0
                    except Exception as e:
                        logger.debug(f"Error checking sudo permission: {e}")
                        has_permission = False
                
                # Check for iptables or nftables
                try:
                    has_iptables = subprocess.run(
                        ["which", "iptables"], 
                        capture_output=True,
                        timeout=2,
                        check=False
                    ).returncode == 0
                    
                    has_nftables = subprocess.run(
                        ["which", "nft"],
                        capture_output=True,
                        timeout=2,
                        check=False
                    ).returncode == 0
                    
                    return has_permission and (has_iptables or has_nftables)
                except Exception as e:
                    logger.debug(f"Error checking iptables/nftables: {e}")
                    return False
        except Exception as e:
            logger.error(f"Error checking redirect capability: {e}")
            return False
    
    async def redirect_ip(self, ip: str, duration: int = 3600) -> bool:
        """
        Redirect traffic from an IP to honeypot or null route.
        
        Args:
            ip: IP address to redirect
            duration: Duration in seconds for the redirection
            
        Returns:
            bool: True if redirection was successful, False otherwise
        """
        if not self.redirect_enabled or not is_valid_ip(ip):
            return False
        
        try:
            destination = self.config.mitigator.redirect_destination
            import platform
            os_name = platform.system().lower()
            
            # Execute platform-specific commands
            if os_name == 'windows':
                # Windows uses netsh for firewall management
                cmd = [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f'name="DDoS_Block_{ip}"',
                    "dir=in",
                    "action=block",
                    f"remoteip={ip}"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
            else:
                # Linux systems - choose between nftables and iptables
                if subprocess.run(["which", "nft"], capture_output=True, check=False).returncode == 0:
                    # Use nftables if available (more modern)
                    cmd = [
                        "sudo", "nft", "add", "rule", "inet", "filter", "input", 
                        f"ip saddr {ip}", "counter", f"goto {destination}"
                    ]
                else:
                    # Fall back to iptables
                    cmd = [
                        "sudo", "iptables", "-A", "INPUT", 
                        "-s", ip, "-j", destination.upper()
                    ]
                
                # Execute the command
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                expiry_time = datetime.now() + timedelta(seconds=duration)
                self.redirected_ips[ip] = expiry_time
                logger.info(f"Redirected traffic from IP {ip} to {destination} until {expiry_time.isoformat()}")
                return True
            else:
                logger.error(f"Failed to redirect IP {ip}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error redirecting IP {ip}: {e}")
            return False
    
    async def remove_redirect(self, ip: str) -> bool:
        """
        Remove traffic redirection for an IP.
        
        Args:
            ip: IP address to unredirect
            
        Returns:
            bool: True if removal was successful, False otherwise
        """
        if not self.redirect_enabled or not is_valid_ip(ip):
            return False
            
        try:
            destination = self.config.mitigator.redirect_destination
            import platform
            os_name = platform.system().lower()
            
            # Execute platform-specific commands
            if os_name == 'windows':
                # Windows uses netsh for firewall management
                cmd = [
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f'name="DDoS_Block_{ip}"'
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
            else:
                # Linux systems - choose between nftables and iptables
                if subprocess.run(["which", "nft"], capture_output=True, check=False).returncode == 0:
                    # Use nftables if available
                    cmd = [
                        "sudo", "nft", "delete", "rule", "inet", "filter", "input", 
                        "handle", f"ip saddr {ip}"
                    ]
                else:
                    # Fall back to iptables
                    cmd = [
                        "sudo", "iptables", "-D", "INPUT", 
                        "-s", ip, "-j", destination.upper()
                    ]
                
                # Execute the command
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                if ip in self.redirected_ips:
                    del self.redirected_ips[ip]
                logger.info(f"Removed traffic redirection for IP {ip}")
                return True
            else:
                logger.error(f"Failed to remove redirection for IP {ip}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing redirection for IP {ip}: {e}")
            return False
    
    async def cleanup_expired_redirects(self):
        """Remove expired traffic redirections."""
        now = datetime.now()
        expired_ips = [ip for ip, expiry in self.redirected_ips.items() if expiry <= now]
        
        for ip in expired_ips:
            await self.remove_redirect(ip)


class ChallengeManager:
    """
    Manages client challenges for suspicious requests.
    Implements lightweight JavaScript challenges or CAPTCHA alternatives.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.challenges: Dict[str, Dict[str, Any]] = {}
        self.last_cleanup = time.time()
        self.secret_key = config.mitigator.challenge_secret or os.urandom(32).hex()
    
    def cleanup_expired(self):
        """Remove expired challenges."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.config.mitigator.cleanup_interval:
            return
            
        self.last_cleanup = current_time
        expiry = self.config.mitigator.challenge_expiry
        
        # Find and remove expired entries
        expired_tokens = [token for token, data in self.challenges.items() 
                        if current_time - data["timestamp"] > expiry]
        
        for token in expired_tokens:
            del self.challenges[token]
            
        if expired_tokens:
            logger.debug(f"Removed {len(expired_tokens)} expired challenges")
    
    def generate_token(self, ip: str, difficulty: int = 1) -> str:
        """
        Generate a unique token for a challenge.
        
        Args:
            ip: Client IP address
            difficulty: Challenge difficulty level (1-5)
            
        Returns:
            str: Challenge token
        """
        timestamp = int(time.time())
        random_part = os.urandom(8).hex()
        
        # Combine data into a base string
        base = f"{ip}:{timestamp}:{random_part}:{difficulty}"
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            base.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Combine into token
        token = f"{base}:{signature}"
        return base64.urlsafe_b64encode(token.encode('utf-8')).decode('utf-8')
    
    def create_challenge(self, ip: str, user_agent: str) -> Dict[str, Any]:
        """
        Create a new challenge for a client.
        
        Args:
            ip: Client IP address
            user_agent: Client user agent string
            
        Returns:
            Dict[str, Any]: Challenge data including token and JavaScript challenge
        """
        self.cleanup_expired()
        
        # Determine challenge difficulty based on client behavior
        # More suspicious clients get harder challenges
        difficulty = 1
        if ip in self.challenges:
            # Increase difficulty for repeated challenges
            previous_challenges = sum(1 for c in self.challenges.values() if c["ip"] == ip)
            difficulty = min(5, 1 + previous_challenges // 2)
        
        # Generate token
        token = self.generate_token(ip, difficulty)
        
        # Generate JavaScript challenge
        js_challenge, expected_answer = generate_challenge(difficulty)
        
        # Store challenge data
        challenge_data = {
            "ip": ip,
            "token": token,
            "difficulty": difficulty,
            "timestamp": time.time(),
            "expected_answer": expected_answer,
            "solved": False,
            "attempts": 0,
            "user_agent": user_agent
        }
        
        self.challenges[token] = challenge_data
        
        # Return data needed for client challenge
        return {
            "token": token,
            "challenge": js_challenge,
            "difficulty": difficulty,
            "expires_in": self.config.mitigator.challenge_expiry
        }
    
    def verify_challenge(self, token: str, answer: str) -> bool:
        """
        Verify a challenge response.
        
        Args:
            token: Challenge token
            answer: Client's answer to the challenge
            
        Returns:
            bool: True if challenge is solved correctly, False otherwise
        """
        self.cleanup_expired()
        
        # Check if token exists
        if token not in self.challenges:
            logger.warning(f"Challenge verification attempt with invalid token: {token}")
            return False
        
        challenge = self.challenges[token]
        challenge["attempts"] += 1
        
        # Check if already solved
        if challenge["solved"]:
            return True
        
        # Check if too many attempts
        if challenge["attempts"] > self.config.mitigator.max_challenge_attempts:
            logger.warning(f"Too many challenge attempts for token {token} from IP {challenge['ip']}")
            return False
        
        # Verify the answer
        is_correct = verify_challenge_response(answer, challenge["expected_answer"])
        
        if is_correct:
            challenge["solved"] = True
            logger.info(f"Challenge solved successfully by IP {challenge['ip']}")
        
        return is_correct
    
    def is_challenge_solved(self, token: str) -> bool:
        """
        Check if a challenge has been solved.
        
        Args:
            token: Challenge token
            
        Returns:
            bool: True if challenge is solved, False otherwise
        """
        return token in self.challenges and self.challenges[token]["solved"]


class AttackMitigator:
    """
    Main class for orchestrating DDoS mitigation strategies.
    Combines rate limiting, circuit breaking, tarpitting, traffic redirection, and challenges.
    """
    
    def __init__(self, config=None):
        """Initialize attack mitigator with configuration."""
        self.config = config or Config()
        
        # Default ban durations (in seconds)
        self.ban_durations = {
            'default': 300,       # Default reduced from 3600 (1 hour) to 300 (5 minutes)
            'repeated': 1800,      # Repeated attacks reduced from 86400 (1 day) to 1800 (30 minutes)
            'severe': 3600,        # Severe attacks reduced from 604800 (1 week) to 3600 (1 hour)
            'temporary': 60        # Temporary ban kept at 60 seconds
        }
        
        # Use JSON storage for banned IPs instead of temporary memory
        # Use storage manager to access data stores
        self.banned_ips = storage_manager.banned_ips
        self.trusted_ips = storage_manager.trusted_ips
        self.behavior_tracking = storage_manager.behavior_tracking
        self.geo_blocks = storage_manager.geo_blocks
        
        # Use the optimized ban manager for faster IP ban operations
        self.ban_manager = ban_manager
        
        # Initialize required components - fix for 'object has no attribute' errors
        self.rate_limiter = RateLimiter(config)
        self.circuit_breaker = CircuitBreaker(config)
        self.tarpitter = Tarpitter(config)
        self.challenge_manager = ChallengeManager(config)
        self.traffic_redirector = TrafficRedirector(config)
        
        # Store start time for uptime calculation
        self.start_time = time.time()
        
        logger.info("Attack mitigation system initialized")
    
    async def start(self) -> None:
        """Start the mitigation system."""
        logger.info("Starting attack mitigation system")
        
        # Schedule periodic cleanup of data
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.cleanup_task.add_done_callback(self._handle_task_done)
        
        # Preload banned IPs into global cache for faster lookups
        self._preload_banned_ips()
    
    def _preload_banned_ips(self) -> None:
        """Load banned IPs into global cache for fast lookup"""
        try:
            # Import global cache from __init__.py
            from ddos_protection import banned_ips_cache, trusted_ips_cache
            
            # Load banned IPs
            banned_ips = self.banned_ips.keys()
            count = 0
            for ip in banned_ips:
                banned_ips_cache[ip] = True
                count += 1
            
            # Load trusted IPs
            trusted_ips = self.trusted_ips.keys()
            trusted_count = 0
            for ip in trusted_ips:
                trusted_ips_cache[ip] = True
                trusted_count += 1
                
            logger.info(f"Preloaded {count} banned IPs and {trusted_count} trusted IPs into memory cache")
        except Exception as e:
            logger.error(f"Failed to preload IPs into cache: {e}")
    
    def _handle_task_done(self, task):
        """Handle task completion callback to prevent pending task destruction errors."""
        try:
            # Get the result to handle any exceptions
            task.result()
        except asyncio.CancelledError:
            # Task was cancelled, this is normal during shutdown
            pass
        except Exception as e:
            logger.error(f"Task ended with error: {e}")
            # Restart critical tasks if they fail
            if task == self.cleanup_task:
                logger.info("Restarting cleanup task after failure")
                self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
                self.cleanup_task.add_done_callback(self._handle_task_done)
    
    async def _periodic_cleanup(self) -> None:
        """Perform periodic cleanup tasks."""
        while True:
            try:
                # Clean up storage components
                for storage in [self.banned_ips, self.trusted_ips, self.behavior_tracking]:
                    if storage:
                        storage.maybe_cleanup()
                
                # Clean up rate limiter
                self.rate_limiter.cleanup_old_records()
                
                # Clean up tarpitter
                self.tarpitter.cleanup_old_records()
                
                # Clean up challenge manager
                if hasattr(self, 'challenge_manager'):
                    self.challenge_manager.cleanup_expired()
                
                # Clean up traffic redirector
                if hasattr(self, 'traffic_redirector'):
                    await self.traffic_redirector.cleanup_expired_redirects()
                
                # Other cleanup tasks...
                
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
                logger.error(traceback.format_exc())
            
            # Wait before next cleanup
            await asyncio.sleep(60)  # Wait one minute before trying again
    
    async def process_request(
        self, 
        ip: str, 
        endpoint: str, 
        user_agent: str = "",
        request_size: int = 0
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Process request and apply appropriate mitigation techniques.
        
        Args:
            ip: Client IP address
            endpoint: Request path
            user_agent: Client user agent
            request_size: Request size in bytes
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: 
                - Boolean indicating if request should be allowed
                - Optional challenge data if required
        """
        # Skip if system is disabled
        if not self.config.enabled:
            return True, None
            
        # Quick check against memory cache first (extremely fast)
        try:
            from ddos_protection import banned_ips_cache, trusted_ips_cache
            
            if ip in banned_ips_cache:
                # Don't even waste time with delay for cached banned IPs
                return False, None
                
            if ip in trusted_ips_cache:
                return True, None
        except ImportError:
            # If import fails, fall back to normal checking
            pass
            
        # Check if in loopback/internal networks for fast allowlist
        is_internal = ip == "127.0.0.1" or ip == "::1" or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")
        if is_internal:
            return True, None
        
        # Check banned IPs first for speed - use database lookup as fallback
        if self._is_banned(ip):
            # Short delay to waste attacker resources
            # Only for IPs not in the cache (first hit)
            try:
                from ddos_protection import banned_ips_cache
                if ip not in banned_ips_cache:
                    banned_ips_cache[ip] = True  # Add to cache for future requests
                    await asyncio.sleep(random.uniform(0.5, 2.0))
            except ImportError:
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            logger.debug(f"Rejecting request from banned IP: {ip}")
            return False, None
            
        # Track request in our system
        # Store request data for further analysis
        if hasattr(self, 'behavior_tracking'):
            current_time = time.time()
            behavior_data = self.behavior_tracking.get(ip, {'requests': [], 'patterns': {}, 'last_update': current_time})
            
            # Update request history with minimal processing
            behavior_data['last_update'] = current_time
            behavior_data['last_path'] = endpoint
            behavior_data['request_count'] = behavior_data.get('request_count', 0) + 1
            
            # Update storage with minimal data
            self.behavior_tracking.set(ip, behavior_data)
            
        # Apply rate limiting
        try:
            is_allowed = await self.rate_limiter.check_rate_limit(ip, endpoint)
            if not is_allowed:
                # If rate limit was exceeded, increment the violation counter for this IP
                if hasattr(self, 'behavior_tracking'):
                    behavior_data = self.behavior_tracking.get(ip, {})
                    violations = behavior_data.get('rate_violations', 0) + 1
                    behavior_data['rate_violations'] = violations
                    self.behavior_tracking.set(ip, behavior_data)
                    
                    # CLOUDFLARE-STYLE CHALLENGE SYSTEM INTEGRATION
                    # Instead of immediately banning, issue a challenge for verification
                    if violations >= 3 and violations < 10:
                        # For repeat offenders between 3-9 violations, issue a browser challenge
                        logger.warning(f"Rate limit exceeded for {ip} on {endpoint} ({violations} violations) - issuing challenge")
                        
                        # Create a challenge for this client
                        if hasattr(self, 'challenge_manager'):
                            challenge_data = self.challenge_manager.create_challenge(ip, user_agent)
                            if challenge_data:
                                # Return false with challenge data
                                return False, {
                                    "challenge": True,
                                    "data": challenge_data,
                                    "type": "browser_verification"
                                }
                    
                    # For extreme cases (≥10 violations), still ban permanently
                    elif violations >= 10:
                        await self.ban_ip_permanent(ip, f"Exceeded rate limits {violations} times")
                        logger.warning(f"Permanently banned {ip} after {violations} rate limit violations")
                    
                    # For first 1-2 violations, just block this request with a warning
                    else:
                        logger.warning(f"Rate limit exceeded for {ip} on {endpoint} ({violations} violations) - temporary block")
                
                return False, None
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
            # Continue processing even if rate limiting fails
        
        # Apply Tarpitting for delay to suspicious IPs
        if self.tarpitter.is_suspicious(ip):
            delay = await self.tarpitter.apply_tarpit(ip)
            if delay > 0:
                logger.debug(f"Applying delay {delay:.2f}s to suspicious IP {ip}")
                await asyncio.sleep(delay)
        
        # Check if IP is in whitelist
        if self._is_trusted(ip):
            return True, None
        
        # Check circuit breaker status for endpoint
        endpoint_status = self.circuit_breaker.check_circuit_status(endpoint)
        # TEMPORARY TEST: Apply to internal IPs as well
        if not endpoint_status: # and not is_internal:
            # If circuit is open, apply tarpitting to non-internal IPs
            await self.tarpitter.apply_tarpit(ip, 2.0)  # Apply severe delay
            
            # For critical endpoints, we might want to challenge or block
            if endpoint in self.config.mitigator.critical_endpoints:
                # Instead of immediate ban, issue a challenge
                if hasattr(self, 'challenge_manager'):
                    challenge_data = self.challenge_manager.create_challenge(ip, user_agent)
                    if challenge_data:
                        logger.warning(f"Circuit breaker triggered for {ip} on critical endpoint {endpoint} - issuing challenge")
                        return False, {
                            "challenge": True,
                            "data": challenge_data,
                            "type": "browser_verification"
                        }
            
            return False, None
        
        # Check for suspicious request size (potential DoS)
        if request_size > 1024 * 1024:  # 1MB
            logger.warning(f"Large request from {ip}: {request_size} bytes")
            self.tarpitter.add_suspicious_ip(ip, level=2)  # Mark as more suspicious
            
            if request_size > 10 * 1024 * 1024:  # 10MB is highly suspicious
                # Ban temporarily for extremely large requests
                await self.ban_ip(ip, f"Extremely large request: {request_size} bytes", 3600)
                return False, None
        
        # Check geo-blocking status if configuration supports it
        has_geo_config = hasattr(self.config, 'geolocation') and self.config.geolocation is not None
        if has_geo_config and hasattr(self.config.geolocation, 'enabled') and self.config.geolocation.enabled and self._is_geo_blocked(ip):
            logger.info(f"Rejecting request from blocked region: {ip}")
            return False, None
        
        # If we reach here, the request is allowed
        return True, None
    
    def _is_banned(self, ip: str) -> bool:
        """
        Check if an IP address is banned.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if IP is banned
        """
        # Use the optimized ban manager for fast lookups (in-memory)
        if self.ban_manager.is_banned(ip):
            return True
        
        # Fall back to database lookup
        ban_info = self.banned_ips.get(ip)
        if ban_info:
            # Check for ban expiration
            if 'expires_at' in ban_info and time.time() > ban_info['expires_at']:
                self.banned_ips.delete(ip)
                return False
            return True
        return False
    
    def _is_trusted(self, ip: str) -> bool:
        """
        Check if an IP address is trusted.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if IP is trusted
        """
        return self.trusted_ips.get(ip) is not None
    
    def _is_geo_blocked(self, ip: str) -> bool:
        """
        Check if an IP address is from a blocked region.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if IP is from a blocked region
        """
        # Skip geo blocking if config not available
        if not hasattr(self.config, 'geolocation') or self.config.geolocation is None:
            return False
        
        # Skip if not enabled
        if not hasattr(self.config.geolocation, 'enabled') or not self.config.geolocation.enabled:
            return False
        
        # Use GeoIP to determine country/region
        # Note: This requires GeoIP integration
        
        # TODO: Implement geo-blocking logic
        return False
    
    async def ban_ip(self, ip: str, reason: str, duration: Optional[int] = None) -> None:
        """
        Ban an IP address.
        
        Args:
            ip: IP address to ban
            reason: Reason for ban
            duration: Ban duration in seconds (optional, None means permanent ban)
        """
        # Use the more efficient ban manager
        self.ban_manager.ban_ip(ip, reason, duration)
        
        # Log appropriate message based on ban type
        if duration is not None:
            logger.info(f"Temporary ban for IP {ip} for {duration} seconds: {reason}")
        else:
            logger.warning(f"PERMANENT ban for IP {ip}: {reason}")
            
        # Additional firewall blocking for permanent bans (if server allows it)
        if duration is None:  # Permanent ban
            try:
                # Apply system-level firewall block in a separate task
                # This will happen asynchronously to not block the request handling
                asyncio.create_task(self._apply_system_firewall_block(ip))
            except Exception as e:
                logger.error(f"Failed to create firewall block task: {e}")
    
    async def ban_ip_permanent(self, ip: str, reason: str) -> None:
        """
        Permanently ban an IP address with immediate system-level blocking.
        This is an optimized version for high-traffic environments.
        
        Args:
            ip: IP address to ban
            reason: Reason for ban
        """
        # Use the more efficient ban manager for immediate ban
        self.ban_manager.ban_ip(ip, reason, None)
        logger.warning(f"PERMANENT IMMEDIATE ban for IP {ip}: {reason}")
        
        # System-level firewall block in a separate task
        try:
            asyncio.create_task(self._apply_system_firewall_block(ip))
        except Exception as e:
            logger.error(f"Failed to create firewall block task: {e}")
    
    async def _apply_system_firewall_block(self, ip: str) -> bool:
        """
        Apply a system firewall block for an IP address.
        
        Args:
            ip: IP address to block
            
        Returns:
            bool: True if block was successful
        """
        try:
            # تجنب تكرار حظر نفس العنوان
            if hasattr(self, '_blocked_ips_set') and ip in self._blocked_ips_set:
                # تم حظر هذا العنوان مسبقًا، قم بتخطي العملية دون تسجيل
                return True
                
            # إنشاء مجموعة للعناوين المحظورة إذا لم تكن موجودة
            if not hasattr(self, '_blocked_ips_set'):
                self._blocked_ips_set = set()
                
            # إضافة العنوان إلى مجموعة العناوين المحظورة
            self._blocked_ips_set.add(ip)
            
            # تحديد نوع نظام التشغيل
            import platform
            self.system_os = platform.system().lower()
        
            if self.system_os == 'windows':
                # استخدام قواعد جدار حماية Windows متقدمة (محسنة)
                rule_name = f"DDoS-Block-{ip.replace('.', '-')}"
                
                # إنشاء قاعدة كاملة الحظر بأولوية عالية
                cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="{rule_name}"',
                    'dir=in',
                    'action=block',
                    f'remoteip={ip}',
                    'enable=yes',
                    'profile=any',
                    'description="Automatically blocked by DDoS Protection System"',
                    'localport=any',
                    'protocol=any',
                    'edge=yes',  # تطبيق على حافة الشبكة
                    'priority=1'  # أعلى أولوية
                ]
                
                # تنفيذ القاعدة الأولى
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # إضافة قاعدة للاتجاه الآخر للتأكد من عدم الرد نهائيًا
                out_cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="{rule_name}-out"',
                    'dir=out',
                    'action=block',
                    f'remoteip={ip}',
                    'enable=yes',
                    'profile=any',
                    'description="Automatically blocked by DDoS Protection System"',
                    'remoteport=any',
                    'protocol=any',
                    'priority=1'
                ]
                
                # تنفيذ القاعدة الثانية
                out_process = await asyncio.create_subprocess_exec(
                    *out_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                out_stdout, out_stderr = await out_process.communicate()
                
                # إضافة قاعدة إضافية للتأكد من عدم استقبال طلبات HTTP/HTTPS
                web_cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="{rule_name}-web"',
                    'dir=in',
                    'action=block',
                    f'remoteip={ip}',
                    'enable=yes',
                    'profile=any',
                    'description="Web ports block by DDoS Protection System"',
                    'localport=80,443,8080,8443',
                    'protocol=TCP',
                    'priority=1'
                ]
                
                # تنفيذ القاعدة الثالثة
                web_process = await asyncio.create_subprocess_exec(
                    *web_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                web_stdout, web_stderr = await web_process.communicate()
                
                # تسجيل نجاح العملية
                if process.returncode == 0 or out_process.returncode == 0 or web_process.returncode == 0:
                    logger.info(f"Applied network-level Windows firewall block for IP {ip}")
                    return True
                else:
                    logger.error(f"Failed to apply Windows firewall block for {ip}: {stderr.decode() or out_stderr.decode() or web_stderr.decode()}")
                    return False
                
            elif self.system_os == 'linux':
                # تنفيذ استراتيجية متعددة المستويات لحظر الطلبات تمامًا
                success = False
                
                # 1. حظر عبر iptables (أساسي)
                iptables_cmd = ['iptables', '-I', 'INPUT', '1', '-s', ip, '-j', 'DROP']
                
                try:
                    in_process = await asyncio.create_subprocess_exec(
                        *iptables_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    in_stdout, in_stderr = await in_process.communicate()
                    
                    if in_process.returncode == 0:
                        success = True
                        logger.info(f"Applied iptables input block for IP {ip}")
                except Exception as e:
                    logger.error(f"Error applying iptables input block: {e}")
                
                # 2. حظر منفذي HTTP/HTTPS بشكل خاص
                web_cmd = ['iptables', '-I', 'INPUT', '1', '-s', ip, '-p', 'tcp', '--match', 'multiport', '--dports', '80,443,8080,8443', '-j', 'DROP']
                
                try:
                    web_process = await asyncio.create_subprocess_exec(
                        *web_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    web_stdout, web_stderr = await web_process.communicate()
                    
                    if web_process.returncode == 0:
                        success = True
                        logger.info(f"Applied iptables web ports block for IP {ip}")
                except Exception as e:
                    logger.error(f"Error applying iptables web ports block: {e}")
                
                # 3. تطبيق توجيه فارغ (null route) - الأكثر فعالية لتجاهل الطلبات تمامًا
                null_cmd = ['ip', 'route', 'add', 'blackhole', f'{ip}/32']
                
                try:
                    null_process = await asyncio.create_subprocess_exec(
                        *null_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    null_stdout, null_stderr = await null_process.communicate()
                    
                    if null_process.returncode == 0:
                        success = True
                        logger.info(f"Applied null route for IP {ip} - traffic will be dropped at network level")
                except Exception as e:
                    logger.debug(f"Error applying null route (requires root): {e}")
                
                # 4. إزالة الاتصالات الحالية مع هذا الـ IP
                conntrack_cmd = ['conntrack', '-D', '-s', ip]
                
                try:
                    conn_process = await asyncio.create_subprocess_exec(
                        *conntrack_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    conn_stdout, conn_stderr = await conn_process.communicate()
                    
                    if conn_process.returncode == 0:
                        logger.info(f"Cleared existing connections for IP {ip}")
                except Exception as e:
                    logger.debug(f"Error clearing connections (requires conntrack): {e}")
                
                return success
                
            elif self.system_os == 'macos':
                # تحسين قواعد PF لنظام ماك
                success = False
                
                # 1. إضافة العنوان إلى جدول العناوين المحظورة
                try:
                    # إنشاء القاعدة إذا لم تكن موجودة
                    with open('/tmp/ddos_pf.conf', 'w') as f:
                        f.write(f"table <ddos_blacklist> persist\n")
                        f.write(f"block drop in quick from <ddos_blacklist> to any\n")
                        f.write(f"block drop out quick from any to <ddos_blacklist>\n")
                    
                    # تطبيق القواعد
                    load_cmd = ['pfctl', '-f', '/tmp/ddos_pf.conf']
                    load_process = await asyncio.create_subprocess_exec(
                        *load_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    load_stdout, load_stderr = await load_process.communicate()
                except Exception as e:
                    logger.debug(f"Error setting up PF rules: {e}")
                
                # إضافة العنوان للقائمة
                add_cmd = ['pfctl', '-t', 'ddos_blacklist', '-T', 'add', ip]
                try:
                    add_process = await asyncio.create_subprocess_exec(
                        *add_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    add_stdout, add_stderr = await add_process.communicate()
                    
                    if add_process.returncode == 0:
                        success = True
                        logger.info(f"Added IP {ip} to PF blacklist table")
                except Exception as e:
                    logger.error(f"Error adding IP to PF table: {e}")
                
                # تأكيد تطبيق القواعد
                flush_cmd = ['pfctl', '-t', 'ddos_blacklist', '-T', 'flush']
                try:
                    flush_process = await asyncio.create_subprocess_exec(
                        *flush_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    flush_stdout, flush_stderr = await flush_process.communicate()
                except Exception as e:
                    logger.debug(f"Error flushing PF rules: {e}")
                
                return success
            
            else:
                logger.warning(f"Firewall blocking not implemented for OS: {self.system_os}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying firewall block for IP {ip}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def unban_ip(self, ip: str) -> bool:
        """
        Unban an IP address.
        
        Args:
            ip: IP address to unban
            
        Returns:
            bool: True if unban was successful
        """
        # Use the more efficient ban manager
        result = self.ban_manager.unban_ip(ip)
        if result:
            logger.info(f"Unbanned IP address: {ip}")
            
            # Try to remove system firewall rules
            try:
                asyncio.create_task(self._remove_system_firewall_block(ip))
            except Exception as e:
                logger.error(f"Failed to create firewall unblock task: {e}")
                
        return result
    
    async def _remove_system_firewall_block(self, ip: str) -> None:
        """Remove system-level firewall block in a separate task"""
        try:
            import platform
            import subprocess
            
            os_name = platform.system().lower()
            
            if os_name == 'linux':
                cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    logger.info(f"Removed permanent firewall rule for {ip}")
                else:
                    logger.error(f"Failed to remove Linux firewall rule: {result.stderr}")
            elif os_name == 'windows':
                cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", 
                      f'name="DDoS_Block_{ip}"']
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    logger.info(f"Removed permanent Windows firewall rule for {ip}")
                else:
                    logger.error(f"Failed to remove Windows firewall rule: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to remove system firewall rule: {e}")
    
    async def add_trusted_ip(self, ip: str, note: str = "") -> None:
        """
        Add an IP address to trusted list.
        
        Args:
            ip: IP address to add
            note: Optional note
        """
        trust_data = {
            'note': note,
            'added_at': time.time()
        }
        
        # Store trusted IP in persistent storage
        self.trusted_ips.set(ip, trust_data)
        logger.info(f"Added trusted IP: {ip}")
    
    async def remove_trusted_ip(self, ip: str) -> bool:
        """
        Remove an IP address from trusted list.
        
        Args:
            ip: IP address to remove
            
        Returns:
            bool: True if removal was successful
        """
        if self._is_trusted(ip):
            # Remove IP from trusted list
            self.trusted_ips.delete(ip)
            logger.info(f"Removed trusted IP: {ip}")
            return True
        
        return False

    def get_mitigation_stats(self) -> Dict[str, Any]:
        """
        Get current mitigation statistics.
        
        Returns:
            Dict[str, Any]: Dictionary with mitigation statistics
        """
        # Collect statistics from various components
        banned_count = len(self.banned_ips.keys()) if hasattr(self, 'banned_ips') else 0
        trusted_count = len(self.trusted_ips.keys()) if hasattr(self, 'trusted_ips') else 0
        behavior_count = len(self.behavior_tracking.keys()) if hasattr(self, 'behavior_tracking') else 0
        
        # Basic statistics
        stats = {
            "banned_ips_count": banned_count,
            "trusted_ips_count": trusted_count,
            "tracked_behaviors_count": behavior_count,
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
        }
        
        return stats
        
    def get_banned_ips(self) -> List[str]:
        """
        Get a list of all currently banned IPs.
        
        Returns:
            List[str]: List of banned IP addresses
        """
        return self.banned_ips.keys()
        
    def check_storage_files(self) -> Dict[str, bool]:
        """
        Check if storage files exist and are accessible.
        
        Returns:
            Dict[str, bool]: Dictionary with status of each storage file
        """
        result = {}
        
        # Check banned IPs file
        try:
            banned_ips = self.banned_ips.keys()
            result["banned_ips"] = True
        except Exception as e:
            logger.error(f"Error accessing banned IPs storage: {e}")
            result["banned_ips"] = False
            
        # Check trusted IPs file
        try:
            trusted_ips = self.trusted_ips.keys()
            result["trusted_ips"] = True
        except Exception as e:
            logger.error(f"Error accessing trusted IPs storage: {e}")
            result["trusted_ips"] = False
            
        # Check behavior tracking file
        try:
            behavior_tracking = self.behavior_tracking.keys()
            result["behavior_tracking"] = True
        except Exception as e:
            logger.error(f"Error accessing behavior tracking storage: {e}")
            result["behavior_tracking"] = False
            
        return result

class DDoSMitigator:
    """
    Implements mitigation strategies for DDoS attacks including
    system-level firewall blocks and rate limiting.
    """
    
    def __init__(self):
        """Initialize the DDoS mitigator"""
        # Track mitigation actions
        self.recent_mitigations = []
        self.blocked_ips = set()
        
        # Detect OS for firewall actions
        self.system_os = self._detect_os()
        logger.info(f"Detected operating system: {self.system_os}")
        
        # Check firewall capabilities
        self.has_firewall = self._check_firewall()
        if not self.has_firewall:
            logger.warning("No firewall capability detected. Will use application-level blocking only.")
        
        logger.info("DDoS mitigator initialized")
    
    def _detect_os(self) -> str:
        """Detect the operating system"""
        if sys.platform.startswith('win'):
            return 'windows'
        elif sys.platform.startswith('linux'):
            return 'linux'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        else:
            return 'unknown'
    
    def _check_firewall(self) -> bool:
        """Check if firewall capability is available"""
        try:
            if self.system_os == 'windows':
                # Check if netsh is available
                result = subprocess.run(['netsh', 'advfirewall', 'show', 'currentprofile'], 
                                     capture_output=True, text=True, check=False)
                return result.returncode == 0
            elif self.system_os == 'linux':
                # Check if iptables or nftables is available
                iptables = subprocess.run(['which', 'iptables'], 
                                      capture_output=True, text=True, check=False)
                nftables = subprocess.run(['which', 'nft'], 
                                      capture_output=True, text=True, check=False)
                return iptables.returncode == 0 or nftables.returncode == 0
            elif self.system_os == 'macos':
                # Check if pfctl is available
                result = subprocess.run(['which', 'pfctl'], 
                                     capture_output=True, text=True, check=False)
                return result.returncode == 0
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking firewall capability: {e}")
            return False
    
    async def mitigate(self, ip: str, attack_type: str, severity: str = 'medium') -> bool:
        """
        Apply mitigation strategies based on attack type and severity.
        
        Args:
            ip: IP address to mitigate
            attack_type: Type of attack detected
            severity: Attack severity (low, medium, high)
            
        Returns:
            bool: True if mitigation was successful
        """
        # Track mitigation action
        mitigation = {
            'ip': ip,
            'type': attack_type,
            'severity': severity,
            'timestamp': time.time(),
            'success': False
        }
        
        try:
            # Apply system firewall block for medium and high severity
            if severity in ('medium', 'high') and self.has_firewall:
                block_result = await self._apply_system_firewall_block(ip)
                mitigation['firewall_block'] = block_result
                
                if block_result:
                    logger.info(f"Applied system firewall block for IP {ip}")
                    self.blocked_ips.add(ip)
                    mitigation['success'] = True
                else:
                    logger.warning(f"Failed to apply system firewall block for IP {ip}")
            
            # Ban IP in storage
            ban_result = await self._ban_ip_in_storage(ip, attack_type, severity)
            mitigation['storage_ban'] = ban_result
            
            if ban_result:
                logger.info(f"Banned IP {ip} in storage")
                if not mitigation['success']:
                    mitigation['success'] = True
            
            # Add to recent mitigations list (limit to 100 entries)
            self.recent_mitigations.append(mitigation)
            if len(self.recent_mitigations) > 100:
                self.recent_mitigations.pop(0)
                
            return mitigation['success']
        
        except Exception as e:
            logger.error(f"Error applying mitigation for IP {ip}: {e}")
            return False
    
    async def _apply_system_firewall_block(self, ip: str) -> bool:
        """
        Apply a system firewall block for an IP address.
        
        Args:
            ip: IP address to block
            
        Returns:
            bool: True if block was successful
        """
        try:
            # تجنب تكرار حظر نفس العنوان
            if hasattr(self, '_blocked_ips_set') and ip in self._blocked_ips_set:
                # تم حظر هذا العنوان مسبقًا، قم بتخطي العملية دون تسجيل
                return True
                
            # إنشاء مجموعة للعناوين المحظورة إذا لم تكن موجودة
            if not hasattr(self, '_blocked_ips_set'):
                self._blocked_ips_set = set()
                
            # إضافة العنوان إلى مجموعة العناوين المحظورة
            self._blocked_ips_set.add(ip)
        
            if self.system_os == 'windows':
                # Use Windows Firewall to block the IP with higher priority
                rule_name = f"DDoS-Block-{ip}"
                
                # إنشاء قاعدة جديدة مع أولوية عالية لضمان تطبيقها أولاً
                cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="{rule_name}"',
                    'dir=in',
                    'action=block',
                    f'remoteip={ip}',
                    'enable=yes',
                    'profile=any',
                    'description="Automatically blocked by DDoS Protection System"',
                    'localport=any',
                    'protocol=any',
                    'edge=yes',  # تطبيق على حافة الشبكة
                    'priority=1'  # أعلى أولوية
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # إضافة قاعدة للاتجاه الآخر للتأكد من الحظر الكامل
                out_cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="{rule_name}-out"',
                    'dir=out',
                    'action=block',
                    f'remoteip={ip}',
                    'enable=yes',
                    'profile=any',
                    'description="Automatically blocked by DDoS Protection System"',
                    'remoteport=any',
                    'protocol=any',
                    'edge=yes',
                    'priority=1'
                ]
                
                out_process = await asyncio.create_subprocess_exec(
                    *out_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                out_stdout, out_stderr = await out_process.communicate()
                
                return process.returncode == 0 and out_process.returncode == 0
                
            elif self.system_os == 'linux':
                # تحسين قواعد iptables
                # 1. حظر كل الاتصالات الواردة
                in_cmd = ['iptables', '-I', 'INPUT', '1', '-s', ip, '-j', 'DROP']
                
                # 2. حظر الاتصالات الصادرة للتأكد من عدم الرد
                out_cmd = ['iptables', '-I', 'OUTPUT', '1', '-d', ip, '-j', 'DROP']
                
                # 3. تطبيق تقنية null route للتخلص من الطلبات على مستوى الشبكة
                # هذا لا يعالج الطلبات أبداً على مستوى التطبيق
                null_cmd = ['ip', 'route', 'add', 'blackhole', ip + '/32']
                
                # تنفيذ الأوامر
                in_process = await asyncio.create_subprocess_exec(
                    *in_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                in_stdout, in_stderr = await in_process.communicate()
                
                out_process = await asyncio.create_subprocess_exec(
                    *out_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                out_stdout, out_stderr = await out_process.communicate()
                
                # تطبيق null route إذا كان متاحاً
                try:
                    null_process = await asyncio.create_subprocess_exec(
                        *null_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    null_stdout, null_stderr = await null_process.communicate()
                    
                    # تسجيل نجاح null route
                    if null_process.returncode == 0:
                        logger.info(f"Applied null route for IP {ip} - requests will be dropped at network level")
                except Exception as e:
                    logger.debug(f"Could not apply null route (requires elevated privileges): {e}")
                
                # مسح جميع حالات الاتصال الحالية لهذا العنوان
                try:
                    # استخدام conntrack لمسح حالات الاتصال الحالية
                    ct_cmd = ['conntrack', '-D', '-s', ip]
                    ct_process = await asyncio.create_subprocess_exec(
                        *ct_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    ct_stdout, ct_stderr = await ct_process.communicate()
                except Exception as e:
                    logger.debug(f"Could not clear connection tracking (requires conntrack tool): {e}")
                
                return in_process.returncode == 0
                
            elif self.system_os == 'macos':
                # تحسين قواعد PF لنظام ماك
                # إضافة العنوان إلى جدول منع العناوين
                add_cmd = ['pfctl', '-t', 'ddos-blacklist', '-T', 'add', ip]
                
                # تأكيد تطبيق القاعدة فوراً
                flush_cmd = ['pfctl', '-t', 'ddos-blacklist', '-T', 'flush']
                
                add_process = await asyncio.create_subprocess_exec(
                    *add_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                add_stdout, add_stderr = await add_process.communicate()
                
                flush_process = await asyncio.create_subprocess_exec(
                    *flush_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                flush_stdout, flush_stderr = await flush_process.communicate()
                
                return add_process.returncode == 0
            
            else:
                logger.warning(f"Firewall blocking not implemented for OS: {self.system_os}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying firewall block for IP {ip}: {e}")
            return False
    
    async def _ban_ip_in_storage(self, ip: str, reason: str, severity: str) -> bool:
        """Ban an IP in storage with appropriate duration based on severity"""
        try:
            from ddos_protection.storage import ban_manager
            
            # Set ban duration based on severity
            durations = {
                'low': 3600,         # 1 hour
                'medium': 86400,     # 1 day
                'high': 604800       # 1 week
            }
            duration = durations.get(severity, 3600)
            
            # Ban the IP
            ban_manager.ban_ip(ip, reason, duration)
            
            # Update global cache
            try:
                from ddos_protection import banned_ips_cache
                if hasattr(banned_ips_cache, 'add'):  # If it's a set
                    banned_ips_cache.add(ip)
                else:  # If it's a dict
                    banned_ips_cache[ip] = True
            except ImportError:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error banning IP {ip} in storage: {e}")
            return False
    
    async def remove_block(self, ip: str) -> bool:
        """
        Remove a block for an IP address from both firewall and storage.
        
        Args:
            ip: IP address to unblock
            
        Returns:
            bool: True if unblock was successful
        """
        try:
            # Remove firewall block
            firewall_result = False
            if self.has_firewall:
                firewall_result = await self._remove_firewall_block(ip)
                
                if firewall_result:
                    logger.info(f"Removed system firewall block for IP {ip}")
                    if ip in self.blocked_ips:
                        self.blocked_ips.remove(ip)
                else:
                    logger.warning(f"Failed to remove system firewall block for IP {ip}")
            
            # Remove from storage
            from ddos_protection.storage import ban_manager
            storage_result = ban_manager.unban_ip(ip)
            
            if storage_result:
                logger.info(f"Unbanned IP {ip} in storage")
                
                # Update global cache
                try:
                    from ddos_protection import banned_ips_cache
                    if hasattr(banned_ips_cache, 'remove'):  # If it's a set
                        banned_ips_cache.remove(ip)
                    elif ip in banned_ips_cache:  # If it's a dict
                        del banned_ips_cache[ip]
                except (ImportError, KeyError):
                    pass
            
            return firewall_result or storage_result
            
        except Exception as e:
            logger.error(f"Error removing block for IP {ip}: {e}")
            return False
    
    async def _remove_firewall_block(self, ip: str) -> bool:
        """Remove a firewall block for an IP address"""
        try:
            if self.system_os == 'windows':
                # Remove Windows Firewall rule
                rule_name = f"DDoS-Block-{ip}"
                
                cmd = [
                    'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                    f'name="{rule_name}"'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                return process.returncode == 0
                
            elif self.system_os == 'linux':
                # Remove iptables rule
                iptables_cmd = [
                    'iptables', '-D', 'INPUT', '-s', ip, '-j', 'DROP'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *iptables_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                return process.returncode == 0
                
            elif self.system_os == 'macos':
                # Remove from pfctl
                cmd = [
                    'pfctl', '-t', 'ddos-blacklist', '-T', 'delete', ip
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                return process.returncode == 0
                
            else:
                logger.warning(f"Firewall unblocking not implemented for OS: {self.system_os}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing firewall block for IP {ip}: {e}")
            return False
    
    def get_mitigation_stats(self) -> Dict:
        """Get statistics about mitigation actions"""
        return {
            'total_mitigations': len(self.recent_mitigations),
            'active_blocks': len(self.blocked_ips),
            'success_rate': sum(1 for m in self.recent_mitigations if m['success']) / len(self.recent_mitigations) if self.recent_mitigations else 0,
            'recent_blocks': [m['ip'] for m in self.recent_mitigations[-10:]] if self.recent_mitigations else []
        } 