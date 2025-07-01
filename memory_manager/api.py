"""
Memory Manager API Module
-----------------------
Provides REST API endpoints for monitoring and managing memory usage.
Can be used with Flask, FastAPI, or other Python web frameworks.
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("memory_manager.api")

class MemoryAPI:
    """API for memory management and monitoring"""
    
    def __init__(self, memory_manager, app=None, route_prefix="/memory"):
        """Initialize the memory API"""
        self.memory_manager = memory_manager
        self.app = app
        self.route_prefix = route_prefix
        
        # Check if we have a proper configuration from memory manager
        if hasattr(memory_manager, 'config') and hasattr(memory_manager.config, 'api'):
            config = memory_manager.config.api
            self.enabled = config.enabled
            self.route_prefix = config.endpoint_prefix or route_prefix
            self.detailed_endpoints = config.detailed_endpoints
            self.management_endpoints = config.management_endpoints
            self.auth_token = config.auth_token
            self.cors_origins = config.cors_origins
        else:
            # Default values
            self.enabled = True
            self.detailed_endpoints = True
            self.management_endpoints = False
            self.auth_token = None
            self.cors_origins = ["*"]
        
        # Register with app if provided
        if app:
            self.register(app)
            
        logger.info(f"Memory API initialized with prefix: {self.route_prefix}")
    
    def check_auth(self, req_token):
        """Check if the request is authorized"""
        # No auth required if no token is set
        if not self.auth_token:
            return True
        
        # Simple token-based authentication
        return req_token == self.auth_token
    
    def register_flask(self, app):
        """Register API endpoints with a Flask app"""
        try:
            from flask import request, jsonify
            
            # Basic status endpoint
            @app.route(f"{self.route_prefix}/status")
            def memory_status():
                # Check authentication for management endpoints
                if self.management_endpoints and self.auth_token:
                    token = request.headers.get('X-Auth-Token')
                    if not self.check_auth(token):
                        return jsonify({'error': 'Unauthorized'}), 401
                
                status = self.memory_manager.get_memory_status()
                return jsonify(status)
            
            # System info endpoint
            @app.route(f"{self.route_prefix}/system")
            def system_info():
                info = self.memory_manager.get_system_info()
                return jsonify(info)
            
            # Memory history endpoint
            if self.detailed_endpoints:
                @app.route(f"{self.route_prefix}/history")
                def memory_history():
                    # Get minutes parameter
                    minutes = request.args.get('minutes', 5, type=int)
                    minutes = min(max(1, minutes), 60)  # Limit to 1-60 minutes
                    
                    history = self.memory_manager.get_memory_history(minutes)
                    return jsonify(history)
                
                @app.route(f"{self.route_prefix}/spikes")
                def memory_spikes():
                    spikes = self.memory_manager.get_memory_spikes()
                    return jsonify(spikes)
                
                @app.route(f"{self.route_prefix}/growth")
                def memory_growth():
                    growth = self.memory_manager.check_memory_growth()
                    return jsonify(growth)
                
                @app.route(f"{self.route_prefix}/metrics")
                def memory_metrics():
                    metrics = self.memory_manager.get_metrics()
                    return jsonify(metrics)
            
            # Management endpoints
            if self.management_endpoints:
                @app.route(f"{self.route_prefix}/optimize", methods=['POST'])
                def memory_optimize():
                    # Check authentication
                    token = request.headers.get('X-Auth-Token')
                    if not self.check_auth(token):
                        return jsonify({'error': 'Unauthorized'}), 401
                    
                    # Get optimization level
                    data = request.get_json() or {}
                    level = data.get('level', 'normal')
                    
                    # Run optimization
                    result = self.memory_manager.optimize_memory(level=level)
                    return jsonify(result)
                
                @app.route(f"{self.route_prefix}/limit", methods=['POST'])
                def set_memory_limit():
                    # Check authentication
                    token = request.headers.get('X-Auth-Token')
                    if not self.check_auth(token):
                        return jsonify({'error': 'Unauthorized'}), 401
                    
                    # Get limit parameter
                    data = request.get_json() or {}
                    limit_mb = data.get('limit_mb', 0)
                    
                    # Set limit
                    result = self.memory_manager.set_memory_limit(limit_mb)
                    return jsonify(result)
            
            # Return success
            logger.info(f"Memory API endpoints registered with Flask: {self.route_prefix}")
            return True
        
        except Exception as e:
            logger.error(f"Error registering Flask endpoints: {e}")
            return False
    
    def register_fastapi(self, app):
        """Register API endpoints with a FastAPI app"""
        try:
            # Try to import FastAPI - this might fail if not installed
            try:
                from fastapi import FastAPI, Depends, HTTPException, Header, Query
                from fastapi.responses import JSONResponse
                from pydantic import BaseModel
                HAS_FASTAPI = True
            except ImportError:
                logger.warning("FastAPI not installed. FastAPI endpoints will not be registered.")
                return False
            
            class OptimizeRequest(BaseModel):
                level: str = "normal"
            
            class LimitRequest(BaseModel):
                limit_mb: int
            
            # Authentication dependency
            async def check_token(x_auth_token: str = Header(None)):
                if self.management_endpoints and self.auth_token:
                    if not self.check_auth(x_auth_token):
                        raise HTTPException(status_code=401, detail="Unauthorized")
                return True
            
            # Basic status endpoint
            @app.get(f"{self.route_prefix}/status")
            async def memory_status(authorized: bool = Depends(check_token)):
                status = self.memory_manager.get_memory_status()
                return status
            
            # System info endpoint
            @app.get(f"{self.route_prefix}/system")
            async def system_info():
                info = self.memory_manager.get_system_info()
                return info
            
            # Memory history endpoint
            if self.detailed_endpoints:
                @app.get(f"{self.route_prefix}/history")
                async def memory_history(minutes: int = Query(5, ge=1, le=60)):
                    history = self.memory_manager.get_memory_history(minutes)
                    return history
                
                @app.get(f"{self.route_prefix}/spikes")
                async def memory_spikes():
                    spikes = self.memory_manager.get_memory_spikes()
                    return spikes
                
                @app.get(f"{self.route_prefix}/growth")
                async def memory_growth():
                    growth = self.memory_manager.check_memory_growth()
                    return growth
                
                @app.get(f"{self.route_prefix}/metrics")
                async def memory_metrics():
                    metrics = self.memory_manager.get_metrics()
                    return metrics
            
            # Management endpoints
            if self.management_endpoints:
                @app.post(f"{self.route_prefix}/optimize")
                async def memory_optimize(request: OptimizeRequest, authorized: bool = Depends(check_token)):
                    result = self.memory_manager.optimize_memory(level=request.level)
                    return result
                
                @app.post(f"{self.route_prefix}/limit")
                async def set_memory_limit(request: LimitRequest, authorized: bool = Depends(check_token)):
                    result = self.memory_manager.set_memory_limit(request.limit_mb)
                    return result
            
            # Return success
            logger.info(f"Memory API endpoints registered with FastAPI: {self.route_prefix}")
            return True
        
        except Exception as e:
            logger.error(f"Error registering FastAPI endpoints: {e}")
            return False
    
    def register(self, app):
        """Register API endpoints with the appropriate framework"""
        self.app = app
        
        # Skip if not enabled
        if not self.enabled:
            logger.info("Memory API is disabled, skipping registration")
            return False
        
        # Detect framework and register endpoints
        if hasattr(app, 'route'):
            # Looks like Flask
            return self.register_flask(app)
        elif hasattr(app, 'get') and hasattr(app, 'post'):
            # Looks like FastAPI
            return self.register_fastapi(app)
        else:
            logger.warning(f"Unknown app framework: {type(app).__name__}")
            return False

# Convenience function to register API with an app
def register_memory_api(memory_manager, app, route_prefix="/memory"):
    """Register memory management API endpoints with a web application"""
    api = MemoryAPI(memory_manager, app, route_prefix)
    return api 