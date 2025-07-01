"""
Application Configuration

This module contains configuration settings for the application,
including database connections, API keys, and environment-specific settings.
"""

import os

class Config:
    """Base configuration class"""
    
    # Redis configuration
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    
    # Flask configuration
    SECRET_KEY = 'change-this-in-production'
    DEBUG = False
    TESTING = False
    
    # API configuration
    API_RATE_LIMIT = '100 per minute'
    
    # Security configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = False
    SECRET_KEY = 'dev-key-change-this'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = False
    DEBUG = False
    SECRET_KEY = 'test-key-change-this'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class ProductionConfig(Config):
    """Production environment configuration"""
    # Production settings should be loaded from environment variables
    pass


# Configuration dictionary to select the appropriate configuration
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 