#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Configuration Module
-------------------------------------------
Manages configuration settings for the DDoS protection system
using dataclasses and YAML for easy configuration.
"""

import os
import yaml
import logging
import ipaddress
from typing import List, Dict, Any, Set, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Configure logger
logger = logging.getLogger("ddos_protection.config")

@dataclass
class DetectorConfig:
    """Configuration for the attack detector component."""
    
    # Traffic analysis settings
    window_size: int = 60  # Size of sliding window for request tracking (seconds)
    rate_threshold: float = 20.0  # Requests per second threshold for individual IPs
    path_entropy_threshold: float = 1.5  # Threshold for path distribution entropy (lower = more suspicious)
    ua_diversity_threshold: int = 5  # Maximum number of different user agents from one IP in window
    error_rate_threshold: float = 0.4  # Maximum ratio of error responses to total requests
    bot_variance_threshold: float = 0.01  # Threshold for identifying bot-like request patterns
    
    # Scoring and blocking settings
    block_score_threshold: int = 5  # Score threshold to mark an IP as suspicious
    block_threshold: int = 10  # Score threshold for auto-blocking an IP
    suspicious_ip_threshold: int = 10  # Number of suspicious IPs to trigger attack detection
    global_rate_threshold: float = 100.0  # Global requests per second threshold
    global_window: int = 60  # Window for global rate calculation (seconds)
    
    # Cleanup and maintenance
    cleanup_interval: int = 30  # Interval for cleaning up expired records (seconds)
    record_expiry: int = 1800  # Time until IP records expire (seconds)
    
    # Whitelist and special cases
    whitelist: List[str] = field(default_factory=lambda: [
        "127.0.0.1", 
        "::1",
        "10.0.0.0/8",  # RFC1918 private networks
        "172.16.0.0/12",
        "192.168.0.0/16"
    ])
    
    # Machine learning settings
    use_ml: bool = True  # Enable machine learning for anomaly detection
    min_samples_for_training: int = 100  # Minimum number of samples before training ML model
    ml_retrain_interval: int = 3600  # Interval for retraining ML model (seconds)
    
    # Geolocation settings
    use_geolocation: bool = False  # Enable geolocation-based filtering
    geo_db_path: str = "./data/geolite2-country.mmdb"  # Path to MaxMind GeoLite2 database
    blocked_countries: List[str] = field(default_factory=list)  # Country codes to block
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure window sizes are reasonable
        if self.window_size < 10:
            logger.warning("window_size is too small, setting to minimum of 10 seconds")
            self.window_size = 10
            
        if self.global_window < 10:
            logger.warning("global_window is too small, setting to minimum of 10 seconds")
            self.global_window = 10
            
        # Parse CIDR notation in whitelist
        parsed_whitelist = []
        for item in self.whitelist:
            try:
                # Check if it's a CIDR notation
                if "/" in item:
                    network = ipaddress.ip_network(item, strict=False)
                    parsed_whitelist.append(str(network))
                else:
                    # Single IP address
                    ip = ipaddress.ip_address(item)
                    parsed_whitelist.append(str(ip))
            except ValueError:
                logger.warning(f"Invalid IP or network in whitelist: {item}")
        
        self.whitelist = parsed_whitelist


@dataclass
class MitigatorConfig:
    """Configuration for the attack mitigator component."""
    
    # Rate limiting settings
    rate_window: int = 60  # Window for rate limiting (seconds)
    global_rate_limit: int = 500  # Maximum global requests per window
    ip_rate_limit: int = 30  # Maximum requests per IP per window
    endpoint_rate_limit: int = 100  # Maximum requests per endpoint per window
    resource_check_interval: int = 30  # Interval for checking server resources (seconds)
    
    # Circuit breaker settings
    circuit_threshold: int = 5  # Failures before opening circuit
    circuit_threshold_critical: int = 3  # Failures before opening circuit for critical endpoints
    circuit_reset_timeout: int = 30  # Time before attempting to close circuit (seconds)
    global_circuit_threshold: int = 20  # Global failures before opening global circuit
    
    # Tarpit settings
    tarpit_base_delay: float = 0.1  # Base delay for tarpitting (seconds)
    tarpit_max_delay: float = 10.0  # Maximum delay for tarpitting (seconds)
    tarpit_expiry: int = 1800  # Time until tarpit entries expire (seconds)
    
    # Traffic redirection settings
    enable_redirection: bool = False  # Enable traffic redirection (requires root/sudo)
    redirect_destination: str = "DROP"  # Destination for redirected traffic (DROP, REJECT, or honeypot IP)
    redirect_threshold: int = 8  # Suspicious score threshold for traffic redirection
    
    # Challenge settings
    challenge_expiry: int = 300  # Time until challenges expire (seconds)
    challenge_secret: str = ""  # Secret key for signing challenges (autogenerated if empty)
    max_challenge_attempts: int = 5  # Maximum attempts to solve a challenge
    
    # Endpoint criticality
    critical_endpoints: List[str] = field(default_factory=lambda: [
        "/login", 
        "/register", 
        "/api/auth",
        "/api/payment",
        "/admin"
    ])
    
    # General settings
    cleanup_interval: int = 60  # Interval for cleaning up expired entries (seconds)
    permanent_block_threshold: int = 15  # Suspicious score threshold for permanent blocking
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure rate limits make sense
        if self.ip_rate_limit >= self.global_rate_limit:
            logger.warning("ip_rate_limit should be less than global_rate_limit, adjusting")
            self.ip_rate_limit = max(1, self.global_rate_limit // 10)
            
        # Normalize tarpit delays
        if self.tarpit_base_delay <= 0:
            self.tarpit_base_delay = 0.1
            
        if self.tarpit_max_delay <= self.tarpit_base_delay:
            self.tarpit_max_delay = self.tarpit_base_delay * 10
            
        # Validate redirect destination
        valid_destinations = ["DROP", "REJECT", "RETURN"]
        if (self.redirect_destination not in valid_destinations and 
            not self._is_valid_ip(self.redirect_destination)):
            logger.warning(f"Invalid redirect_destination: {self.redirect_destination}, setting to DROP")
            self.redirect_destination = "DROP"
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is a valid IP address."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False


@dataclass
class APIConfig:
    """Configuration for the API component."""
    
    # Authentication settings
    auth_required: bool = True  # Require authentication for API access
    auth_token: str = ""  # API authentication token (autogenerated if empty)
    token_expiry: int = 86400  # Token expiry time (seconds)
    
    # Endpoint settings
    base_path: str = "/ddos"  # Base path for API endpoints
    enable_management: bool = True  # Enable management endpoints (/block, /unblock, etc.)
    enable_metrics: bool = True  # Enable metrics endpoints (/status, /metrics, etc.)
    
    # CORS settings
    allow_cors: bool = False  # Allow Cross-Origin Resource Sharing
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    
    # Rate limiting settings for API itself
    rate_limit: int = 60  # Requests per minute for API endpoints
    
    def __post_init__(self):
        """Generate authentication token if not provided."""
        if not self.auth_token and self.auth_required:
            import secrets
            self.auth_token = secrets.token_urlsafe(32)
            logger.info("Generated new API authentication token")


@dataclass
class MonitorConfig:
    """Configuration for the monitoring component."""
    
    # Logging settings
    log_level: str = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file: str = ""  # Log file path (empty for console output)
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_json_logs: bool = False  # Enable JSON formatted logs
    
    # Prometheus metrics
    enable_prometheus: bool = True  # Enable Prometheus metrics
    prometheus_port: int = 9090  # Port for Prometheus metrics server
    
    # Alert settings
    enable_alerts: bool = False  # Enable alerting
    alert_methods: List[str] = field(default_factory=lambda: ["console"])  # Alert methods (console, email, slack, webhook)
    alert_threshold: float = 2.0  # Attack intensity threshold for alerting
    alert_cooldown: int = 300  # Cooldown between alerts (seconds)
    
    # Email alert settings
    email_server: str = "smtp.example.com"
    email_port: int = 587
    email_use_tls: bool = True
    email_username: str = ""
    email_password: str = ""
    email_from: str = "ddos-monitor@example.com"
    email_to: List[str] = field(default_factory=list)
    
    # Slack alert settings
    slack_webhook_url: str = ""
    
    # Custom webhook alert settings
    webhook_url: str = ""
    webhook_method: str = "POST"
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            logger.warning(f"Invalid log_level: {self.log_level}, setting to INFO")
            self.log_level = "INFO"
            
        # Validate alert methods
        valid_methods = ["console", "email", "slack", "webhook"]
        self.alert_methods = [m for m in self.alert_methods if m in valid_methods]
        
        # Check email configuration if email alerts are enabled
        if "email" in self.alert_methods:
            if not (self.email_username and self.email_password and self.email_to):
                logger.warning("Email alerts enabled but configuration incomplete")
                self.alert_methods.remove("email")
                
        # Check Slack configuration if Slack alerts are enabled
        if "slack" in self.alert_methods and not self.slack_webhook_url:
            logger.warning("Slack alerts enabled but webhook URL not provided")
            self.alert_methods.remove("slack")
            
        # Check webhook configuration if webhook alerts are enabled
        if "webhook" in self.alert_methods and not self.webhook_url:
            logger.warning("Webhook alerts enabled but URL not provided")
            self.alert_methods.remove("webhook")


@dataclass
class StorageConfig:
    """Configuration for the storage component."""
    
    # Storage type
    type: str = "json"  # Storage type (json, redis, memory)
    
    # JSON storage settings
    json_directory: str = "storage"  # Directory for JSON storage files
    
    # Cleanup settings
    cleanup_interval: int = 3600  # Interval for cleaning up expired entries (seconds)
    
    # TTL settings (time-to-live)
    banned_ips_ttl: int = 2592000  # 30 days
    suspicious_ips_ttl: int = 86400  # 1 day
    rate_limits_ttl: int = 3600  # 1 hour
    challenge_tokens_ttl: int = 1800  # 30 minutes
    
    # Size limits
    max_banned_ips: int = 100000  # Maximum number of banned IPs to store
    max_suspicious_ips: int = 500000  # Maximum number of suspicious IPs to store
    max_rate_limits: int = 50000  # Maximum number of rate limit entries
    max_challenge_tokens: int = 20000  # Maximum number of challenge tokens
    
    # Redis settings (if using Redis)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_prefix: str = "ddos:"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate storage type
        valid_types = ["json", "redis", "memory"]
        if self.type not in valid_types:
            logger.warning(f"Invalid storage type: {self.type}, setting to json")
            self.type = "json"
        
        # Ensure TTL values are reasonable
        if self.banned_ips_ttl < 3600:
            logger.warning("banned_ips_ttl is too small, setting to minimum of 1 hour")
            self.banned_ips_ttl = 3600
            
        if self.suspicious_ips_ttl < 300:
            logger.warning("suspicious_ips_ttl is too small, setting to minimum of 5 minutes")
            self.suspicious_ips_ttl = 300


@dataclass
class Config:
    """Main configuration for the DDoS protection system."""
    
    # Component configurations
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    mitigator: MitigatorConfig = field(default_factory=MitigatorConfig)
    api: APIConfig = field(default_factory=APIConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    # General settings
    enabled: bool = True  # Enable the DDoS protection system
    bypass_on_error: bool = True  # Allow requests through if the system encounters an error
    integration_mode: str = "middleware"  # Integration mode: middleware, proxy, or standalone
    
    # Environment and paths
    config_path: str = field(default_factory=lambda: os.environ.get("DDOS_CONFIG_PATH", "./config/ddos.yaml"))
    data_dir: str = field(default_factory=lambda: os.environ.get("DDOS_DATA_DIR", "./data"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            path: Path to save configuration to (uses config_path if not provided)
        """
        save_path = path or self.config_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
            
        logger.info(f"Configuration saved to {save_path}")


def load_config(path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        path: Path to configuration file (uses environment variable or default if not provided)
        
    Returns:
        Config: Loaded configuration
    """
    config_path = path or os.environ.get("DDOS_CONFIG_PATH", "./config/ddos.yaml")
    
    # Create default configuration
    config = Config()
    
    # If configuration file exists, load it
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                
            # Update configuration with loaded values
            if config_dict:
                # Handle top-level fields
                for key in ["enabled", "bypass_on_error", "integration_mode", "config_path", "data_dir"]:
                    if key in config_dict:
                        setattr(config, key, config_dict[key])
                
                # Handle component configurations
                for component in ["detector", "mitigator", "api", "monitor", "storage"]:
                    if component in config_dict:
                        component_config = getattr(config, component)
                        component_dict = config_dict[component]
                        
                        for key, value in component_dict.items():
                            if hasattr(component_config, key):
                                setattr(component_config, key, value)
                                
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        logger.info(f"Configuration file {config_path} not found, using defaults")
        
        # Create default configuration file
        try:
            config.save()
        except Exception as e:
            logger.warning(f"Could not create default configuration file: {e}")
    
    return config


# Default configuration instance
default_config = load_config() 