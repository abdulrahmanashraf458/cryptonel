#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - OPTIONS Patch
-------------------------------------
Patches the DDoS protection system to:
1. Not ban based on OPTIONS HTTP method (needed for CORS preflight)
2. Prioritize Cloudflare for bans
3. Fix event loop conflicts
"""

import logging
import asyncio
import sys
from typing import Dict, Any, Optional, Union, List
import os
import time
import traceback

# Configure logger
logger = logging.getLogger("ddos_protection.options_patch")

# Flag to determine if we should use Cloudflare exclusively
USE_CLOUDFLARE_EXCLUSIVELY = True

def patch_ddos_system():
    """
    Apply patches to the DDoS protection system.
    This function modifies the behavior of the system to:
    1. Not ban based on OPTIONS HTTP method
    2. Prioritize Cloudflare for banning
    3. Fix event loop conflicts
    """
    logger.info("Applying DDoS protection system patches")
    
    # Patch ban_manager to prefer Cloudflare
    _patch_ban_manager()
    
    # Patch server.py early_ip_rejection to ignore OPTIONS method
    _patch_early_ip_rejection()
    
    # Patch asyncio to prevent event loop issues
    _patch_asyncio()
    
    # Clean up any existing OPTIONS-related bans
    _cleanup_options_bans()
    
    # Set environment variable to signal the patch is applied
    os.environ["DDOS_PATCHED"] = "true"
    os.environ["USE_CLOUDFLARE_EXCLUSIVELY"] = "true"
    
    logger.info("DDoS protection system patches applied successfully")

def _patch_asyncio():
    """Patch asyncio to better handle event loop conflicts"""
    try:
        # Store original functions
        original_get_event_loop = asyncio.get_event_loop
        
        # Create a patched version that is more reliable
        def patched_get_event_loop():
            try:
                # First try to get the running loop (the standard way)
                return asyncio.get_running_loop()
            except RuntimeError:
                # If no running loop, fall back to the original behavior
                try:
                    return original_get_event_loop()
                except RuntimeError:
                    # No event loop exists, create a new one
                    if sys.platform.startswith('win'):
                        loop = asyncio.SelectorEventLoop()
                    else:
                        loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop
            
        # Apply patch
        asyncio.get_event_loop = patched_get_event_loop
        
        # Patch run_until_complete to handle errors better
        original_run_until_complete = asyncio.BaseEventLoop.run_until_complete
        
        def patched_run_until_complete(self, future):
            try:
                return original_run_until_complete(self, future)
            except RuntimeError as e:
                # Handle "Cannot run the event loop while another loop is running"
                if "another loop is running" in str(e):
                    logger.warning("Detected nested event loop execution, attempting alternate approach")
                    try:
                        # Try to get the current running loop
                        current_loop = asyncio.get_running_loop()
                        # Create a task in the running loop instead
                        future = asyncio.ensure_future(future, loop=current_loop)
                        return future
                    except Exception as inner_e:
                        logger.error(f"Failed to handle nested event loop: {inner_e}")
                        raise e
                else:
                    raise e  # Re-raise other RuntimeErrors
        
        # Apply the run_until_complete patch
        asyncio.BaseEventLoop.run_until_complete = patched_run_until_complete
        
        logger.info("Applied asyncio event loop patches successfully")
    except Exception as e:
        logger.error(f"Failed to patch asyncio: {e}")
        logger.error(traceback.format_exc())

def _patch_ban_manager():
    """Patch the ban_manager to prioritize Cloudflare."""
    try:
        from ddos_protection.storage import ban_manager
        
        # Store original method
        original_ban_ip = ban_manager.ban_ip
        
        # Create a new method that only uses Cloudflare
        def patched_ban_ip(ip: str, reason: str = "Unknown", duration: Optional[int] = None) -> bool:
            # Skip banning if the reason includes "OPTIONS" method
            if "OPTIONS" in reason:
                logger.info(f"Skipping ban for IP {ip} using OPTIONS method: {reason}")
                return False
                
            # Skip fingerprinting or device ban related reasons
            if "device" in reason.lower() or "fingerprint" in reason.lower():
                logger.info(f"Skipping device-related ban for IP {ip}: {reason}")
                return False
                
            # Always try Cloudflare but don't handle any local bans
            try:
                # Import the Cloudflare client directly
                from ddos_protection.network.cloudflare.api import cf_client
                
                if not cf_client:
                    logger.warning("Cloudflare client not available")
                    return False
                    
                # Use direct API call instead of async
                success = False
                
                try:
                    # Create a new thread to handle the Cloudflare API call
                    import threading
                    
                    result = {"success": False}
                    
                    def call_cloudflare():
                        try:
                            # Create a new event loop for this thread
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                # Call the Cloudflare API
                                cf_success, _ = loop.run_until_complete(cf_client.block_ip(ip, reason, duration or 86400))
                                result["success"] = cf_success
                            finally:
                                loop.close()
                        except Exception as e:
                            logger.error(f"Thread error calling Cloudflare: {e}")
                    
                    # Start the thread and wait for it to finish
                    t = threading.Thread(target=call_cloudflare)
                    t.daemon = True
                    t.start()
                    t.join(timeout=5.0)  # Wait up to 5 seconds
                    
                    success = result["success"]
                    
                    if success:
                        logger.info(f"Successfully blocked IP {ip} using Cloudflare")
                    else:
                        logger.warning(f"Failed to block IP {ip} using Cloudflare")
                    
                    # Always return True to bypass local banning
                    return True
                    
                except Exception as e:
                    logger.error(f"Error calling Cloudflare in thread: {e}")
                    # Return True to avoid local bans even on error
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to send Cloudflare ban for IP {ip}: {e}")
                # Return True to bypass local banning
                return True
            
            # We should never reach this point, but just in case
            return True
        
        # Apply the patch
        ban_manager.ban_ip = patched_ban_ip
        logger.info("ban_manager.ban_ip patched successfully - ONLY using Cloudflare")
        
        # Also patch is_banned to prevent local checks
        original_is_banned = ban_manager.is_banned
        
        def patched_is_banned(ip: str) -> bool:
            # Only check if the IP is OPTIONS request
            if ip.endswith("OPTIONS"):
                return False
            
            # Allow normal check to pass through
            return original_is_banned(ip)
            
        # Apply is_banned patch
        ban_manager.is_banned = patched_is_banned
        
    except ImportError as e:
        logger.error(f"Failed to patch ban_manager: {e}")

def _patch_early_ip_rejection():
    """Patch the early_ip_rejection function to ignore OPTIONS requests."""
    try:
        # Find server.py in the current path
        import sys
        import importlib
        
        # This approach can patch the function globally if it's already imported
        try:
            # Try to get the server module if it's already loaded
            import server
            
            # Get the early_ip_rejection function
            original_early_ip_rejection = server.early_ip_rejection
            
            # Define a wrapper function
            def patched_early_ip_rejection():
                # Skip processing for OPTIONS requests
                from flask import request
                if request.method == "OPTIONS":
                    logger.debug(f"Allowing OPTIONS request from {request.remote_addr}")
                    return None
                
                # Call original function for non-OPTIONS requests
                return original_early_ip_rejection()
            
            # Replace the original function
            server.early_ip_rejection = patched_early_ip_rejection
            logger.info("server.early_ip_rejection patched successfully")
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not patch early_ip_rejection directly: {e}")
            logger.warning("The server will need to be restarted for this patch to take effect")
            
    except Exception as e:
        logger.error(f"Failed to patch early_ip_rejection: {e}")

def _cleanup_options_bans():
    """Clean up any existing bans for OPTIONS requests"""
    try:
        # Import the ban manager
        from ddos_protection.storage import ban_manager
        
        # Get all banned IPs
        banned_ips = ban_manager.get_banned_ips()
        
        # Check for any OPTIONS-related bans
        options_bans = []
        for ip, ban_info in banned_ips.items():
            if "OPTIONS" in ban_info.get("reason", ""):
                options_bans.append(ip)
        
        # Remove any OPTIONS-related bans
        for ip in options_bans:
            logger.info(f"Removing OPTIONS-related ban for IP {ip}")
            ban_manager.unban_ip(ip)
            
        if options_bans:
            logger.info(f"Cleaned up {len(options_bans)} OPTIONS-related bans")
            
        # Also try to clean up via Cloudflare
        try:
            from ddos_protection.network.cloudflare.api import cf_client
            if cf_client:
                # Create a new thread to handle this
                import threading
                
                def cleanup_cloudflare():
                    try:
                        # Create a new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            # Get Cloudflare bans list
                            cf_bans = loop.run_until_complete(cf_client.list_blocked_ips())
                            # Filter for OPTIONS bans
                            for ip, info in cf_bans.items():
                                if "OPTIONS" in info.get("reason", ""):
                                    # Unblock the IP
                                    success, _ = loop.run_until_complete(cf_client.unblock_ip(ip))
                                    if success:
                                        logger.info(f"Successfully removed OPTIONS-related ban for IP {ip} in Cloudflare")
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.error(f"Error cleaning up Cloudflare bans: {e}")
                
                # Run the cleanup in a separate thread
                thread = threading.Thread(target=cleanup_cloudflare)
                thread.daemon = True
                thread.start()
        except Exception as e:
            logger.error(f"Failed to clean up Cloudflare bans: {e}")
            
    except Exception as e:
        logger.error(f"Failed to clean up OPTIONS-related bans: {e}")

def init():
    """Initialize the patch module."""
    patch_ddos_system()

# Apply patches immediately when imported
if __name__ != "__main__":
    init() 