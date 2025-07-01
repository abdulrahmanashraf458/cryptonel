#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Attack Detector Module
----------------------------------------------
Responsible for detecting various types of DDoS attacks using multiple techniques:
1. Traffic pattern analysis (request rate, distribution)
2. Client behavior profiling
3. Packet inspection for malformed requests
4. Machine learning models for anomaly detection
"""

import asyncio
import time
import ipaddress
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional, Union, Any
import socket
import hashlib
import re

import numpy as np
from sklearn.ensemble import IsolationForest
import mmh3  # MurmurHash for efficient feature hashing

# Local imports
from ddos_protection.config import Config
from ddos_protection.utils import (
    is_valid_ip, 
    is_known_good_bot, 
    calculate_entropy, 
    analyze_path_distribution,
    load_geolocation_db,
    get_ip_geolocation,
    extract_request_features
)

# Configure logger
logger = logging.getLogger("ddos_protection.detector")

class TrafficRecord:
    """Stores traffic data for a specific IP address."""
    
    def __init__(self, ip: str, window_size: int = 60):
        self.ip = ip
        self.request_timestamps = deque(maxlen=window_size)  # Rolling window of timestamps
        self.path_distribution = defaultdict(int)  # Path frequency count
        self.bytes_sent = 0
        self.bytes_received = 0
        self.error_count = 0
        self.user_agent_hash = set()  # Hashed user agents for this IP
        self.response_codes = defaultdict(int)  # Status code distribution
        self.last_updated = time.time()
        self.is_suspicious = False
        self.block_score = 0  # Score used to determine if IP should be blocked
        self.challenge_status = False  # Has the IP passed a challenge?
        self.geolocation = None  # Location data
        self.request_interval_variance = 0.0  # Variance in request timing (low variance = bot-like)
        
    def add_request(self, timestamp: float, path: str, bytes_sent: int, 
                  bytes_received: int, status_code: int, user_agent: str):
        """Record a new request from this IP."""
        self.request_timestamps.append(timestamp)
        self.path_distribution[path] += 1
        self.bytes_sent += bytes_sent
        self.bytes_received += bytes_received
        self.response_codes[status_code] += 1
        self.last_updated = timestamp
        
        # Hash and store the user agent to track agent diversity
        ua_hash = mmh3.hash(user_agent, signed=False)
        self.user_agent_hash.add(ua_hash)
        
        # Update request interval variance if we have enough samples
        if len(self.request_timestamps) > 3:
            intervals = np.diff(list(self.request_timestamps))
            self.request_interval_variance = np.var(intervals)
    
    def get_request_rate(self, window_seconds: int = 60) -> float:
        """Calculate requests per second over the last window_seconds."""
        if not self.request_timestamps:
            return 0.0
            
        now = time.time()
        # Filter timestamps within the window
        recent_requests = [ts for ts in self.request_timestamps 
                         if now - ts <= window_seconds]
        
        if not recent_requests:
            return 0.0
            
        # Calculate requests per second
        time_diff = now - min(recent_requests)
        if time_diff <= 0:
            return 0.0
            
        return len(recent_requests) / time_diff
    
    def get_features(self) -> Dict[str, float]:
        """Extract features for anomaly detection."""
        request_rate = self.get_request_rate()
        path_entropy = calculate_entropy(list(self.path_distribution.values()))
        status_entropy = calculate_entropy(list(self.response_codes.values()))
        user_agent_count = len(self.user_agent_hash)
        
        # Calculate ratio of 4xx/5xx errors to total requests
        total_requests = sum(self.response_codes.values())
        error_ratio = 0.0
        if total_requests > 0:
            error_requests = sum(self.response_codes[code] for code in self.response_codes 
                               if code >= 400)
            error_ratio = error_requests / total_requests
        
        return {
            "request_rate": request_rate,
            "path_entropy": path_entropy,
            "status_entropy": status_entropy,
            "user_agent_diversity": user_agent_count,
            "error_ratio": error_ratio,
            "bytes_per_request": self.bytes_received / max(1, total_requests),
            "request_interval_variance": self.request_interval_variance
        }

class RequestBuffer:
    """Thread-safe buffer for incoming requests to be analyzed."""
    
    def __init__(self, maxsize: int = 10000):
        self.buffer = asyncio.Queue(maxsize=maxsize)
        
    async def add_request(self, request_data: Dict[str, Any]):
        """Add request to the buffer for processing."""
        try:
            # Don't block if buffer is full, just drop the request
            await asyncio.wait_for(self.buffer.put(request_data), timeout=0.1)
        except asyncio.TimeoutError:
            logger.warning("Request buffer full, dropping request")
    
    async def get_request(self) -> Dict[str, Any]:
        """Get the next request from the buffer."""
        return await self.buffer.get()
    
    def qsize(self) -> int:
        """Get current buffer size."""
        return self.buffer.qsize()
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return self.buffer.empty()

class AttackDetector:
    """Main class for detecting DDoS attacks using multiple methods."""
    
    def __init__(self, config: Config):
        self.config = config
        self.ip_records: Dict[str, TrafficRecord] = {}
        self.blocked_ips: Set[str] = set()
        self.whitelisted_ips: Set[str] = set()
        self.global_request_rate = 0.0
        self.request_buffer = RequestBuffer()
        self.last_cleanup = time.time()
        self.ml_model = None
        self.model_features = None
        self.attack_status = {
            "under_attack": False,
            "attack_type": None,
            "attack_start": None,
            "intensity": 0,
            "blocked_requests": 0,
            "suspicious_ips": set()
        }
        self.geo_db = None
        self.ipinfo_api_token = getattr(self.config.detector, "ipinfo_api_token", None)
        self.use_ipinfo_api = getattr(self.config.detector, "use_ipinfo_api", False)
        
        # Initialize ML model if enabled
        if self.config.detector.use_ml:
            self.initialize_ml_model()
            
        # Load geolocation database if enabled
        if self.config.detector.use_geolocation:
            self.geo_db = load_geolocation_db(self.config.detector.geo_db_path)
            if not self.geo_db:
                logger.warning("Geolocation database could not be loaded. API-only mode if token is available.")
        
        # Hardcoded list of known good IPs (e.g., internal systems, monitoring)
        # In production, this should be loaded from config/database
        self.whitelisted_ips.update(self.config.detector.whitelist)
        
        # Start the background processing task
        self.processing_task = None
    
    def initialize_ml_model(self):
        """Initialize machine learning model for anomaly detection."""
        logger.info("Initializing machine learning model for anomaly detection")
        # Using Isolation Forest for anomaly detection (lightweight and effective)
        self.ml_model = IsolationForest(
            n_estimators=100,
            max_samples='auto',
            contamination=0.05,  # Expect about 5% of traffic to be anomalous
            random_state=42,
            n_jobs=1  # Limit to single thread for resource efficiency
        )
        
        # Define feature names used for model training/inference
        self.model_features = [
            "request_rate", 
            "path_entropy",
            "status_entropy", 
            "user_agent_diversity",
            "error_ratio",
            "bytes_per_request",
            "request_interval_variance"
        ]
        
        # We'll train the model later when we have enough data
        
    async def start(self):
        """Start attack detector components."""
        logger.info("Starting DDoS attack detector")
        
        # Initial training if available
        if hasattr(self, 'train_model') and callable(self.train_model):
            await self.train_model()
            
        # Start processing loop in background
        self.running = True
        self.processing_task = asyncio.create_task(self.process_requests())
        logger.info("Starting request processing loop")
        
    async def stop(self):
        """Stop attack detector components."""
        logger.info("Stopping DDoS attack detector")
        
        # Stop processing loop
        self.running = False
        
        # Cancel processing task if it exists
        if hasattr(self, 'processing_task') and self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("DDoS attack detector stopped")
    
    async def process_requests(self):
        """Background task to process requests from the buffer."""
        logger.info("Starting request processing loop")
        try:
            while True:
                # Process requests in buffer
                while not self.request_buffer.is_empty():
                    request_data = await self.request_buffer.get_request()
                    self.process_request(request_data)
                
                # Perform periodic tasks
                current_time = time.time()
                if current_time - self.last_cleanup > self.config.detector.cleanup_interval:
                    self.cleanup_old_records()
                    self.update_global_metrics()
                    self.detect_ongoing_attacks()
                    self.last_cleanup = current_time
                    
                    # Retrain ML model periodically if we have enough data
                    if (self.config.detector.use_ml and 
                        len(self.ip_records) > self.config.detector.min_samples_for_training):
                        self.train_ml_model()
                
                # Wait a short time to avoid consuming too many resources
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            logger.info("Request processing task cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error in request processing loop: {e}")
            # Restart the task after a short delay
            await asyncio.sleep(1)
            asyncio.create_task(self.process_requests())
    
    def process_request(self, request_data: Dict[str, Any]):
        """Process a request and check for anomalies."""
        ip = request_data.get("ip", "")
        path = request_data.get("path", "")
        user_agent = request_data.get("user_agent", "")
        
        # Skip processing for whitelisted IPs
        if ip in self.whitelisted_ips:
            return
            
        # Create or update IP record
        if ip not in self.ip_records:
            self.ip_records[ip] = TrafficRecord(ip, window_size=self.config.detector.window_size)
            
            # Get geolocation data if enabled
            if self.config.detector.use_geolocation:
                try:
                    self.ip_records[ip].geolocation = get_ip_geolocation(
                        ip, 
                        self.geo_db,
                        self.ipinfo_api_token if self.use_ipinfo_api else None
                    )
                    
                    # Check if IP is from a blocked country
                    if (self.ip_records[ip].geolocation and 
                        self.ip_records[ip].geolocation.get("country_code") in self.config.detector.blocked_countries):
                        self.ip_records[ip].block_score += 100  # Automatic high score
                        logger.info(f"IP {ip} from blocked country: {self.ip_records[ip].geolocation.get('country_code')}")
                except Exception as e:
                    logger.error(f"Error getting geolocation for {ip}: {e}")
        
        # Add request to IP record
        self.ip_records[ip].add_request(
            request_data.get("timestamp", time.time()),
            path,
            request_data.get("bytes_sent", 0),
            request_data.get("bytes_received", 0),
            request_data.get("status_code", 200),
            user_agent
        )
        
        # Check for suspicious patterns for this individual IP
        self.check_ip_level_anomalies(ip)
        
        # If ML model is enabled and trained, check for anomalies
        if self.config.detector.use_ml and self.ml_model and hasattr(self.ml_model, 'predict'):
            self.check_ml_anomalies(ip)
    
    def check_ip_level_anomalies(self, ip: str):
        """Check for suspicious patterns at the individual IP level."""
        record = self.ip_records[ip]
        
        # Simple rule-based detection
        request_rate = record.get_request_rate()
        
        # Rule 1: High request rate
        if request_rate > self.config.detector.rate_threshold:
            record.block_score += 2
            logger.debug(f"IP {ip} has high request rate: {request_rate:.2f}/sec")
        
        # Rule 2: Path/endpoint hammering (low entropy = repetitive behavior)
        path_values = list(record.path_distribution.values())
        if len(path_values) > 5:  # Only check if we have enough data
            path_entropy = calculate_entropy(path_values)
            if path_entropy < self.config.detector.path_entropy_threshold:
                record.block_score += 2
                logger.debug(f"IP {ip} has low path entropy: {path_entropy:.2f}")
        
        # Rule 3: Unusual user-agent diversity (many different UAs from same IP)
        ua_count = len(record.user_agent_hash)
        if ua_count > self.config.detector.ua_diversity_threshold:
            record.block_score += 2
            logger.debug(f"IP {ip} has high UA diversity: {ua_count}")
        
        # Rule 4: High error rate (4xx/5xx responses)
        total_requests = sum(record.response_codes.values())
        if total_requests > 10:  # Only check if we have enough data
            error_requests = sum(record.response_codes[code] for code in record.response_codes 
                               if code >= 400)
            error_rate = error_requests / total_requests
            if error_rate > self.config.detector.error_rate_threshold:
                record.block_score += 1
                logger.debug(f"IP {ip} has high error rate: {error_rate:.2f}")
        
        # Rule 5: Very low request interval variance (bot-like behavior)
        if (record.request_interval_variance < self.config.detector.bot_variance_threshold and
            len(record.request_timestamps) > 10):
            record.block_score += 2
            logger.debug(f"IP {ip} has low request interval variance: {record.request_interval_variance:.5f}")
        
        # Update suspicious status if block score exceeds threshold
        if record.block_score >= self.config.detector.block_score_threshold:
            record.is_suspicious = True
            self.attack_status["suspicious_ips"].add(ip)
            logger.warning(f"IP {ip} flagged as suspicious (score: {record.block_score})")
    
    def check_ml_anomalies(self, ip: str):
        """Use machine learning model to detect anomalies."""
        record = self.ip_records[ip]
        
        # Extract features for this IP
        features = record.get_features()
        
        # Skip if we don't have all required features
        if not all(f in features for f in self.model_features):
            return
        
        # Convert features to array for prediction
        X = np.array([[features[f] for f in self.model_features]])
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        try:
            prediction = self.ml_model.predict(X)[0]
            # Score is distance from decision boundary, lower is more anomalous
            score = self.ml_model.decision_function(X)[0]
            
            if prediction == -1:  # Anomaly detected
                # Adjust block score based on how anomalous it is
                score_adjustment = max(1, int((0.5 - score) * 5)) if score < 0.5 else 1
                record.block_score += score_adjustment
                logger.debug(f"ML model detected anomaly for IP {ip} (score: {score:.4f})")
                
                # Update suspicious status if block score exceeds threshold
                if record.block_score >= self.config.detector.block_score_threshold:
                    record.is_suspicious = True
                    self.attack_status["suspicious_ips"].add(ip)
        except Exception as e:
            logger.error(f"Error in ML anomaly detection for IP {ip}: {e}")
    
    def train_ml_model(self):
        """Train the ML model using current traffic data."""
        if not self.config.detector.use_ml or not self.ml_model:
            return
            
        try:
            # Only train if we have enough records
            if len(self.ip_records) < self.config.detector.min_samples_for_training:
                return
                
            logger.info(f"Training ML model with {len(self.ip_records)} IP records")
            
            # Extract features from all IP records
            feature_lists = []
            for ip, record in self.ip_records.items():
                features = record.get_features()
                # Only use if we have all required features
                if all(f in features for f in self.model_features):
                    feature_lists.append([features[f] for f in self.model_features])
            
            # Skip if we don't have enough valid feature sets
            if len(feature_lists) < self.config.detector.min_samples_for_training:
                logger.info(f"Not enough valid feature sets for training ({len(feature_lists)})")
                return
                
            # Convert to numpy array and train
            X = np.array(feature_lists)
            self.ml_model.fit(X)
            logger.info("ML model training completed")
            
        except Exception as e:
            logger.error(f"Error training ML model: {e}")
    
    def update_global_metrics(self):
        """Update global traffic metrics."""
        current_time = time.time()
        window = self.config.detector.global_window
        
        # Calculate global request rate across all IPs
        total_requests = 0
        for ip, record in self.ip_records.items():
            # Count requests within the window
            count = sum(1 for ts in record.request_timestamps if current_time - ts <= window)
            total_requests += count
        
        # Calculate requests per second
        self.global_request_rate = total_requests / window if window > 0 else 0
        
        # Update metrics in attack status
        self.attack_status["suspicious_ip_count"] = len(self.attack_status["suspicious_ips"])
        self.attack_status["global_request_rate"] = self.global_request_rate
    
    def detect_ongoing_attacks(self):
        """Detect if we're currently under attack based on metrics."""
        # Check if enough IPs are suspicious
        suspicious_threshold = self.config.detector.suspicious_ip_threshold
        suspicious_count = len(self.attack_status["suspicious_ips"])
        
        # Check if global request rate is too high
        rate_threshold = self.config.detector.global_rate_threshold
        
        # Determine attack type and intensity
        attack_types = []
        intensity = 0
        
        if suspicious_count >= suspicious_threshold:
            attack_types.append("distributed")
            intensity = max(intensity, suspicious_count / suspicious_threshold)
        
        if self.global_request_rate >= rate_threshold:
            attack_types.append("volumetric")
            intensity = max(intensity, self.global_request_rate / rate_threshold)
        
        # Update attack status
        was_under_attack = self.attack_status["under_attack"]
        is_under_attack = len(attack_types) > 0
        
        self.attack_status["under_attack"] = is_under_attack
        self.attack_status["intensity"] = round(intensity, 2) if is_under_attack else 0
        
        if attack_types:
            self.attack_status["attack_type"] = "-".join(attack_types)
        
        # Log attack start or end
        if is_under_attack and not was_under_attack:
            self.attack_status["attack_start"] = datetime.now().isoformat()
            logger.warning(
                f"DDoS attack detected: {self.attack_status['attack_type']} "
                f"(intensity: {intensity:.2f}, suspicious IPs: {suspicious_count})"
            )
        elif not is_under_attack and was_under_attack:
            duration = "unknown"
            if self.attack_status["attack_start"]:
                start_time = datetime.fromisoformat(self.attack_status["attack_start"])
                duration = str(datetime.now() - start_time)
            
            logger.warning(f"DDoS attack ended (duration: {duration})")
            self.attack_status["attack_start"] = None
            self.attack_status["attack_type"] = None
    
    def cleanup_old_records(self):
        """Remove old IP records to prevent memory bloat."""
        current_time = time.time()
        expiration = self.config.detector.record_expiry
        
        # Find expired records
        expired_ips = [
            ip for ip, record in self.ip_records.items()
            if current_time - record.last_updated > expiration
        ]
        
        # Remove expired records
        for ip in expired_ips:
            del self.ip_records[ip]
            if ip in self.attack_status["suspicious_ips"]:
                self.attack_status["suspicious_ips"].remove(ip)
        
        if expired_ips:
            logger.debug(f"Cleaned up {len(expired_ips)} expired IP records")
    
    async def add_request(self, request_data: Dict[str, Any]) -> bool:
        """Process a new request and determine if it should be blocked."""
        ip = request_data.get("ip")
        
        # Critical improvement: Verify request is potentially malicious before blocking
        # This helps prevent false positives and site self-DoS
        
        # Skip IP whitelist checks and directly analyze behavior patterns
        
        # Always add to buffer for analysis regardless of decision
        if self.request_buffer:
            asyncio.create_task(self.request_buffer.add_request(request_data))
            
        # Check for device verification before proceeding with ban
        try:
            from ddos_protection.storage.device_manager import device_manager
            device_fingerprint = request_data.get("device_fingerprint")
            if device_fingerprint and device_manager.is_verified(device_fingerprint):
                # This is a verified device, don't block it
                return False
        except (ImportError, AttributeError):
            pass
        
        # Check frequency of requests from this IP
        if ip in self.ip_records:
            record = self.ip_records[ip]
            request_rate = record.get_request_rate()
            
            # Progressive approach - more violations = stricter action
            # Instead of immediately banning, escalate response based on severity
            
            # Require sustained high request rate before considering blocking
            is_high_frequency = request_rate > self.config.detector.rate_threshold * 2
            
            # Check pattern of requests (low entropy = repetitive behavior = suspicious)
            path_values = list(record.path_distribution.values())
            path_entropy = calculate_entropy(path_values) if len(path_values) > 5 else 999
            is_repetitive = path_entropy < self.config.detector.path_entropy_threshold / 2
            
            # Check interval variance (extremely low variance = bot-like)
            is_bot_like = record.request_interval_variance < self.config.detector.bot_variance_threshold / 10
            
            # Calculate violation score (how many indicators are triggered)
            violation_score = sum([is_high_frequency, is_repetitive, is_bot_like])
            
            # Only take action if at least one indicator is triggered
            if violation_score >= 1:
                # Track violation count with storage manager
                try:
                    from ddos_protection.storage import storage_manager
                    
                    # Get current violation count for this IP
                    violations = storage_manager.behavior_tracking.get(ip, {}).get('violations', 0)
                    
                    # Increment violation count
                    violations += 1
                    
                    # Store updated count
                    storage_manager.behavior_tracking.set(
                        ip, 
                        {'violations': violations}, 
                        ttl=3600  # 1 hour expiry for violations
                    )
                    
                    # Apply progressive action based on violation count:
                    # 1-2 violations: Warning only
                    # 3-9 violations: Apply challenge
                    # 10+ violations: Ban
                    
                    if violations >= 10:
                        # Permanent ban for repeat offenders
                        self.blocked_ips.add(ip)
                        self.attack_status["blocked_requests"] += 1
                        return True  # Block the request
                        
                    elif violations >= 3:
                        # For medium violations, challenge instead of ban
                        record.challenge_status = True
                        
                        # This will allow the middleware to apply a browser challenge
                        # but we return True to indicate blocking until they pass the challenge
                        return True
                        
                    else:
                        # For minor violations, just warn/monitor
                        # The user might get rate-limited but not blocked
                        return False
                        
                except (ImportError, AttributeError, Exception) as e:
                    # If storage manager not available, fall back to old behavior
                    # Only block if multiple signatures of attack are detected
                    is_attack = violation_score >= 2
                    
                    if is_attack and record.block_score >= self.config.detector.block_threshold * 2:
                        # Double-verify this is not a false positive
                        # Check if this IP has many 200 OK responses (legitimate user)
                        try:
                            success_rate = sum(record.response_codes.get(code, 0) for code in [200, 201, 204]) / sum(record.response_codes.values())
                            
                            if success_rate < 0.7:  # If less than 70% success, likely attacker
                                self.blocked_ips.add(ip)
                                self.attack_status["blocked_requests"] += 1
                                return True  # Block the request
                        except:
                            # In case of error, err on the side of allowing the request
                            pass
        
        # Default to allowing request unless explicitly blocked
        return False  # Allow the request
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked."""
        return ip in self.blocked_ips
    
    def whitelist_ip(self, ip: str) -> bool:
        """Add IP to whitelist."""
        if is_valid_ip(ip):
            self.whitelisted_ips.add(ip)
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            return True
        return False
    
    def block_ip(self, ip: str) -> bool:
        """Manually block an IP."""
        if is_valid_ip(ip) and ip not in self.whitelisted_ips:
            self.blocked_ips.add(ip)
            return True
        return False
    
    def unblock_ip(self, ip: str) -> bool:
        """Remove IP from blocked list."""
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current attack detector status."""
        return {
            "under_attack": self.attack_status["under_attack"],
            "attack_type": self.attack_status["attack_type"],
            "attack_start": self.attack_status["attack_start"],
            "intensity": self.attack_status["intensity"],
            "blocked_requests": self.attack_status["blocked_requests"],
            "suspicious_ip_count": len(self.attack_status["suspicious_ips"]),
            "global_request_rate": self.global_request_rate,
            "blocked_ip_count": len(self.blocked_ips),
            "whitelisted_ip_count": len(self.whitelisted_ips),
            "ip_record_count": len(self.ip_records),
            "buffer_size": self.request_buffer.qsize()
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status with suspicious IPs and their scores."""
        suspicious_ips = {}
        for ip in self.attack_status["suspicious_ips"]:
            if ip in self.ip_records:
                record = self.ip_records[ip]
                suspicious_ips[ip] = {
                    "block_score": record.block_score,
                    "request_rate": record.get_request_rate(),
                    "user_agent_count": len(record.user_agent_hash),
                    "paths": dict(record.path_distribution),
                    "geolocation": record.geolocation,
                    "last_updated": datetime.fromtimestamp(record.last_updated).isoformat()
                }
        
        return {
            **self.get_status(),
            "suspicious_ips": suspicious_ips
        }

    async def detect_attack(self, request_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if a request is part of an attack.
        
        Args:
            request_data: Request data including IP, path, user agent, etc.
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: 
                - Boolean indicating if attack is detected
                - Optional challenge data if verification is needed
        """
        ip = request_data.get('ip')
        path = request_data.get('path', '')
        user_agent = request_data.get('user_agent', '')
        
        # Skip detection for whitelisted IPs
        if ip in self.whitelisted_ips:
            return False, None
        
        # Skip detection for known good bots
        if is_known_good_bot(user_agent):
            if ip not in self.whitelisted_ips:
                self.whitelisted_ips.add(ip)
            return False, None
        
        # Process through all attack detectors
        attack_detected = False
        challenge_data = None
        
        # Run traffic analyzer to detect attack patterns
        is_attack = await self.traffic_analyzer.analyze_request(
            ip, path, user_agent, request_size=request_data.get('request_size', 0)
        )
        
        if is_attack:
            logger.warning(f"Attack pattern detected from IP {ip} on path {path}")
            attack_detected = True
            
            # Instead of immediate ban, we may want to challenge the client
            # This allows legitimate users who trigger false positives to continue
            should_challenge = True  # Default to challenging
            
            # Check if this IP has had multiple attack detections recently
            try:
                from ddos_protection.storage import storage_manager
                attack_history = storage_manager.behavior_tracking.get(ip, {})
                
                attack_count = attack_history.get('attack_detections', 0) + 1
                storage_manager.behavior_tracking.set(
                    ip, 
                    {**attack_history, 'attack_detections': attack_count}, 
                    ttl=3600
                )
                
                # Only immediately ban for persistent attackers (5+ detections)
                if attack_count >= 5:
                    should_challenge = False
                    
                    # Apply ban via mitigator
                    try:
                        from ddos import DDoSProtectionSystem
                        if self.ddos_system and hasattr(self.ddos_system, 'mitigator'):
                            await self.ddos_system.mitigator.ban_ip(
                                ip, 
                                f"Detected attack pattern: Multiple detections ({attack_count})", 
                                3600  # 1 hour ban
                            )
                            logger.warning(f"Banned IP {ip} after {attack_count} attack detections")
                    except Exception as e:
                        logger.error(f"Error applying ban: {e}")
            except Exception as e:
                logger.error(f"Error checking attack history: {e}")
            
            # If we should challenge instead of ban
            if should_challenge:
                try:
                    # Generate a challenge
                    if hasattr(self.ddos_system, 'mitigator') and hasattr(self.ddos_system.mitigator, 'challenge_manager'):
                        challenge_manager = self.ddos_system.mitigator.challenge_manager
                        challenge_data = challenge_manager.create_challenge(ip, user_agent)
                except Exception as e:
                    logger.error(f"Error creating challenge: {e}")
        
        return attack_detected, challenge_data 