#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Cloudflare Integration
---------------------------------------------
Implements integration with Cloudflare API for DDoS protection.
- Block and unblock IPs through Cloudflare
- Sync banned IPs with Cloudflare
- Automatically apply rate limits

This module is configured to be the PRIMARY method of protection,
bypassing local JSON storage and device fingerprinting systems.
"""

import os
import time
import json
import logging
import threading
import asyncio
from typing import Dict, List, Optional, Union, Any
from functools import wraps

# Import API client explicitly to fix import error
try:
    from .api import CloudflareAPIClient, blocked_ips_cache
except ImportError as e:
    logging.getLogger('ddos_protection.cloudflare').error(f"Failed to import CloudflareAPIClient: {e}")
    # Create stub definitions if API is not available
    class CloudflareAPIClient:
        def __init__(self, *args, **kwargs):
            pass
    blocked_ips_cache = set()

# Configuration for Cloudflare API
CF_API_EMAIL = os.environ.get('CF_API_EMAIL', '')
CF_API_KEY = os.environ.get('CF_API_KEY', '')
CF_ZONE_ID = os.environ.get('CF_ZONE_ID', '')

# Configure logger
logger = logging.getLogger('ddos_protection.cloudflare')

# Check if we're in development mode
CF_DEV_MODE = os.environ.get('CF_DEV_MODE', 'false').lower() == 'true'

# Flag to indicate if Cloudflare integration is enabled
if CF_DEV_MODE:
    CLOUDFLARE_ENABLED = True
    logger.info("Cloudflare running in DEVELOPMENT MODE (no actual API calls)")
else:
    CLOUDFLARE_ENABLED = all([CF_API_EMAIL, CF_API_KEY, CF_ZONE_ID])

# Create Cloudflare routes blueprint if Flask is available
try:
    from flask import Blueprint, request, jsonify, current_app
    from werkzeug.local import LocalProxy
    
    # Create blueprint for Cloudflare routes
    cf_blueprint = Blueprint('cloudflare', __name__)
    
    # Import routes if available
    try:
        from .routes import register_cloudflare_routes
    except ImportError:
        register_cloudflare_routes = None
        
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    cf_blueprint = None
    register_cloudflare_routes = None

# Global client instance
cf_client = None

# Initialize the cf_client
try:
    cf_client = CloudflareAPIClient(CF_API_EMAIL, CF_API_KEY, CF_ZONE_ID)
    logger.info("Cloudflare API client created")
except Exception as e:
    logger.error(f"Error creating Cloudflare API client: {e}")
    cf_client = None

def init_cloudflare_integration(app=None):
    """
    Initialize Cloudflare integration.
    
    Args:
        app: Flask application (optional)
        
    Returns:
        bool: True if initialization was successful
    """
    global cf_client, CLOUDFLARE_ENABLED
    
    # Set environment variable to indicate Cloudflare is primary protection method
    os.environ['USE_CLOUDFLARE_EXCLUSIVELY'] = 'true'
    
    # Check if we're in development mode
    dev_mode = CF_DEV_MODE
    
    # In dev mode, always return success without warnings
    if dev_mode:
        # Create client instance in dev mode
        try:
            from .api import CloudflareAPIClient, blocked_ips_cache
            logger.info("Cloudflare integration initialized in DEVELOPMENT MODE")
            if app is not None and FLASK_AVAILABLE:
                # Register routes with app
                if register_cloudflare_routes:
                    register_cloudflare_routes(app)
                    
                # Add client to app context
                app.cf_client = cf_client
                
            return True
        except Exception as e:
            logger.debug(f"Dev mode error (safe to ignore): {e}")
            return True
            
    # In production mode, check for credentials
    if not CLOUDFLARE_ENABLED:
        return False
    
    # Create client instance
    try:
        from .api import CloudflareAPIClient, blocked_ips_cache
        
        # Normal mode with real credentials
        cf_client = CloudflareAPIClient(CF_API_EMAIL, CF_API_KEY, CF_ZONE_ID)
        logger.info("Cloudflare API client initialized successfully")
        
        # Inject client to Flask app if provided
        if app is not None and FLASK_AVAILABLE:
            # Register routes with app
            if register_cloudflare_routes:
                register_cloudflare_routes(app)
                
            # Add client to app context
            app.cf_client = cf_client
            
            # In Cloudflare-only mode, we don't need to patch ban_manager
            # since all storage modules have been removed
            try:
                if 'USE_CLOUDFLARE_EXCLUSIVELY' not in os.environ or os.environ['USE_CLOUDFLARE_EXCLUSIVELY'].lower() != 'true':
                    integrate_with_ban_manager()
                    logger.info("Ban manager patched to use Cloudflare")
            except Exception as e:
                # This is expected in Cloudflare-only mode, so just debug log
                logger.debug(f"Ban manager integration skipped (Cloudflare-only mode): {e}")
            
            logger.info("Cloudflare integration with Flask app completed")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Cloudflare API client: {e}")
        return False

def patch_options_handling():
    """Patch systems to ignore OPTIONS requests"""
    try:
        # Patch ban_manager if available
        from ddos_protection.storage import ban_manager
        
        # Store original method
        original_ban_ip = ban_manager.ban_ip
        
        # Create a new method that skips OPTIONS requests
        def patched_ban_ip(ip, reason="Unknown", duration=None):
            if "OPTIONS" in reason:
                logger.info(f"Skipping ban for IP {ip} using OPTIONS method: {reason}")
                return False
                
            # Call original method
            return original_ban_ip(ip, reason, duration)
        
        # Apply the patch
        ban_manager.ban_ip = patched_ban_ip
        logger.info("Ban manager patched to ignore OPTIONS requests")
    except Exception as e:
        logger.error(f"Failed to patch OPTIONS handling: {e}")

def integrate_with_ban_manager():
    """Integrate Cloudflare client with ban manager"""
    try:
        from ddos_protection.storage import ban_manager
        from .api import CloudflareAPIClient
        
        if not cf_client:
            logger.warning("Cloudflare client not initialized")
            return False
            
        # Store original methods
        original_ban_ip = ban_manager.ban_ip
        original_unban_ip = ban_manager.unban_ip
        
        # Create enhanced ban_ip method that uses Cloudflare
        def enhanced_ban_ip(ip, reason="Unknown", duration=None):
            # Skip if it's an OPTIONS request
            if "OPTIONS" in reason:
                logger.info(f"Skipping ban for IP {ip} using OPTIONS method: {reason}")
                return False
                
            # Skip tracking and fingerprinting related bans
            if "device" in reason.lower() or "fingerprint" in reason.lower() or "tracking" in reason.lower():
                logger.info(f"Skipping device-related ban for IP {ip}: {reason}")
                return False
                
            # Always use Cloudflare and skip local storage
            try:
                # Use event loop if one exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule it for later execution to avoid blocking
                        asyncio.create_task(cf_client.block_ip(ip, reason, duration or 86400))
                    else:
                        # Run it now if loop is not running
                        loop.run_until_complete(cf_client.block_ip(ip, reason, duration or 86400))
                except RuntimeError:
                    # No event loop, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(cf_client.block_ip(ip, reason, duration or 86400))
                    finally:
                        loop.close()
                
                logger.info(f"IP {ip} banned via Cloudflare: {reason}")
                return True
            except Exception as e:
                logger.error(f"Error banning IP through Cloudflare: {e}")
                # Fallback to local ban only if Cloudflare fails AND we're not explicitly set to use only Cloudflare
                if os.environ.get('USE_CLOUDFLARE_EXCLUSIVELY', 'true').lower() != 'true':
                    return original_ban_ip(ip, reason, duration)
                return False
        
        # Create enhanced unban_ip method that uses Cloudflare
        def enhanced_unban_ip(ip):
            # Always try to unban in Cloudflare
            try:
                # Use event loop if one exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule it for later execution to avoid blocking
                        asyncio.create_task(cf_client.unblock_ip(ip))
                    else:
                        # Run it now if loop is not running
                        loop.run_until_complete(cf_client.unblock_ip(ip))
                except RuntimeError:
                    # No event loop, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(cf_client.unblock_ip(ip))
                    finally:
                        loop.close()
                
                logger.info(f"IP {ip} unbanned from Cloudflare")
            except Exception as e:
                logger.error(f"Error unbanning IP from Cloudflare: {e}")
            
            # Always try local unban too for consistency
            return original_unban_ip(ip)
        
        # Apply patches
        ban_manager.ban_ip = enhanced_ban_ip
        ban_manager.unban_ip = enhanced_unban_ip
        
        logger.info("Ban manager patched to use Cloudflare")
        return True
    except Exception as e:
        logger.error(f"Failed to integrate with ban manager: {e}")
        return False

async def sync_from_cloudflare():
    """
    Synchronize banned IPs from Cloudflare to local system.
    This ensures consistency between Cloudflare and the local ban list.
    """
    global cf_client
    
    if not cf_client:
        logger.warning("Cloudflare client not initialized")
        return False
        
    try:
        # Get list of blocked IPs from Cloudflare
        cf_banned_ips = await cf_client.list_blocked_ips()
        
        if not cf_banned_ips:
            logger.info("No IPs banned in Cloudflare")
            return True
            
        # Get local ban manager
        try:
            from ddos_protection.storage import ban_manager
            from ddos_protection import banned_ips_cache
            
            # Sync banned IPs to local cache
            for ip, info in cf_banned_ips.items():
                # Add to banned_ips_cache if available
                if hasattr(banned_ips_cache, 'add'):  # If it's a set
                    banned_ips_cache.add(ip)
                elif isinstance(banned_ips_cache, dict):  # If it's a dict
                    banned_ips_cache[ip] = True
                
                # We don't need to call ban_ip since we're using Cloudflare exclusively
            
            logger.info(f"Synchronized {len(cf_banned_ips)} banned IPs from Cloudflare")
            return True
        except ImportError:
            logger.warning("Local ban manager not available")
            return False
    except Exception as e:
        logger.error(f"Error syncing from Cloudflare: {e}")
        return False

def start_periodic_sync(interval=3600):
    """
    Start periodic synchronization with Cloudflare.
    
    Args:
        interval: Sync interval in seconds (default: 1 hour)
    """
    global cf_client
    
    if not cf_client:
        logger.warning("Cloudflare client not initialized")
        return False
        
    try:
        def sync_job():
            """Run sync job periodically"""
            while True:
                try:
                    # Use asyncio.run for the sync task
                    asyncio.run(sync_from_cloudflare())
                except Exception as e:
                    logger.error(f"Error in periodic Cloudflare sync: {e}")
                    
                # Sleep for the interval
                time.sleep(interval)
        
        # Start sync thread
        sync_thread = threading.Thread(target=sync_job, daemon=True)
        sync_thread.start()
        
        logger.info(f"Started periodic Cloudflare sync (interval: {interval}s)")
        return True
    except Exception as e:
        logger.error(f"Failed to start periodic sync: {e}")
        return False

# Export primary interfaces
__all__ = ['CloudflareAPIClient', 'cf_client', 'integrate_with_ban_manager',
           'sync_from_cloudflare', 'init_cloudflare_integration', 'start_periodic_sync', 'CLOUDFLARE_ENABLED'] 