#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Manager Module
------------------------------------
Orchestrates all components of the DDoS protection system (detector, mitigator, API, monitor).
"""

import os
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable

# Local imports
from ddos_protection.config import Config, load_config
from ddos_protection.core.detector import AttackDetector
from ddos_protection.core.mitigator import AttackMitigator
from ddos_protection.api import create_api_server
from ddos_protection.storage import storage_manager

# Optional imports
try:
    from ddos_protection.monitoring.monitor import Monitor, create_monitor
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False
    logging.getLogger("ddos_protection.manager").warning("Monitor module not available, monitoring functionality will be limited")

# Configure logger
logger = logging.getLogger("ddos_protection.manager")

class DDoSProtectionSystem:
    """
    Main class for orchestrating all components of the DDoS protection system.
    """
    
    def __init__(self, config: Optional[Config] = None, config_path: Optional[str] = None):
        """
        Initialize the DDoS protection system.
        
        Args:
            config: System configuration (if None, will be loaded from config_path)
            config_path: Path to configuration file (if None, will use default)
        """
        # Load configuration
        self.config = config or load_config(config_path)
        
        # Configure storage system
        self._configure_storage()
        
        # Initialize components
        self.detector = AttackDetector(self.config)
        self.mitigator = AttackMitigator(self.config)
        self.api_server = create_api_server(
            self.config, 
            detector=self.detector, 
            mitigator=self.mitigator
        )
        
        # Initialize monitor if available
        self.monitor = None
        if MONITOR_AVAILABLE:
            self.monitor = create_monitor(self.config)
        
        # Periodic status updates
        self.status_update_task = None
        self.cleanup_task = None
        self.status_update_interval = 5  # seconds
        self.running = False
        
        logger.info("DDoS protection system initialized")
    
    def _configure_storage(self):
        """Configure the storage system based on configuration."""
        storage_config = self.config.storage
        
        # Log storage configuration
        logger.info(f"Configuring storage system with type: {storage_config.type}")
        logger.info(f"Storage directory: {storage_config.json_directory}")
        
        # The storage_manager is already initialized in the storage module
        # We just need to update it with our configuration
        
        # Custom initialization based on storage type could be added here
        if storage_config.type == "redis":
            logger.warning("Redis storage not fully implemented yet, falling back to JSON")
        
        logger.info("Storage system configured successfully")
    
    async def start(self, host: str = "127.0.0.1", port: int = 8080):
        """
        Start all components of the DDoS protection system.
        
        Args:
            host: Host to bind API server to
            port: Port to listen on for API server
        """
        if self.running:
            logger.warning("DDoS protection system already running")
            return
            
        logger.info("Starting DDoS protection system")
        
        # Start detector
        await self.detector.start()
        
        # Start mitigator
        await self.mitigator.start()
        
        # Start API server
        await self.api_server.start(host, port)
        
        # Start monitor if available
        if self.monitor:
            await self.monitor.start()
        
        # Start periodic status updates
        self.running = True
        self.status_update_task = asyncio.create_task(self._update_status_periodically())
        
        # Start storage cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_storage_periodically())
        
        logger.info("DDoS protection system started")
    
    async def stop(self):
        """Stop all components of the DDoS protection system."""
        if not self.running:
            logger.warning("DDoS protection system is not running")
            return
            
        logger.info("Stopping DDoS protection system")
        
        # Cancel status update task
        if hasattr(self, 'status_update_task') and self.status_update_task:
            self.status_update_task.cancel()
            
        # Cancel cleanup task
        if hasattr(self, 'cleanup_task') and self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Save all storage data
        storage_manager.save_all()
        
        # Stop API server
        await self.api_server.stop()
        
        # Stop monitor if available
        if self.monitor:
            await self.monitor.stop()
        
        # Stop detector
        await self.detector.stop()
        
        # Mark as stopped
        self.running = False
        
        logger.info("DDoS protection system stopped")
    
    async def _update_status_periodically(self):
        """Periodically update status and check for alerts."""
        try:
            while self.running:
                try:
                    # Get detector status
                    detector_status = self.detector.get_status()
                    
                    # Get mitigator stats
                    mitigator_stats = self.mitigator.get_mitigation_stats()
                    
                    # Check if under attack
                    if detector_status.get("under_attack", False):
                        logger.warning(
                            f"Under attack: {detector_status.get('attack_type', 'unknown')} "
                            f"(intensity: {detector_status.get('intensity', 0):.2f})"
                        )
                    
                    # Update monitor metrics if available
                    if self.monitor:
                        await self.monitor.update_metrics(detector_status, mitigator_stats)
                        
                        # Check if we should send alerts
                        await self.monitor.check_alerts(detector_status)
                        
                except Exception as e:
                    logger.error(f"Error updating status: {e}")
                
                # Sleep for the interval
                await asyncio.sleep(self.status_update_interval)
        
        except asyncio.CancelledError:
            logger.info("Status update task cancelled")
            raise
    
    async def _cleanup_storage_periodically(self):
        """Periodically clean up storage and save data."""
        try:
            cleanup_interval = self.config.storage.cleanup_interval
            while self.running:
                try:
                    # Run cleanup for all storage components
                    storage_manager.cleanup_all()
                    
                    # Save all data
                    storage_manager.save_all()
                    
                    logger.debug("Storage cleanup completed successfully")
                    
                except Exception as e:
                    logger.error(f"Error during storage cleanup: {e}")
                
                # Sleep for the cleanup interval
                await asyncio.sleep(cleanup_interval)
        
        except asyncio.CancelledError:
            logger.info("Storage cleanup task cancelled")
            # Final save before exiting
            try:
                storage_manager.save_all()
            except Exception as e:
                logger.error(f"Error during final storage save: {e}")
            raise
    
    async def process_request(
        self, 
        ip: str, 
        path: str, 
        user_agent: str = "", 
        request_size: int = 0
    ) -> bool:
        """
        Process a request through the DDoS protection system.
        
        Args:
            ip: Client IP address
            path: Request path
            user_agent: Client user agent
            request_size: Size of request in bytes
            
        Returns:
            bool: True if request is allowed, False if it should be blocked
        """
        # Skip if system is disabled
        if not self.config.enabled:
            return True
            
        try:
            # Check banned IPs first - always block banned IPs immediately
            if self.mitigator._is_banned(ip):
                logger.debug(f"Request from banned IP {ip} blocked immediately")
                return False
                
            # Create request data for detector
            request_data = {
                "ip": ip,
                "timestamp": time.time(),
                "path": path,
                "user_agent": user_agent,
                "bytes_received": request_size,
                "bytes_sent": 0,
                "status_code": 200
            }
            
            # Process through detector
            should_block = await self.detector.add_request(request_data)
            if should_block:
                return False
                
            # Process through mitigator
            is_allowed, _ = await self.mitigator.process_request(
                ip=ip,
                endpoint=path,
                user_agent=user_agent,
                request_size=request_size
            )
            
            return is_allowed
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            
            # If bypass_on_error is enabled, let the request through
            if self.config.bypass_on_error:
                return True
            else:
                # Otherwise, block the request
                return False
    
    def record_request_success(self, path: str):
        """
        Record a successful request.
        
        Args:
            path: Request path
        """
        if self.mitigator:
            self.mitigator.record_request_success(path)
    
    def record_request_failure(self, path: str, ip: str):
        """
        Record a failed request.
        
        Args:
            path: Request path
            ip: Client IP address
        """
        if self.mitigator:
            self.mitigator.record_request_failure(path, ip)


async def run_standalone_system(host: str = "127.0.0.1", port: int = 8080, config_path: Optional[str] = None):
    """
    Run the DDoS protection system in standalone mode.
    
    Args:
        host: Host to bind API server to
        port: Port to listen on for API server
        config_path: Path to configuration file
    """
    # Create system
    system = DDoSProtectionSystem(config_path=config_path)
    
    # Start system
    await system.start(host, port)
    
    try:
        # Run until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping system")
    finally:
        # Stop system
        await system.stop()


def main():
    """Command line entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DDoS Protection System")
    parser.add_argument(
        "--host", 
        default="127.0.0.1", 
        help="Host to bind API server to"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="Port to listen on for API server"
    )
    parser.add_argument(
        "--config", 
        default=None, 
        help="Path to configuration file"
    )
    args = parser.parse_args()
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run system
    asyncio.run(run_standalone_system(args.host, args.port, args.config))


if __name__ == "__main__":
    main() 