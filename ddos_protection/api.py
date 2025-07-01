#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - API Module
--------------------------------
Implements a REST API for monitoring and managing the DDoS protection system.
Provides endpoints for:
- Viewing system status and metrics
- Managing blocked/whitelisted IPs
- Viewing attack history and logs
- Adjusting configuration settings
"""

import os
import json
import time
import logging
import asyncio
import ipaddress
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import hmac
import hashlib
from functools import wraps
import traceback

# API framework - use aiohttp for lightweight non-blocking API
try:
    import aiohttp
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logging.getLogger("ddos_protection.api").warning("aiohttp not available, API functionality will be disabled")

# Import dependencies needed for middleware
from flask import request, jsonify

# Local imports
from ddos_protection.config import Config
from ddos_protection.utils import is_valid_ip, get_real_ip_from_request
from ddos_protection.core.detector import AttackDetector
from ddos_protection.core.mitigator import AttackMitigator

# Configure logger
logger = logging.getLogger("ddos_protection.api")

class APIServer:
    """
    REST API server for the DDoS protection system.
    Uses aiohttp for lightweight, non-blocking API endpoints.
    """
    
    def __init__(self, config: Config, detector=None, mitigator=None, monitor=None):
        """
        Initialize the API server.
        
        Args:
            config: System configuration
            detector: Attack detector instance
            mitigator: Attack mitigator instance
            monitor: System monitor instance
        """
        self.config = config
        self.detector = detector
        self.mitigator = mitigator
        self.monitor = monitor
        
        self.app = None
        self.runner = None
        self.site = None
        
        # Rate limiting
        self.rate_limit_counters = {}
        self.rate_limit_window = 60  # 1 minute window
        
        # Check if aiohttp is available
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is required for API functionality")
            return
            
        # Create aiohttp application
        self.app = web.Application(middlewares=[self._middleware_rate_limit, self._middleware_auth])
        self._setup_routes()
        
        logger.info("API server initialized")
    
    async def _middleware_auth(self, request, handler):
        """
        Authentication middleware to validate API requests.
        
        Args:
            request: HTTP request
            handler: Request handler function
            
        Returns:
            Response: HTTP response
        """
        # Skip authentication if not required
        if not self.config.api.auth_required:
            return await handler(request)
            
        # Skip authentication for status endpoint
        if request.path == f"{self.config.api.base_path}/status" and request.method == "GET":
            return await handler(request)
            
        # Check authentication token
        token = None
        
        # Check headers first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
        # Then check query parameters
        if not token:
            token = request.query.get("token")
            
        # Validate token
        if not token or token != self.config.api.auth_token:
            return web.json_response(
                {"error": "Authentication required", "code": "auth_required"},
                status=401
            )
            
        return await handler(request)
    
    async def _middleware_rate_limit(self, request, handler):
        """
        Rate limiting middleware to prevent API abuse.
        
        Args:
            request: HTTP request
            handler: Request handler function
            
        Returns:
            Response: HTTP response
        """
        # Get client IP
        ip = request.remote
        
        # Get current time
        current_time = time.time()
        
        # Initialize counters for this IP if needed
        if ip not in self.rate_limit_counters:
            self.rate_limit_counters[ip] = {
                "count": 0,
                "reset_time": current_time + self.rate_limit_window
            }
            
        # Check if window has expired and reset if needed
        if current_time > self.rate_limit_counters[ip]["reset_time"]:
            self.rate_limit_counters[ip] = {
                "count": 0,
                "reset_time": current_time + self.rate_limit_window
            }
            
        # Increment request count
        self.rate_limit_counters[ip]["count"] += 1
        
        # Check if rate limit is exceeded
        if self.rate_limit_counters[ip]["count"] > self.config.api.rate_limit:
            # Add rate limit headers
            headers = {
                "X-RateLimit-Limit": str(self.config.api.rate_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(self.rate_limit_counters[ip]["reset_time"])),
                "Retry-After": str(int(self.rate_limit_counters[ip]["reset_time"] - current_time))
            }
            
            return web.json_response(
                {"error": "Rate limit exceeded", "code": "rate_limit_exceeded"},
                status=429,
                headers=headers
            )
            
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(self.config.api.rate_limit),
            "X-RateLimit-Remaining": str(self.config.api.rate_limit - self.rate_limit_counters[ip]["count"]),
            "X-RateLimit-Reset": str(int(self.rate_limit_counters[ip]["reset_time"]))
        }
        
        # Call handler
        response = await handler(request)
        
        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value
            
        return response
    
    def _setup_routes(self):
        """Setup API routes."""
        base = self.config.api.base_path
        
        # Status endpoints
        self.app.router.add_get(f"{base}/status", self.get_status)
        self.app.router.add_get(f"{base}/metrics", self.get_metrics)
        self.app.router.add_get(f"{base}/detailed-status", self.get_detailed_status)
        
        # Management endpoints (conditionally enable)
        if self.config.api.enable_management:
            self.app.router.add_get(f"{base}/config", self.get_config)
            self.app.router.add_post(f"{base}/block", self.block_ip)
            self.app.router.add_post(f"{base}/unblock", self.unblock_ip)
            self.app.router.add_post(f"{base}/whitelist", self.whitelist_ip)
            self.app.router.add_get(f"{base}/blocked", self.get_blocked_ips)
            self.app.router.add_get(f"{base}/suspicious", self.get_suspicious_ips)
            self.app.router.add_post(f"{base}/reset-stats", self.reset_stats)
    
    async def start(self, host: str = "127.0.0.1", port: int = 8080):
        """
        Start the API server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        if not AIOHTTP_AVAILABLE or not self.app:
            logger.error("Cannot start API server: aiohttp not available")
            return
            
        # Create runner and site
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Create site
        self.site = web.TCPSite(self.runner, host, port)
        
        # Start site
        await self.site.start()
        
        logger.info(f"API server started on http://{host}:{port}{self.config.api.base_path}")
    
    async def stop(self):
        """Stop the API server."""
        if self.runner:
            await self.runner.cleanup()
            logger.info("API server stopped")
    
    async def get_status(self, request):
        """
        Get current system status.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with system status
        """
        status = {
            "enabled": self.config.enabled,
            "version": "1.0.0",  # TODO: Get from version file
            "timestamp": datetime.now().isoformat(),
        }
        
        # Add detector status if available
        if self.detector:
            detector_status = self.detector.get_status()
            status.update({
                "under_attack": detector_status.get("under_attack", False),
                "attack_type": detector_status.get("attack_type"),
                "attack_start": detector_status.get("attack_start"),
                "intensity": detector_status.get("intensity", 0),
                "blocked_requests": detector_status.get("blocked_requests", 0),
            })
        
        # Add mitigator statistics if available
        if self.mitigator:
            mitigator_stats = self.mitigator.get_mitigation_stats()
            status.update({
                "blocked_ips": mitigator_stats.get("blocked_ip_count", 0),
                "rate_limited_requests": mitigator_stats.get("rate_limited", 0),
                "challenged_requests": mitigator_stats.get("challenged", 0),
            })
            
        return web.json_response(status)
    
    async def get_metrics(self, request):
        """
        Get system metrics in Prometheus format.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with Prometheus metrics
        """
        metrics = []
        
        # Basic system metrics
        metrics.append("# HELP ddos_system_enabled Whether the DDoS protection system is enabled")
        metrics.append("# TYPE ddos_system_enabled gauge")
        metrics.append(f"ddos_system_enabled {1 if self.config.enabled else 0}")
        
        # Add detector metrics if available
        if self.detector:
            detector_status = self.detector.get_status()
            
            metrics.append("# HELP ddos_under_attack Whether the system is currently under attack")
            metrics.append("# TYPE ddos_under_attack gauge")
            metrics.append(f"ddos_under_attack {1 if detector_status.get('under_attack', False) else 0}")
            
            metrics.append("# HELP ddos_attack_intensity Attack intensity level")
            metrics.append("# TYPE ddos_attack_intensity gauge")
            metrics.append(f"ddos_attack_intensity {detector_status.get('intensity', 0)}")
            
            metrics.append("# HELP ddos_blocked_requests_total Total number of blocked requests")
            metrics.append("# TYPE ddos_blocked_requests_total counter")
            metrics.append(f"ddos_blocked_requests_total {detector_status.get('blocked_requests', 0)}")
            
            metrics.append("# HELP ddos_suspicious_ips Number of suspicious IPs")
            metrics.append("# TYPE ddos_suspicious_ips gauge")
            metrics.append(f"ddos_suspicious_ips {detector_status.get('suspicious_ip_count', 0)}")
            
            metrics.append("# HELP ddos_global_request_rate Global request rate")
            metrics.append("# TYPE ddos_global_request_rate gauge")
            metrics.append(f"ddos_global_request_rate {detector_status.get('global_request_rate', 0)}")
        
        # Add mitigator metrics if available
        if self.mitigator:
            mitigator_stats = self.mitigator.get_mitigation_stats()
            
            metrics.append("# HELP ddos_blocked_ips Number of blocked IPs")
            metrics.append("# TYPE ddos_blocked_ips gauge")
            metrics.append(f"ddos_blocked_ips {mitigator_stats.get('blocked_ip_count', 0)}")
            
            metrics.append("# HELP ddos_rate_limited_total Total number of rate limited requests")
            metrics.append("# TYPE ddos_rate_limited_total counter")
            metrics.append(f"ddos_rate_limited_total {mitigator_stats.get('rate_limited', 0)}")
            
            metrics.append("# HELP ddos_circuit_broken_total Total number of circuit broken requests")
            metrics.append("# TYPE ddos_circuit_broken_total counter")
            metrics.append(f"ddos_circuit_broken_total {mitigator_stats.get('circuit_broken', 0)}")
            
            metrics.append("# HELP ddos_challenged_total Total number of challenged requests")
            metrics.append("# TYPE ddos_challenged_total counter")
            metrics.append(f"ddos_challenged_total {mitigator_stats.get('challenged', 0)}")
            
            metrics.append("# HELP ddos_tarpitted_total Total number of tarpitted requests")
            metrics.append("# TYPE ddos_tarpitted_total counter")
            metrics.append(f"ddos_tarpitted_total {mitigator_stats.get('tarpitted', 0)}")
            
            metrics.append("# HELP ddos_uptime System uptime in seconds")
            metrics.append("# TYPE ddos_uptime gauge")
            metrics.append(f"ddos_uptime {mitigator_stats.get('uptime', 0)}")
            
        return web.Response(text="\n".join(metrics), content_type="text/plain")
    
    async def get_detailed_status(self, request):
        """
        Get detailed system status.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with detailed system status
        """
        status = {
            "enabled": self.config.enabled,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "integration_mode": self.config.integration_mode,
                "bypass_on_error": self.config.bypass_on_error,
            }
        }
        
        # Add detector status if available
        if self.detector:
            status["detector"] = self.detector.get_detailed_status()
        
        # Add mitigator statistics if available
        if self.mitigator:
            status["mitigator"] = self.mitigator.get_mitigation_stats()
            
        return web.json_response(status)
    
    async def get_config(self, request):
        """
        Get system configuration.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with system configuration
        """
        # Convert config to dict, excluding sensitive fields
        config_dict = self.config.to_dict()
        
        # Remove sensitive fields
        if "api" in config_dict and "auth_token" in config_dict["api"]:
            config_dict["api"]["auth_token"] = "********"
            
        if "monitor" in config_dict:
            if "email_password" in config_dict["monitor"]:
                config_dict["monitor"]["email_password"] = "********"
            if "slack_webhook_url" in config_dict["monitor"]:
                config_dict["monitor"]["slack_webhook_url"] = "********"
            
        return web.json_response(config_dict)
    
    async def block_ip(self, request):
        """
        Block an IP address.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with result
        """
        # Parse request body
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON", "code": "invalid_json"},
                status=400
            )
            
        # Get IP from request
        ip = data.get("ip")
        
        # Validate IP
        if not ip or not is_valid_ip(ip):
            return web.json_response(
                {"error": "Invalid IP address", "code": "invalid_ip"},
                status=400
            )
            
        # Block IP using mitigator
        if self.mitigator:
            success = self.mitigator.block_ip(ip)
            if success:
                logger.info(f"IP {ip} blocked via API")
                return web.json_response({"success": True, "ip": ip})
            else:
                return web.json_response(
                    {"error": "Failed to block IP", "code": "block_failed"},
                    status=400
                )
        else:
            return web.json_response(
                {"error": "Mitigator not available", "code": "mitigator_not_available"},
                status=503
            )
    
    async def unblock_ip(self, request):
        """
        Unblock an IP address.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with result
        """
        # Parse request body
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON", "code": "invalid_json"},
                status=400
            )
            
        # Get IP from request
        ip = data.get("ip")
        
        # Validate IP
        if not ip or not is_valid_ip(ip):
            return web.json_response(
                {"error": "Invalid IP address", "code": "invalid_ip"},
                status=400
            )
            
        # Unblock IP using mitigator
        if self.mitigator:
            success = self.mitigator.unblock_ip(ip)
            if success:
                logger.info(f"IP {ip} unblocked via API")
                return web.json_response({"success": True, "ip": ip})
            else:
                return web.json_response(
                    {"error": "Failed to unblock IP", "code": "unblock_failed"},
                    status=400
                )
        else:
            return web.json_response(
                {"error": "Mitigator not available", "code": "mitigator_not_available"},
                status=503
            )
    
    async def whitelist_ip(self, request):
        """
        Whitelist an IP address.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with result
        """
        # Parse request body
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON", "code": "invalid_json"},
                status=400
            )
            
        # Get IP from request
        ip = data.get("ip")
        
        # Validate IP
        if not ip or not is_valid_ip(ip):
            return web.json_response(
                {"error": "Invalid IP address", "code": "invalid_ip"},
                status=400
            )
            
        # Whitelist IP using mitigator
        if self.mitigator:
            success = self.mitigator.whitelist_ip(ip)
            
            # Also whitelist in detector if available
            if self.detector:
                detector_success = self.detector.whitelist_ip(ip)
                success = success and detector_success
                
            if success:
                logger.info(f"IP {ip} whitelisted via API")
                return web.json_response({"success": True, "ip": ip})
            else:
                return web.json_response(
                    {"error": "Failed to whitelist IP", "code": "whitelist_failed"},
                    status=400
                )
        else:
            return web.json_response(
                {"error": "Mitigator not available", "code": "mitigator_not_available"},
                status=503
            )
    
    async def get_blocked_ips(self, request):
        """
        Get list of blocked IPs.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with blocked IPs
        """
        blocked_ips = []
        
        # Get blocked IPs from mitigator
        if self.mitigator and hasattr(self.mitigator, "blocked_ips"):
            blocked_ips = list(self.mitigator.blocked_ips)
            
        return web.json_response({"blocked_ips": blocked_ips, "count": len(blocked_ips)})
    
    async def get_suspicious_ips(self, request):
        """
        Get list of suspicious IPs.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with suspicious IPs
        """
        suspicious_ips = {}
        
        # Get suspicious IPs from detector
        if self.detector and hasattr(self.detector, "get_detailed_status"):
            detector_status = self.detector.get_detailed_status()
            if "suspicious_ips" in detector_status:
                suspicious_ips = detector_status["suspicious_ips"]
                
        return web.json_response({
            "suspicious_ips": suspicious_ips, 
            "count": len(suspicious_ips)
        })
    
    async def reset_stats(self, request):
        """
        Reset system statistics.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: HTTP response with result
        """
        # Reset mitigator statistics
        if self.mitigator and hasattr(self.mitigator, "reset_stats"):
            self.mitigator.reset_stats()
            
        # Reset detector statistics
        # Not implemented yet
            
        logger.info("System statistics reset via API")
        return web.json_response({"success": True})


class FlaskIntegration:
    """Integration class for Flask applications."""
    
    def __init__(self, app, config: Config, detector=None, mitigator=None):
        """Initialize Flask integration."""
        self.app = app
        self.config = config
        
        # Create components if not provided
        self.detector = detector or AttackDetector(config)
        self.mitigator = mitigator or AttackMitigator(config)
        
        # Setup middleware
        self._setup_middleware()
        
        logger.info("DDoS protection integrated with Flask application")
    
    def _setup_middleware(self):
        """Setup Flask middleware for DDoS protection."""
        
        @self.app.before_request
        async def ddos_protection():
            """DDoS protection middleware for Flask."""
            # Skip protection if disabled
            if not self.config.enabled:
                return None
                
            try:
                # Get client IP
                ip = get_real_ip_from_request(request)
                
                # Check for local request using attribute (set by our custom middleware)
                is_local_request = getattr(request, 'is_local_request', False)
                
                # Fast path for local requests
                if is_local_request:
                    return None
                
                # Skip API endpoints
                if request.path.startswith(self.config.api.base_path):
                    return None
                
                # Skip static files
                if 'static' in request.path or any(request.path.endswith(ext) for ext in ['.css', '.js', '.jpg', '.png', '.gif', '.ico']):
                    return None
                
                # Create request data
                request_data = {
                    "ip": ip,
                    "timestamp": time.time(),
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "bytes_received": int(request.headers.get("Content-Length", 0)),
                    "bytes_sent": 0,  # Will be updated in after_request
                    "status_code": 200  # Will be updated in after_request
                }
                
                # Process request through detector
                should_block = await self.detector.add_request(request_data)
                
                if should_block:
                    # Process through mitigator for appropriate action
                    allowed, challenge_data = await self.mitigator.process_request(
                        ip=ip,
                        endpoint=request.path,
                        user_agent=request.headers.get("User-Agent", ""),
                        request_size=int(request.headers.get("Content-Length", 0))
                    )
                    
                    if not allowed:
                        if challenge_data:
                            # Return challenge response
                            return jsonify({"challenge": challenge_data}), 403
                        else:
                            # Return rate limit response
                            return jsonify({"error": "Too many requests"}), 429
            
            except Exception as e:
                logger.error(f"Error in DDoS protection middleware: {e}")
                logger.error(traceback.format_exc())
                
                # If bypass_on_error is enabled, let the request through
                if self.config.bypass_on_error:
                    return None
                else:
                    # Otherwise, block the request
                    return jsonify({"error": "Internal error in DDoS protection"}), 500
                
            # Allow request to proceed
            return None
        
        @self.app.after_request
        def ddos_after_request(response):
            """After request handler to record response status."""
            # Skip processing if disabled
            if not self.config.enabled:
                return response
                
            try:
                path = request.path
                status_code = response.status_code
                
                # Record success/failure for circuit breaker
                if status_code >= 500:
                    self.mitigator.record_request_failure(path, get_real_ip_from_request(request))
                else:
                    self.mitigator.record_request_success(path)
                    
            except Exception as e:
                logger.error(f"Error in after_request handler: {e}")
                
            return response


class FastAPIIntegration:
    """
    FastAPI integration for the DDoS protection system.
    Provides middleware for FastAPI applications.
    """
    
    def __init__(self, app, config: Config, detector=None, mitigator=None):
        """
        Initialize FastAPI integration.
        
        Args:
            app: FastAPI application
            config: System configuration
            detector: Attack detector instance
            mitigator: Attack mitigator instance
        """
        self.app = app
        self.config = config
        self.detector = detector
        self.mitigator = mitigator
        
        # Register middleware
        self._setup_middleware()
        
        logger.info("FastAPI integration initialized")
    
    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        from fastapi import Request, Response, HTTPException
        from fastapi.responses import JSONResponse
        
        @self.app.middleware("http")
        async def ddos_protection_middleware(request: Request, call_next):
            """DDoS protection middleware for FastAPI."""
            # Skip protection if disabled
            if not self.config.enabled:
                return await call_next(request)
                
            try:
                # Extract client IP
                ip = request.client.host if request.client else "0.0.0.0"
                
                # Extract request information
                path = request.url.path
                user_agent = request.headers.get("User-Agent", "")
                
                # Get request size
                request_size = 0
                if request.headers.get("Content-Length"):
                    try:
                        request_size = int(request.headers.get("Content-Length", "0"))
                    except ValueError:
                        pass
                
                # Process request through detector
                if self.detector:
                    # Create request data for detector
                    request_data = {
                        "ip": ip,
                        "timestamp": time.time(),
                        "path": path,
                        "user_agent": user_agent,
                        "bytes_received": request_size,
                        "bytes_sent": 0,  # Will be updated after response
                        "status_code": 200  # Will be updated after response
                    }
                    
                    # Check if request should be blocked
                    should_block = await self.detector.add_request(request_data)
                    if should_block:
                        # Return 403 Forbidden for blocked requests
                        return JSONResponse(
                            status_code=403,
                            content={"error": "Request blocked by DDoS protection"}
                        )
                
                # Process request through mitigator
                if self.mitigator:
                    # Process request through mitigator
                    is_allowed, response_data = await self.mitigator.process_request(
                        ip=ip,
                        endpoint=path,
                        user_agent=user_agent,
                        request_size=request_size
                    )
                    
                    if not is_allowed:
                        # Check if we have a challenge response
                        if response_data and "challenge" in response_data:
                            # Return challenge to client
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "status": "challenge_required",
                                    "challenge": response_data["challenge"]
                                }
                            )
                            
                        # Return 429 Too Many Requests for rate-limited requests
                        return JSONResponse(
                            status_code=429,
                            content={"error": "Too many requests"}
                        )
                
                # Allow request to proceed
                response = await call_next(request)
                
                # Record successful request in circuit breaker
                if self.mitigator and response.status_code < 500:
                    self.mitigator.record_request_success(path)
                
                return response
                
            except Exception as e:
                logger.error(f"Error in DDoS protection middleware: {e}")
                
                # If bypass_on_error is enabled, let the request through
                if self.config.bypass_on_error:
                    return await call_next(request)
                else:
                    # Otherwise, block the request
                    return JSONResponse(
                        status_code=500,
                        content={"error": "Internal error in DDoS protection"}
                    )


def create_api_server(config: Config, detector=None, mitigator=None, monitor=None) -> APIServer:
    """
    Create an API server instance.
    
    Args:
        config: System configuration
        detector: Attack detector instance
        mitigator: Attack mitigator instance
        monitor: System monitor instance
        
    Returns:
        APIServer: API server instance
    """
    return APIServer(config, detector, mitigator, monitor)


def integrate_with_flask(app, config: Config, detector=None, mitigator=None) -> FlaskIntegration:
    """
    Integrate DDoS protection with a Flask application.
    
    Args:
        app: Flask application
        config: System configuration
        detector: Attack detector instance
        mitigator: Attack mitigator instance
        
    Returns:
        FlaskIntegration: Flask integration instance
    """
    return FlaskIntegration(app, config, detector, mitigator)


def integrate_with_fastapi(app, config: Config, detector=None, mitigator=None) -> FastAPIIntegration:
    """
    Integrate DDoS protection with a FastAPI application.
    
    Args:
        app: FastAPI application
        config: System configuration
        detector: Attack detector instance
        mitigator: Attack mitigator instance
        
    Returns:
        FastAPIIntegration: FastAPI integration instance
    """
    return FastAPIIntegration(app, config, detector, mitigator) 