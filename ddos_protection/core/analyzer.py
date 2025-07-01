#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Traffic Analyzer
----------------------------------------
وحدة تحليل حركة المرور للكشف عن أنماط الهجوم
"""

import logging
import time
import re
import asyncio
import threading
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any, Tuple

# Setup logger
logger = logging.getLogger('ddos_protection.analyzer')

class TrafficAnalyzer:
    """
    Analyzes traffic patterns to detect DDoS attacks based on behavioral analysis.
    Identifies suspicious patterns that may indicate a DDoS attack in progress.
    """
    
    def __init__(self):
        """Initialize the traffic analyzer"""
        # IP tracking
        self.ip_requests = defaultdict(list)  # Tracks request times by IP
        self.ip_paths = defaultdict(set)      # Tracks unique paths by IP
        self.ip_agents = defaultdict(set)     # Tracks unique user agents by IP
        
        # Enhanced tracking for better detection
        self.ip_legitimate_score = defaultdict(float)  # Score for legitimate behavior
        self.ip_request_patterns = defaultdict(list)   # Pattern of requests to detect normal browsing
        self.ip_static_assets = defaultdict(int)       # Count of static asset requests per IP
        self.ip_api_requests = defaultdict(int)        # Count of API requests per IP
        
        # Global tracking
        self.recent_requests = deque(maxlen=1000)  # Recent requests for global analysis
        self.path_counts = defaultdict(int)       # Count of requests by path
        
        # Attack pattern recognition
        self.attack_patterns = {
            'rapid_fire': self._check_rapid_fire,
            'path_scanning': self._check_path_scanning,
            'agent_switching': self._check_agent_switching,
            'resource_abuse': self._check_resource_abuse
        }
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Analysis thresholds
        self.thresholds = {
            'requests_per_minute': 250,       # Increased from 120 to 250
            'min_interval_ms': 25,            # Decreased from 50 to 25
            'max_paths_per_minute': 80,       # Increased from 40 to 80
            'max_agents_per_ip': 8,           # Keeping same value
            'large_request_size': 1024 * 1000  # Increased from 500KB to 1000KB
        }
        
        # Static assets regex pattern
        self.static_asset_pattern = re.compile(r'\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|pdf)$', re.IGNORECASE)
        
        # API paths pattern
        self.api_path_pattern = re.compile(r'^/api/', re.IGNORECASE)
        
        # Common browser resources pattern - avoid flagging standard browser loading patterns as attacks
        self.browser_resources_pattern = re.compile(r'/(favicon|robots|manifest|sw|serviceworker|favicon-sw|assets)', re.IGNORECASE)
        
        logger.info("Traffic analyzer initialized with enhanced detection and reduced sensitivity")
    
    async def analyze_request(self, ip: str, path: str, user_agent: Optional[str] = None, 
                         request_size: int = 0) -> bool:
        """
        Analyze a request to determine if it's part of an attack pattern.
        
        Args:
            ip: Client IP address
            path: Request path
            user_agent: User agent string
            request_size: Size of the request in bytes
            
        Returns:
            bool: True if request appears to be part of an attack, False otherwise
        """
        with self.lock:
            current_time = time.time()
            
            # Check if this is a static asset request
            is_static_asset = bool(self.static_asset_pattern.search(path))
            is_api_request = bool(self.api_path_pattern.search(path))
            
            # Record request data
            self.ip_requests[ip].append(current_time)
            self.ip_paths[ip].add(path)
            if user_agent:
                self.ip_agents[ip].add(user_agent)
            
            # Track asset/API requests
            if is_static_asset:
                self.ip_static_assets[ip] += 1
            if is_api_request:
                self.ip_api_requests[ip] += 1
            
            # Record request pattern (simplified path)
            path_type = 'static' if is_static_asset else ('api' if is_api_request else 'page')
            self.ip_request_patterns[ip].append((path_type, current_time))
            
            # Keep only recent data
            self._clean_old_data(ip, current_time)
            
            # Add to global tracking
            self.recent_requests.append({
                'ip': ip,
                'path': path,
                'user_agent': user_agent,
                'time': current_time,
                'size': request_size,
                'is_static': is_static_asset,
                'is_api': is_api_request
            })
            self.path_counts[path] += 1
            
            # Calculate legitimate score for this IP
            self._update_legitimate_score(ip)
            
            # Skip analysis for highly trusted IPs (high legitimate score)
            if self.ip_legitimate_score[ip] > 0.8:
                return False
                
            # Skip analysis for static assets if we have seen other pages from this IP
            if is_static_asset and len(self.ip_paths[ip]) > 1 and self.ip_legitimate_score[ip] > 0.5:
                return False
            
            # Check for attack patterns
            detected_attacks = []
            total_confidence = 0
            
            for pattern_name, pattern_func in self.attack_patterns.items():
                is_attack, confidence = pattern_func(ip, path, user_agent, request_size, current_time)
                if is_attack:
                    detected_attacks.append(pattern_name)
                    total_confidence += confidence
            
            # Adjust confidence based on legitimate score
            if detected_attacks:
                # Reduce confidence for IPs with legitimate behavior
                adjusted_confidence = max(0, total_confidence - self.ip_legitimate_score[ip])
                
                # If multiple attack patterns detected, it's more likely an attack
                if len(detected_attacks) > 1:
                    adjusted_confidence = min(1.0, adjusted_confidence * 1.5)
                
                if adjusted_confidence > 0.7:  # 70% confidence threshold
                    logger.warning(f"Attack patterns detected: {', '.join(detected_attacks)} from IP {ip} (confidence: {adjusted_confidence:.2f})")
                    # Penalize legitimate score
                    self.ip_legitimate_score[ip] = max(0, self.ip_legitimate_score[ip] - 0.3)
                    return True
                
            return False
    
    def _clean_old_data(self, ip: str, current_time: float):
        """Remove data older than 1 minute"""
        # Keep only requests from the last minute
        cutoff_time = current_time - 60
        while self.ip_requests[ip] and self.ip_requests[ip][0] < cutoff_time:
            self.ip_requests[ip].pop(0)
        
        # Remove IP tracking if no recent requests
        if not self.ip_requests[ip]:
            del self.ip_requests[ip]
            if ip in self.ip_paths:
                del self.ip_paths[ip]
            if ip in self.ip_agents:
                del self.ip_agents[ip]
    
    def _check_rapid_fire(self, ip: str, path: str, user_agent: Optional[str], 
                        request_size: int, current_time: float) -> Tuple[bool, float]:
        """
        Check for rapid-fire requests (many requests in a short period).
        
        Returns:
            Tuple[bool, float]: (is_attack, confidence)
        """
        requests = self.ip_requests[ip]
        
        # Need multiple requests to analyze
        if len(requests) < 5:
            return False, 0.0
        
        # Calculate request rate (requests per minute)
        first_request = requests[0]
        duration = current_time - first_request
        
        # Avoid division by zero
        if duration < 0.1:
            duration = 0.1
            
        requests_per_minute = (len(requests) / duration) * 60
        
        # Calculate average interval between requests
        intervals = [requests[i] - requests[i-1] for i in range(1, len(requests))]
        avg_interval = sum(intervals) / len(intervals) if intervals else 1.0
        avg_interval_ms = avg_interval * 1000
        
        # Confidence calculation based on multiple factors
        confidence = 0.0
        
        # Factor 1: Request rate
        if requests_per_minute > self.thresholds['requests_per_minute']:
            rate_factor = min(requests_per_minute / self.thresholds['requests_per_minute'], 10) / 10
            confidence += rate_factor * 0.5  # 50% weight for request rate
            
        # Factor 2: Request interval
        if avg_interval_ms < self.thresholds['min_interval_ms']:
            interval_factor = min(self.thresholds['min_interval_ms'] / (avg_interval_ms + 1), 10) / 10
            confidence += interval_factor * 0.5  # 50% weight for interval
        
        # Determine if this is an attack based on confidence
        is_attack = confidence > 0.7  # 70% confidence threshold
        
        return is_attack, confidence
    
    def _check_path_scanning(self, ip: str, path: str, user_agent: Optional[str], 
                           request_size: int, current_time: float) -> Tuple[bool, float]:
        """
        Check for path scanning (accessing many different paths).
        
        Returns:
            Tuple[bool, float]: (is_attack, confidence)
        """
        unique_paths = len(self.ip_paths[ip])
        request_count = len(self.ip_requests[ip])
        
        # Need multiple requests to analyze
        if request_count < 10:  # Increased minimum request threshold from 5 to 10
            return False, 0.0
        
        # Filter out browser resources (favicon, etc.) from the count
        browser_resource_paths = sum(1 for p in self.ip_paths[ip] if self.browser_resources_pattern.search(p))
        static_asset_paths = sum(1 for p in self.ip_paths[ip] if self.static_asset_pattern.search(p))
        
        # Adjusted unique paths count - give less weight to common browser resources
        adjusted_unique_paths = unique_paths - (browser_resource_paths * 0.8) - (static_asset_paths * 0.6)
        adjusted_unique_paths = max(adjusted_unique_paths, 1)  # Ensure it's at least 1
        
        # Calculate path diversity - adjusted to consider resource types
        path_diversity = adjusted_unique_paths / request_count
        
        # Calculate paths per minute
        first_request = self.ip_requests[ip][0]
        duration = current_time - first_request
        
        # Avoid division by zero
        if duration < 0.1:
            duration = 0.1
            
        paths_per_minute = (adjusted_unique_paths / duration) * 60
        
        # Confidence calculation
        confidence = 0.0
        
        # Factor 1: Path diversity
        if path_diversity > 0.8:  # Increased from 0.7 to 0.8
            confidence += path_diversity * 0.3  # 30% weight
            
        # Factor 2: Paths per minute
        if paths_per_minute > self.thresholds['max_paths_per_minute']:
            rate_factor = min(paths_per_minute / self.thresholds['max_paths_per_minute'], 10) / 10
            confidence += rate_factor * 0.5  # Reduced from 0.7 to 0.5
        
        # Factor 3: Suspicious path patterns (like directory scanning)
        suspicious_patterns = [
            r'/\.env',
            r'/\.git',
            r'/wp-admin',
            r'/admin',
            r'/config',
            r'/backup',
            r'/dbadmin',
            r'/phpMyAdmin',
            r'/phpmyadmin',
            r'/administrator'
        ]
        
        suspicious_count = sum(1 for p in self.ip_paths[ip] if any(re.search(pattern, p) for pattern in suspicious_patterns))
        
        # If suspicious paths are detected, increase confidence
        if suspicious_count > 0:
            confidence += min(suspicious_count / 3, 1.0) * 0.6  # Up to 60% boost for suspicious paths
        
        # Determine if this is an attack based on confidence - increased threshold
        is_attack = confidence > 0.85  # Increased from 0.7 to 0.85 for more certainty
        
        return is_attack, confidence
    
    def _check_agent_switching(self, ip: str, path: str, user_agent: Optional[str], 
                             request_size: int, current_time: float) -> Tuple[bool, float]:
        """
        Check for user agent switching (using many different user agents).
        
        Returns:
            Tuple[bool, float]: (is_attack, confidence)
        """
        if not user_agent:
            return False, 0.0
            
        unique_agents = len(self.ip_agents[ip])
        request_count = len(self.ip_requests[ip])
        
        # Need multiple requests to analyze
        if request_count < 5:
            return False, 0.0
        
        # Calculate agent switching confidence
        if unique_agents > self.thresholds['max_agents_per_ip']:
            # Calculate confidence based on how many agents above threshold
            confidence = min((unique_agents / self.thresholds['max_agents_per_ip']) - 1, 1.0)
            
            # Check for any suspicious user agents
            suspicious_patterns = [
                r'got',
                r'bot',
                r'crawl',
                r'spider',
                r'scan',
                r'python',
                r'curl',
                r'wget',
                r'go-http',
                r'(?:^|[^a-z])php'
            ]
            
            suspicious_count = 0
            for agent in self.ip_agents[ip]:
                for pattern in suspicious_patterns:
                    if re.search(pattern, agent.lower()):
                        suspicious_count += 1
                        break
            
            # If more than half are suspicious, increase confidence
            if suspicious_count / unique_agents > 0.5:
                confidence += 0.3  # Boost confidence by 30%
                confidence = min(confidence, 1.0)  # Cap at 100%
            
            return confidence > 0.7, confidence
        
        return False, 0.0
    
    def _check_resource_abuse(self, ip: str, path: str, user_agent: Optional[str], 
                          request_size: int, current_time: float) -> Tuple[bool, float]:
        """
        Check for resource-intensive requests (large requests or expensive endpoints).
        
        Returns:
            Tuple[bool, float]: (is_attack, confidence)
        """
        # Check for large request
        is_large_request = request_size > self.thresholds['large_request_size']
        
        # Check for expensive endpoints
        expensive_endpoints = [
            r'/api/search',
            r'/api/report',
            r'/api/export',
            r'/download',
            r'/upload'
        ]
        
        is_expensive_endpoint = any(re.search(pattern, path) for pattern in expensive_endpoints)
        
        # Count total requests to this path
        path_request_count = self.path_counts[path]
        
        # Calculate confidence
        confidence = 0.0
        
        # Factor 1: Request size
        if is_large_request:
            size_factor = min(request_size / self.thresholds['large_request_size'], 10) / 10
            confidence += size_factor * 0.4  # 40% weight
            
        # Factor 2: Expensive endpoint with high frequency
        if is_expensive_endpoint:
            request_count = len(self.ip_requests[ip])
            if request_count > 10:  # Need at least 10 requests to consider
                expensive_count = sum(1 for req in self.recent_requests if req['ip'] == ip and any(re.search(pattern, req['path']) for pattern in expensive_endpoints))
                expensive_ratio = expensive_count / request_count
                
                if expensive_ratio > 0.5:  # More than 50% of requests are to expensive endpoints
                    confidence += expensive_ratio * 0.6  # 60% weight
        
        # Determine if this is an attack based on confidence
        is_attack = confidence > 0.7  # 70% confidence threshold
        
        return is_attack, confidence
    
    def _update_legitimate_score(self, ip: str):
        """Update the legitimate score for an IP based on browsing patterns"""
        # Check for normal browsing patterns
        requests = self.ip_requests[ip]
        patterns = self.ip_request_patterns[ip]
        
        # Need enough data to analyze
        if len(requests) < 3:
            return
        
        score = 0.2  # Start with a small base score - assume some legitimacy by default
        
        # Factor 1: Balance between pages, APIs and static assets (normal browsing has a mix)
        static_ratio = self.ip_static_assets[ip] / max(1, len(requests))
        page_ratio = (len(requests) - self.ip_static_assets[ip] - self.ip_api_requests[ip]) / max(1, len(requests))
        
        # Typical browsing has 5-15x more static assets than pages
        if 0.05 < page_ratio < 0.3 and 0.7 < static_ratio < 0.95:
            score += 0.3
        elif 0.01 < page_ratio < 0.5 and 0.5 < static_ratio < 0.99:
            # More generous ratio range
            score += 0.2
        
        # Factor 2: Reasonable intervals between requests (not too fast, not too slow)
        intervals = [requests[i] - requests[i-1] for i in range(1, len(requests))]
        avg_interval = sum(intervals) / len(intervals) if intervals else 1.0
        if 0.05 < avg_interval < 10.0:  # Between 50ms and 10s is reasonable
            score += 0.3
        elif 0.01 < avg_interval < 20.0:  # More generous interval range
            score += 0.2
        
        # Factor 3: Pattern of requests (page followed by multiple static assets)
        page_followed_by_assets = 0
        for i in range(len(patterns) - 1):
            if patterns[i][0] == 'page' and patterns[i+1][0] == 'static':
                page_followed_by_assets += 1
        
        if page_followed_by_assets > 0:
            score += 0.2
        
        # Factor 4: Consistent user agent
        if len(self.ip_agents[ip]) <= 2:  # Allow for 1-2 user agents (mobile + desktop is common)
            score += 0.2
        elif len(self.ip_agents[ip]) <= 4:  # Still somewhat reasonable
            score += 0.1
        
        # Update score with exponential moving average (give more weight to new observations)
        self.ip_legitimate_score[ip] = self.ip_legitimate_score[ip] * 0.7 + score * 0.3
        
        # Cap the score between 0 and 1
        self.ip_legitimate_score[ip] = max(0, min(1, self.ip_legitimate_score[ip])) 