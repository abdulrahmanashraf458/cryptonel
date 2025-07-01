#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Network Components
----------------------------------------
مكونات الشبكة لنظام الحماية من هجمات DDoS
"""

# Import Cloudflare components only - system_firewall has been removed
from .cloudflare import CloudflareAPIClient, cf_client

# Try to import additional Cloudflare components
try:
    from .cloudflare import init_cloudflare_integration, CLOUDFLARE_ENABLED
    __all__ = ['CloudflareAPIClient', 'cf_client', 'init_cloudflare_integration', 'CLOUDFLARE_ENABLED']
except ImportError:
    __all__ = ['CloudflareAPIClient', 'cf_client']