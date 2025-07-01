#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Monitoring Module
---------------------------------------
Handles logging, metrics collection, and alerting for the DDoS protection system.
"""

import os
import sys
import time
import json
import logging
import smtplib
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import RotatingFileHandler

# Local imports
from ddos_protection.config import Config

# Configure base logger
logger = logging.getLogger("ddos_protection")

class Monitor:
    """Main monitoring class for handling logs, metrics, and alerts."""
    
    def __init__(self, config: Config):
        """Initialize the monitor."""
        self.config = config
        self.alert_history = []
        self.last_alert_time = None
        self.alert_cooldown = self.config.monitor.alert_cooldown
        
        # Configure logging
        self._setup_logging()
        
        # Initialize Prometheus metrics if enabled
        if self.config.monitor.enable_prometheus:
            self._setup_prometheus()
        
        logger.info("DDoS protection monitor initialized")
    
    def _setup_logging(self):
        """Configure logging based on configuration."""
        # Get log level
        log_level_name = self.config.monitor.log_level.upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(self.config.monitor.log_format)
        
        # Configure root logger
        root_logger = logging.getLogger("ddos_protection")
        root_logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        
        # Always add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if configured
        if self.config.monitor.log_file:
            try:
                # Create directory if it doesn't exist
                log_dir = os.path.dirname(self.config.monitor.log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                # Setup rotating file handler
                file_handler = RotatingFileHandler(
                    self.config.monitor.log_file,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                
                logger.info(f"Logging to file: {self.config.monitor.log_file}")
            except Exception as e:
                logger.error(f"Failed to setup file logging: {e}")
    
    def _setup_prometheus(self):
        """Setup Prometheus metrics server if available."""
        try:
            from prometheus_client import start_http_server, Counter, Gauge
            
            # Start metrics server in a separate thread
            prometheus_port = self.config.monitor.prometheus_port
            start_http_server(prometheus_port)
            logger.info(f"Prometheus metrics server started on port {prometheus_port}")
            
            # Initialize metrics
            self.metrics = {
                # Counters
                "requests_total": Counter(
                    "ddos_requests_total", 
                    "Total number of requests processed"
                ),
                "blocked_requests_total": Counter(
                    "ddos_blocked_requests_total", 
                    "Total number of blocked requests"
                ),
                "attacks_total": Counter(
                    "ddos_attacks_total", 
                    "Total number of detected attacks"
                ),
                
                # Gauges
                "under_attack": Gauge(
                    "ddos_under_attack", 
                    "Whether the system is currently under attack"
                ),
                "attack_intensity": Gauge(
                    "ddos_attack_intensity", 
                    "Current attack intensity level"
                ),
                "suspicious_ips": Gauge(
                    "ddos_suspicious_ips", 
                    "Number of suspicious IPs"
                ),
                "blocked_ips": Gauge(
                    "ddos_blocked_ips", 
                    "Number of blocked IPs"
                )
            }
            
        except ImportError:
            logger.warning("prometheus_client not available, metrics collection disabled")
    
    async def start(self):
        """Start the monitoring system."""
        logger.info("DDoS protection monitor started")
    
    async def stop(self):
        """Stop the monitoring system."""
        logger.info("DDoS protection monitor stopped")
    
    async def update_metrics(self, detector_status: Dict[str, Any], mitigator_stats: Dict[str, Any]):
        """Update Prometheus metrics based on detector and mitigator status."""
        if not hasattr(self, "metrics"):
            return
            
        # Update metrics from detector
        if detector_status:
            self.metrics["under_attack"].set(1 if detector_status.get("under_attack", False) else 0)
            self.metrics["attack_intensity"].set(detector_status.get("intensity", 0))
            self.metrics["suspicious_ips"].set(detector_status.get("suspicious_ip_count", 0))
            
            # If we just detected an attack, increment the counter
            if detector_status.get("under_attack", False) and self.metrics["under_attack"]._value.get() == 0:
                self.metrics["attacks_total"].inc()
        
        # Update metrics from mitigator
        if mitigator_stats:
            self.metrics["blocked_ips"].set(mitigator_stats.get("blocked_ip_count", 0))
            
            # Update the delta for counters
            prev_blocked = self.metrics["blocked_requests_total"]._value.get()
            new_blocked = mitigator_stats.get("blocked_requests", 0)
            if new_blocked > prev_blocked:
                self.metrics["blocked_requests_total"]._value.set(new_blocked)
    
    async def check_alerts(self, detector_status: Dict[str, Any]):
        """Check if any alerts should be sent based on current status."""
        if not self.config.monitor.enable_alerts:
            return
            
        # Check if we're in alert cooldown period
        current_time = time.time()
        if (self.last_alert_time is not None and 
            current_time - self.last_alert_time < self.alert_cooldown):
            return
            
        # Check for attack that exceeds threshold
        is_attack = detector_status.get("under_attack", False)
        intensity = detector_status.get("intensity", 0)
        
        if is_attack and intensity >= self.config.monitor.alert_threshold:
            # Prepare alert message
            attack_type = detector_status.get("attack_type", "unknown")
            attack_start = detector_status.get("attack_start", datetime.now().isoformat())
            suspicious_count = detector_status.get("suspicious_ip_count", 0)
            
            message = f"DDoS attack detected!\n\n" \
                      f"Type: {attack_type}\n" \
                      f"Intensity: {intensity:.2f}\n" \
                      f"Start time: {attack_start}\n" \
                      f"Suspicious IPs: {suspicious_count}\n\n" \
                      f"Please check the monitoring dashboard for more details."
                      
            subject = f"DDoS Alert: {attack_type} attack (Intensity: {intensity:.2f})"
            
            # Send alerts through configured channels
            for method in self.config.monitor.alert_methods:
                try:
                    if method == "email":
                        await self._send_email_alert(subject, message)
                    elif method == "slack":
                        await self._send_slack_alert(subject, message)
                    elif method == "webhook":
                        await self._send_webhook_alert(subject, message)
                    elif method == "console":
                        logger.critical(f"ALERT: {subject}\n{message}")
                except Exception as e:
                    logger.error(f"Failed to send {method} alert: {e}")
            
            # Record alert
            self.alert_history.append({
                "timestamp": datetime.now().isoformat(),
                "subject": subject,
                "message": message,
                "intensity": intensity
            })
            
            # Update last alert time
            self.last_alert_time = current_time
    
    async def _send_email_alert(self, subject: str, message: str):
        """Send an email alert."""
        # Create message
        msg = MIMEMultipart()
        msg["From"] = self.config.monitor.email_from
        msg["To"] = ", ".join(self.config.monitor.email_to)
        msg["Subject"] = subject
        
        # Add message body
        msg.attach(MIMEText(message, "plain"))
        
        # Connect to SMTP server and send
        server = smtplib.SMTP(
            self.config.monitor.email_server, 
            self.config.monitor.email_port
        )
        
        if self.config.monitor.email_use_tls:
            server.starttls()
            
        if self.config.monitor.email_username and self.config.monitor.email_password:
            server.login(
                self.config.monitor.email_username,
                self.config.monitor.email_password
            )
            
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email alert sent to {self.config.monitor.email_to}")
    
    async def _send_slack_alert(self, subject: str, message: str):
        """Send a Slack alert."""
        if not self.config.monitor.slack_webhook_url:
            logger.error("Cannot send Slack alert: webhook URL not configured")
            return
            
        payload = {
            "text": f"*{subject}*\n```{message}```"
        }
        
        response = requests.post(
            self.config.monitor.slack_webhook_url,
            json=payload
        )
        
        if response.status_code == 200:
            logger.info("Slack alert sent")
        else:
            logger.error(f"Failed to send Slack alert: {response.status_code} {response.text}")
    
    async def _send_webhook_alert(self, subject: str, message: str):
        """Send a webhook alert."""
        if not self.config.monitor.webhook_url:
            logger.error("Cannot send webhook alert: URL not configured")
            return
            
        payload = {
            "subject": subject,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "ddos_protection"
        }
        
        response = requests.post(
            self.config.monitor.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in (200, 201, 202):
            logger.info("Webhook alert sent")
        else:
            logger.error(f"Failed to send webhook alert: {response.status_code} {response.text}")

def create_monitor(config: Config) -> Monitor:
    """Create a monitor instance."""
    return Monitor(config)

# Add the MonitorSystem class that's being imported in __init__.py
class MonitorSystem:
    """
    Wrapper for the Monitor class to provide compatibility with the DDoSProtectionSystem.
    This class is imported in the __init__.py file.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the monitoring system.
        
        Args:
            config: DDoS protection system configuration
        """
        # Create an instance of the underlying Monitor class
        self.monitor = Monitor(config)
        self.config = config
        logger.info("Monitor system initialized")
    
    async def start(self):
        """Start the monitoring system."""
        await self.monitor.start()
    
    async def stop(self):
        """Stop the monitoring system."""
        await self.monitor.stop()
    
    async def update_metrics(self, detector_status: Dict[str, Any], mitigator_stats: Dict[str, Any]):
        """Update system metrics."""
        await self.monitor.update_metrics(detector_status, mitigator_stats)
    
    async def check_alerts(self, detector_status: Dict[str, Any]):
        """Check and send alerts if necessary."""
        await self.monitor.check_alerts(detector_status) 